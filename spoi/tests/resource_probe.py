"""Subprocess for testing lifetimes including the process-wide sharing manager."""

from functools import partial
import gc
import json
import os
import sys

import psutil
import torch

from spoi.config import ExperimentConfig
from spoi.coordinator import ExpertSession, SessionError
from spoi.qwen3_adapter import build_reference
from test_failures import fault_worker


def main():
    config = ExperimentConfig(request_timeout=0.3, shutdown_timeout=0.2)
    _, state = build_reference(config)
    names = []
    identities = {}
    for mode in ("normal", "timeout", "crash"):
        target = {} if mode == "normal" else {"_worker_target": partial(fault_worker, mode=mode)}
        session = ExpertSession(config, state, **target)
        for shard in session._shards:
            for tensor in (shard.gate_up, shard.down):
                # Observe only our own named tensor resources, never unlink any.
                _, name, _ = tensor.untyped_storage()._share_filename_cpu_()
                names.append(name.decode())
        del tensor, shard
        try:
            with session:
                for child in psutil.Process().children(recursive=True):
                    identities[child.pid] = child.create_time()
                session.forward(torch.randn(1, 16, 64))
        except SessionError:
            if mode == "normal":
                raise
        else:
            if mode != "normal":
                raise AssertionError("injected failure did not occur")
        del session
        gc.collect()
    print(json.dumps(dict(pid=os.getpid(), processes=identities, shared_memory_names=names)), flush=True)


if __name__ == "__main__":
    main()
