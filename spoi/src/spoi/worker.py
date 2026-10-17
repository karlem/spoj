"""Private spawn entry and plain local-queue protocol; no full model in a child."""

from dataclasses import dataclass
import os
import time
import traceback

import torch
import torch.multiprocessing as mp

from .partition import Assignments
from .qwen3_adapter import ExpertShard, configure_threads, evaluate_shard


@dataclass(frozen=True)
class Execute:
    run_id: str
    request_id: int
    worker_id: int
    assignments: Assignments


@dataclass(frozen=True)
class Stop:
    run_id: str


def worker_main(worker_id, run_id, shard: ExpertShard, requests, responses, threads):
    request_id = None
    try:
        mp.set_sharing_strategy("file_system")
        configure_threads(threads)
        if shard.actual_digest() != shard.digest:
            raise ValueError("expert shard integrity mismatch")
        if any(tensor.untyped_storage().nbytes() != tensor.numel() * tensor.element_size()
               for tensor in (shard.gate_up, shard.down)):
            raise ValueError("expert shard retains nonlocal backing storage")
        responses.put(dict(kind="ready", run_id=run_id, worker_id=worker_id, pid=os.getpid(),
                           expert_ids=shard.expert_ids, digest=shard.digest,
                           state_hash=shard.state_hash, storage_bytes=shard.storage_bytes))
        last_request = 0
        with torch.inference_mode():
            while True:
                message = requests.get()
                if isinstance(message, Stop) and message.run_id == run_id:
                    responses.put(dict(kind="stopped", run_id=run_id, worker_id=worker_id))
                    return
                if not isinstance(message, Execute):
                    raise ValueError("unexpected request message")
                request_id = message.request_id
                if message.run_id != run_id or message.worker_id != worker_id or request_id <= last_request:
                    raise ValueError("stale or mismatched request identity")
                last_request = request_id
                a = message.assignments
                start = time.perf_counter_ns()
                output = evaluate_shard(shard, a.rows, a.expert_ids, a.weights)
                compute_ns = time.perf_counter_ns() - start
                responses.put(dict(kind="result", run_id=run_id, request_id=request_id,
                                   worker_id=worker_id, token_indices=a.token_indices,
                                   slot_indices=a.slot_indices, output=output, compute_ns=compute_ns))
    except BaseException as exc:
        responses.put(dict(kind="error", run_id=run_id, request_id=request_id,
                           worker_id=worker_id, error_type=type(exc).__name__,
                           message=str(exc), traceback=traceback.format_exc()))
