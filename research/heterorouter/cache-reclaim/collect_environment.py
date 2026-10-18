#!/usr/bin/env python3
"""Bounded readiness evidence; this does not execute or benchmark an inference engine."""
import argparse
import ctypes
import datetime
import errno
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as exc:
        return {"error": type(exc).__name__, "errno": exc.errno}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    commands = []
    for command in (["lscpu", "--json"],
                    ["lsblk", "--json", "-o", "NAME,TYPE,SIZE,MOUNTPOINTS"],
                    ["findmnt", "-T", "/workspace", "-o", "TARGET,SOURCE,FSTYPE"],
                    ["findmnt", "-T", "/tmp", "-o", "TARGET,SOURCE,FSTYPE"]):
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=10)
            commands.append({"argv": command, "exit_code": proc.returncode,
                             "stdout": proc.stdout[:16000], "stderr": proc.stderr[:2000]})
        except (OSError, subprocess.TimeoutExpired) as exc:
            commands.append({"argv": command, "exit_code": None, "error": str(exc)})
    status = read("/proc/self/status")
    status = [line for line in status.splitlines()
              if line.startswith(("Cap", "Cpus_allowed_list:", "Mems_allowed_list:"))]
    paths = ["/proc/self/cgroup", "/proc/sys/kernel/perf_event_paranoid",
             "/sys/kernel/security/lockdown"]
    paths += ["/sys/fs/cgroup/" + name for name in
              ("cpu.max", "cpu.stat", "cpuset.cpus.effective", "memory.max",
               "memory.current", "memory.peak", "memory.swap.max", "memory.stat",
               "memory.events", "memory.pressure", "io.stat", "io.pressure")]
    perf = {"purpose": "disabled own-process userspace task-clock permission probe"}
    syscall = {"x86_64": 298, "aarch64": 241}.get(platform.machine())
    if syscall is not None:
        # perf_event_attr v0: disabled, exclude_kernel, exclude_hv; no sampling.
        attr = ctypes.create_string_buffer(struct.pack("IIQQQQQIIQ", 1, 64, 1,
                                                     0, 0, 0, 1 | 32 | 64, 0, 0, 0))
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        fd = libc.syscall(syscall, ctypes.byref(attr), 0, -1, -1, 0)
        if fd >= 0:
            os.close(fd)
            perf.update(available=True, errno=0)
        else:
            code = ctypes.get_errno()
            perf.update(available=False, errno=code, error=errno.errorcode.get(code))
    else:
        perf.update(available=None, reason="unlisted syscall architecture")
    strace = {"purpose": "trace /bin/true only; not an inference or storage trace"}
    if shutil.which("strace"):
        command = ["strace", "-o", str(args.output / "strace-readiness.log"),
                   "-e", "trace=openat,read,pread64,mmap,madvise,munmap", "/bin/true"]
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=10)
            strace.update(argv=command, exit_code=proc.returncode,
                          stderr=proc.stderr[:2000])
        except (OSError, subprocess.TimeoutExpired) as exc:
            strace.update(exit_code=None, error=str(exc))
    else:
        strace.update(exit_code=None, error="tool unavailable")
    packages = {}
    for name in ("torch", "transformers", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    mounts = {}
    for name in ("/workspace", "/tmp"):
        stat = os.statvfs(name)
        mounts[name] = {"capacity_bytes": stat.f_blocks * stat.f_frsize,
                        "available_bytes": stat.f_bavail * stat.f_frsize}
    result = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "platform": platform.platform(), "kernel": platform.release(),
              "machine": platform.machine(), "python": platform.python_version(),
              "packages": packages, "page_bytes": os.sysconf("SC_PAGESIZE"),
              "affinity": sorted(os.sched_getaffinity(0)), "status": status,
              "files": {path: read(path) for path in paths}, "mount_capacity": mounts,
              "tools": {name: shutil.which(name) for name in
                        ("perf", "bpftrace", "strace", "nsys", "iostat", "nvidia-smi", "uv")},
              "tracepoint_directory": {path: {"exists": Path(path).exists(),
                   "readable": os.access(path, os.R_OK),
                   "events_exists": (Path(path) / "events").exists()}
                  for path in ("/sys/kernel/tracing", "/sys/kernel/debug/tracing")},
              "perf_event_open": perf, "strace_readiness": strace,
              "commands": commands,
              "limitations": ["No model or inference workload executed by this collector.",
                  "Guest devices do not identify host storage or sustainable bandwidth.",
                  "Cgroup counters are snapshots of this session, not model measurements."]}
    (args.output / "environment.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"environment": str(args.output / "environment.json"),
                      "perf_event_open": perf, "strace_readiness": strace}, indent=2))


if __name__ == "__main__":
    main()
