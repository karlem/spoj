"""Local TCP boundary with independent HF contribution and output checks."""
from dataclasses import asdict
import socket
import subprocess
import sys
import time
import uuid
import threading

import torch

from .baseline import baseline
from .partition import aggregate, pack, validate_input
from .qwen3_adapter import ExpertShard, compatibility, tensor_digest
from .tcp_wire import ProtocolError, recv_frame, send_frame
from .tcp_worker import identity


class TCPError(RuntimeError):
    pass


def owners_for(experts, workers):
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError('local TCP supports 1 through 4 workers')
    quotient, extra = divmod(experts, workers)
    return tuple(worker for worker in range(workers) for _ in range(quotient+(worker < extra)))


class TCPSession:
    def __init__(self, block, frozen, workers=3, *, trace=False, _worker_script=None):
        self.owners = owners_for(frozen.config.num_experts, workers)
        if tensor_digest(block.state_dict()) != frozen.hash:
            raise ValueError('oracle differs from frozen state')
        self.block, self.frozen, self.config = block, frozen, frozen.config
        self.count, self.trace = workers, trace
        self.run = uuid.uuid4().hex
        self.processes, self.sockets, self.listeners = [], [], []
        self.ready, self.events, self.records = [], [], []
        self.request, self.closed, self.opened = 0, False, False
        self.exitcodes = []
        self.shutdown_errors = []
        self._sent = {}
        self._trace_bytes = 0
        self._lock = threading.Lock()
        self._worker_script = _worker_script
        self.versions = compatibility()

    def _meta(self, kind, worker, request, **extra):
        return dict(kind=kind, run=self.run, worker=worker, request=request, **extra)

    def _event(self, sock, event):
        if self.trace:
            self._trace_bytes += event['bytes']
            if len(self.events) >= 128 or self._trace_bytes > 4*1024*1024:
                raise TCPError('trace frame budget exceeded')
            self.events.append(dict(**event, local=list(sock.getsockname()), peer=list(sock.getpeername())))

    def _send(self, worker, kind, tensors, deadline, request=None, **extra):
        sock = self.sockets[worker]
        event = send_frame(sock, self._meta(kind, worker, self.request if request is None else request, **extra),
                           tensors, deadline, capture=self.trace)
        self._event(sock, event)
        self._sent[(worker, kind)] = event['sha256']

    def _recv(self, worker, kind, deadline, request=None):
        sock = self.sockets[worker]
        meta, tensors, event = recv_frame(sock, deadline, capture=self.trace)
        self._event(sock, event)
        if meta.get('kind') == 'error':
            raise TCPError(f'worker error: {meta.get("message")}')
        identity(meta, kind, self.run, worker, self.request if request is None else request)
        return meta, tensors

    def __enter__(self):
        if self.opened or self.closed:
            raise TCPError('session cannot be reused')
        self.opened = True
        deadline = time.monotonic()+self.config.startup_timeout
        state = self.frozen.state_dict()
        try:
            for worker in range(self.count):
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listeners.append(listener)
                listener.bind(('127.0.0.1', 0))
                listener.listen(1)
                port = listener.getsockname()[1]
                command = [sys.executable, '-m', 'spoi.tcp_worker'] if self._worker_script is None else [sys.executable, self._worker_script]
                command += ['--port', str(port), '--worker', str(worker), '--run', self.run,
                            '--startup-timeout', str(self.config.startup_timeout)]
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                self.processes.append(process)
                listener.settimeout(max(0.001, deadline-time.monotonic()))
                connection, _ = listener.accept()
                self.sockets.append(connection)
                listener.close()
                hello, tensors = self._recv(worker, 'hello', deadline, request=0)
                if (set(hello) != {'kind', 'run', 'worker', 'request', 'pid', 'versions'} or tensors
                        or hello['pid'] != process.pid or hello['versions'] != self.versions):
                    raise TCPError('invalid hello')
                ids = tuple(e for e, owner in enumerate(self.owners) if owner == worker)
                shard = ExpertShard(ids, state['experts.gate_up_proj'][list(ids)].clone(),
                                    state['experts.down_proj'][list(ids)].clone(), self.frozen.hash, '')
                digest = shard.actual_digest()
                self._send(worker, 'init', dict(gate_up=shard.gate_up, down=shard.down), deadline, request=0,
                           config=asdict(self.config), ids=list(ids), hash=self.frozen.hash, digest=digest)
                ready, tensors = self._recv(worker, 'ready', deadline, request=0)
                expected = self._meta('ready', worker, 0, pid=process.pid, ids=list(ids),
                                      hash=self.frozen.hash, digest=digest, storage=list(shard.storage_bytes),
                                      received_init=self._sent[(worker, 'init')])
                if ready != expected or tensors:
                    raise TCPError('invalid readiness/ownership/digest')
                self.ready.append(ready)
            return self
        except BaseException:
            self.close(suppress=True)
            raise

    def forward(self, x):
        if not self.opened or self.closed:
            raise TCPError('session is not running')
        if not self._lock.acquire(blocking=False):
            raise TCPError('concurrent requests unsupported')
        try:
            validate_input(x, self.config.hidden_size)
            if self.trace and (x.shape[0]*x.shape[1] > 16 or x.shape[2] > 64 or len(self.records) >= 4):
                raise TCPError('bounded trace supports <=16 tokens, <=64 hidden, <=4 requests')
            self.request += 1
            deadline = time.monotonic()+self.config.request_timeout
            with torch.inference_mode():
                logits, weights, selected = self.block.gate(x)
                # The coordinator uses an independent router cloned from snapshot.
                other_logits, other_weights, other_selected = self.frozen.router()(x)
                torch.testing.assert_close(other_logits, logits, rtol=0, atol=0)
                torch.testing.assert_close(other_weights, weights, rtol=0, atol=0)
                assert torch.equal(other_selected, selected), 'router expert mismatch'
                assignments = pack(x, other_selected, other_weights, self.owners, self.count)
                pairs = [(int(t), int(s)) for a in assignments for t, s in zip(a.token_indices, a.slot_indices)]
                wanted = {(t, s) for t in range(x.shape[0]*x.shape[1]) for s in range(self.config.top_k)}
                if len(pairs) != len(wanted) or set(pairs) != wanted:
                    raise TCPError('assignment coverage mismatch')
                for worker, a in enumerate(assignments):
                    self._send(worker, 'execute', dict(rows=a.rows, tokens=a.token_indices, slots=a.slot_indices,
                                                       experts=a.expert_ids, weights=a.weights), deadline)
                outputs, oracle_outputs, contributions = [], [], []
                for worker, a in enumerate(assignments):
                    meta, tensors = self._recv(worker, 'result', deadline)
                    if set(meta) != {'kind', 'run', 'worker', 'request', 'received_request'} or meta.get('received_request') != self._sent[(worker, 'execute')] or set(tensors) != {'tokens', 'slots', 'experts', 'weights', 'output'}:
                        raise TCPError('invalid result schema')
                    for key, expected in dict(tokens=a.token_indices, slots=a.slot_indices, experts=a.expert_ids, weights=a.weights).items():
                        value = tensors[key]
                        if value.dtype != expected.dtype or value.shape != expected.shape or not torch.equal(value, expected):
                            raise TCPError('returned assignment identity/coverage mismatch')
                    value = tensors['output']
                    if value.dtype != torch.float32 or value.shape != a.rows.shape:
                        raise TCPError('invalid contribution shape/dtype')
                    # Actual untouched HF experts execute one expert choice per row.
                    # This oracle does not call the custom shard evaluator.
                    oracle = self.block.experts(a.rows, a.expert_ids[:, None], a.weights[:, None])
                    torch.testing.assert_close(value, oracle, rtol=1e-5, atol=1e-6, msg='HF contribution parity')
                    outputs.append(value)
                    oracle_outputs.append(oracle)
                    if self.trace:
                        for i in range(a.count):
                            contributions.append(dict(worker=worker, token=int(a.token_indices[i]), slot=int(a.slot_indices[i]),
                                expert=int(a.expert_ids[i]), weight=float(a.weights[i]), input=a.rows[i].tolist(),
                                output=value[i].tolist(), hf_output=oracle[i].tolist()))
                actual = aggregate(x.shape, assignments, outputs)
                oracle_sum = aggregate(x.shape, assignments, oracle_outputs)
                expected = baseline(self.block, x)
                torch.testing.assert_close(oracle_sum, expected, rtol=1e-5, atol=1e-6)
                torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
                if self.trace:
                    self.records.append(dict(request=self.request, input=x.tolist(), logits=logits.tolist(),
                        selected=selected.tolist(), weights=weights.tolist(), contributions=contributions,
                        output=actual.tolist(), hf_output=expected.tolist(),
                        max_absolute_error=float((actual-expected).abs().max()) if actual.numel() else 0.0))
                return actual
        except BaseException:
            self.close(suppress=True)
            raise
        finally:
            self._lock.release()

    def close(self, *, suppress=False):
        if self.closed:
            return
        self.closed = True
        deadline = time.monotonic()+self.config.shutdown_timeout
        for worker in range(len(self.sockets)):
            try:
                self._send(worker, 'stop', {}, deadline, request=self.request+1)
                meta, tensors = self._recv(worker, 'stopped', deadline, request=self.request+1)
                if set(meta) != {'kind', 'run', 'worker', 'request'} or tensors:
                    raise TCPError('invalid stop acknowledgement')
            except Exception as exc:
                self.shutdown_errors.append(f'worker {worker}: {type(exc).__name__}: {exc}')
        for connection in [*self.sockets, *self.listeners]:
            connection.close()
        for process in self.processes:
            try:
                process.wait(timeout=max(0, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic()+1
        for process in self.processes:
            try:
                process.wait(timeout=max(0, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
        deadline = time.monotonic()+1
        for process in self.processes:
            process.wait(timeout=max(0.001, deadline-time.monotonic()))
        self.exitcodes = [p.returncode for p in self.processes]
        if any(code != 0 for code in self.exitcodes):
            self.shutdown_errors.append(f'unclean exit codes: {self.exitcodes}')
        if self.shutdown_errors and not suppress:
            raise TCPError('shutdown failure: ' + '; '.join(self.shutdown_errors))

    def __exit__(self, exc_type, exc, tb):
        self.close(suppress=exc_type is not None)
