import ctypes
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil


def test_subprocess_cleanup_has_no_process_or_named_shard_leak():
    probe = Path(__file__).with_name("resource_probe.py")
    completed = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True,
                               timeout=90, env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "resource_tracker:" not in completed.stderr, completed.stderr
    assert "leaked semaphore" not in completed.stderr, completed.stderr
    data = json.loads(completed.stdout.splitlines()[-1])
    # Native macOS and Linux expose POSIX shm_open through libc. This probe
    # opens read-only and closes; it never removes a resource to fake cleanup.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint]
    libc.shm_open.restype = ctypes.c_int

    def alive():
        result = []
        for pid, created in data["processes"].items():
            try:
                process = psutil.Process(int(pid))
                if process.create_time() == created and process.status() != psutil.STATUS_ZOMBIE:
                    result.append(int(pid))
            except psutil.NoSuchProcess:
                pass
        return result

    def named_resources():
        result = []
        for name in data["shared_memory_names"]:
            descriptor = libc.shm_open(name.encode(), os.O_RDONLY, 0)
            if descriptor >= 0:
                os.close(descriptor)
                result.append(name)
            else:
                assert ctypes.get_errno() == errno.ENOENT
        return result

    deadline = time.monotonic() + 10  # torch_shm_manager has a cleanup grace period.
    while time.monotonic() < deadline and (alive() or named_resources()):
        time.sleep(0.1)
    assert not alive(), f"surviving descendants: {alive()}"
    assert not named_resources(), f"leaked named shards: {named_resources()}"
