"""One-request-at-a-time session hiding spawn, bounded transport and cleanup."""

from dataclasses import dataclass
import queue
import threading
import time
import uuid

import torch
import torch.multiprocessing as mp

from .partition import aggregate, pack, validate_input
from .qwen3_adapter import FrozenState, configure_threads
from .worker import Execute, Stop, worker_main


class SessionError(RuntimeError):
    pass


class SessionTimeout(SessionError):
    pass


@dataclass(frozen=True)
class ForwardResult:
    output: torch.Tensor
    run_id: str
    request_id: int
    assignment_counts: tuple[int, int]
    worker_compute_ns: tuple[int, int]
    timings_ns: dict[str, int]


class ExpertSession:
    """Context manager for exactly two persistent local CPU expert workers.

    Construct with the reference's FrozenState. Enter before forward; close is
    idempotent. A protocol/worker/deadline failure permanently closes the session.
    Concurrent forward calls are rejected. `_worker_target` is a private seam
    for adversarial protocol tests, never a CLI fault-injection option.
    """

    def __init__(self, config, frozen: FrozenState, *, _worker_target=worker_main):
        if config != frozen.config:
            raise ValueError("session config differs from frozen state config")
        configure_threads(config.threads)
        self.config = config
        self.run_id = uuid.uuid4().hex
        self.state_hash = frozen.hash
        self._router = frozen.router()
        self._shards = tuple(frozen.shard(worker) for worker in (0, 1))
        self._worker_target = _worker_target
        self._processes = []
        self._requests = []
        self._responses = None
        self._opened = False
        self._closed = False
        self._request_id = 0
        self._forward_lock = threading.Lock()
        self.workers = ()
        self.startup_ns = None
        self.exitcodes = ()

    @property
    def worker_pids(self):
        return tuple(worker["pid"] for worker in self.workers)

    def __enter__(self):
        if self._closed or self._opened:
            raise SessionError("session cannot be entered twice")
        self._opened = True
        start = time.perf_counter_ns()
        try:
            mp.set_sharing_strategy("file_system")
            context = mp.get_context("spawn")
            self._responses = context.Queue(maxsize=4)
            for worker, shard in enumerate(self._shards):
                requests = context.Queue(maxsize=1)
                self._requests.append(requests)
                process = context.Process(target=self._worker_target,
                                          args=(worker, self.run_id, shard, requests,
                                                self._responses, self.config.threads),
                                          name=f"spoi-{self.run_id}-{worker}")
                self._processes.append(process)
                process.start()
            ready = {}
            deadline = time.monotonic() + self.config.startup_timeout
            while len(ready) < 2:
                message = self._receive(deadline)
                worker = self._identity(message, "ready", ready)
                shard = self._shards[worker]
                expected = dict(pid=self._processes[worker].pid, expert_ids=shard.expert_ids,
                                digest=shard.digest, state_hash=self.state_hash,
                                storage_bytes=shard.storage_bytes)
                if any(message.get(key) != value for key, value in expected.items()):
                    raise SessionError(f"worker {worker} readiness/integrity mismatch")
                ready[worker] = message
            self.workers = tuple(ready[worker] for worker in (0, 1))
            # Children now own only the transmitted compact slices.
            self._shards = ()
            self.startup_ns = time.perf_counter_ns() - start
            return self
        except BaseException:
            self.close()
            raise

    def _check_children(self):
        for worker, process in enumerate(self._processes):
            if process.pid is not None and process.exitcode is not None:
                raise SessionError(f"worker {worker} exited unexpectedly (exitcode={process.exitcode})")

    @staticmethod
    def _remaining(deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SessionTimeout("worker deadline exceeded")
        return min(remaining, 0.05)

    def _receive(self, deadline):
        while True:
            try:
                # Read available traceback/error before inspecting exit status.
                return self._responses.get(timeout=self._remaining(deadline))
            except queue.Empty:
                self._check_children()

    def _send(self, worker, message, deadline):
        while True:
            self._check_children()
            try:
                self._requests[worker].put(message, timeout=self._remaining(deadline))
                return
            except queue.Full:
                pass

    def _identity(self, message, kind, seen, request_id=None):
        if not isinstance(message, dict):
            raise SessionError("malformed worker message")
        worker = message.get("worker_id")
        if (message.get("run_id") != self.run_id or type(worker) is not int
                or worker not in (0, 1) or worker in seen):
            raise SessionError("stale, mismatched or duplicate worker identity")
        if message.get("kind") == "error":
            if message.get("request_id") != request_id:
                raise SessionError("mismatched worker error request ID")
            raise SessionError(f"worker {worker}: {message.get('error_type')}: {message.get('message')}\n"
                               f"{message.get('traceback')}")
        if message.get("kind") != kind or (request_id is not None and message.get("request_id") != request_id):
            raise SessionError("unexpected worker message kind or request ID")
        return worker

    def forward(self, x) -> ForwardResult:
        if not self._opened or self._closed:
            raise SessionError("session is not running")
        if not self._forward_lock.acquire(blocking=False):
            raise SessionError("concurrent forward calls are unsupported")
        try:
            validate_input(x, self.config.hidden_size)
            with torch.inference_mode():
                start = time.perf_counter_ns()
                deadline = time.monotonic() + self.config.request_timeout
                _, weights, selected = self._router(x)
                routed = time.perf_counter_ns()
                assignments = pack(x, selected, weights, self.config.owners)
                packed = time.perf_counter_ns()
                self._request_id += 1
                request_id = self._request_id
                for worker, assignment in enumerate(assignments):
                    self._send(worker, Execute(self.run_id, request_id, worker, assignment), deadline)
                dispatched = time.perf_counter_ns()
                replies = {}
                while len(replies) < 2:
                    message = self._receive(deadline)
                    worker = self._identity(message, "result", replies, request_id)
                    self._validate_result(message, assignments[worker])
                    replies[worker] = message
                gathered = time.perf_counter_ns()
                output = aggregate(x.shape, assignments, [replies[w]["output"] for w in (0, 1)])
                finished = time.perf_counter_ns()
                timings = dict(router_ns=routed-start, pack_ns=packed-routed,
                               dispatch_ns=dispatched-packed, wait_gather_ns=gathered-dispatched,
                               aggregate_ns=finished-gathered, distributed_e2e_ns=finished-start)
                return ForwardResult(output, self.run_id, request_id,
                                     tuple(a.count for a in assignments),
                                     tuple(replies[w]["compute_ns"] for w in (0, 1)), timings)
        except BaseException:
            self.close()
            raise
        finally:
            self._forward_lock.release()

    @staticmethod
    def _validate_result(message, expected):
        for key in ("token_indices", "slot_indices"):
            actual = message.get(key)
            wanted = getattr(expected, key)
            if (not isinstance(actual, torch.Tensor) or actual.device.type != "cpu"
                    or actual.dtype != torch.long or actual.shape != wanted.shape
                    or not torch.equal(actual, wanted)):
                raise SessionError(f"invalid returned {key}: assignment coverage mismatch")
        output = message.get("output")
        if (not isinstance(output, torch.Tensor) or output.device.type != "cpu"
                or output.dtype != torch.float32 or output.shape != expected.rows.shape
                or not torch.isfinite(output).all()):
            raise SessionError("invalid worker output shape/dtype/values")
        if type(message.get("compute_ns")) is not int or message["compute_ns"] < 0:
            raise SessionError("invalid worker compute duration")

    def close(self):
        if self._closed:
            return
        self._closed = True
        deadline = time.monotonic() + self.config.shutdown_timeout
        for worker, requests in enumerate(self._requests):
            try:
                requests.put_nowait(Stop(self.run_id))
            except (queue.Full, ValueError, OSError):
                pass
        # Drain replies while joining: tensor queue producers may otherwise wait
        # for a feeder that cannot finish. Never join a failed queue feeder.
        while any(p.pid is not None and p.is_alive() for p in self._processes) and time.monotonic() < deadline:
            try:
                self._responses.get(timeout=min(0.05, max(0.001, deadline-time.monotonic())))
            except Exception:
                # A worker may have died during tensor serialization. Cleanup
                # must still reap both children if a queue cannot be decoded.
                pass
            for process in self._processes:
                if process.pid is not None:
                    process.join(timeout=0)
        for process in self._processes:
            if process.pid is None:
                continue
            if process.is_alive():
                process.terminate()
        for process in self._processes:
            if process.pid is None:
                continue
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
        self.exitcodes = tuple(p.exitcode for p in self._processes if p.pid is not None)
        survivors = [p.pid for p in self._processes if p.pid is not None and p.is_alive()]
        for channel in [*self._requests, self._responses]:
            if channel is not None:
                channel.cancel_join_thread()
                channel.close()
        for process in self._processes:
            if process.pid is not None and not process.is_alive():
                process.close()
        self._processes = []
        self._requests = []
        self._responses = None
        self._shards = ()
        if survivors:
            raise SessionError(f"could not reap worker processes: {survivors}")

    def __exit__(self, exc_type, exc, tb):
        self.close()
