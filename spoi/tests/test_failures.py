"""Adversarial workers use the real loop/math and corrupt only its private seam."""

from functools import partial
import os
import time

import pytest
import torch

from spoi.config import ExperimentConfig
from spoi.coordinator import ExpertSession, SessionError, SessionTimeout
from spoi.qwen3_adapter import build_reference
from spoi.worker import worker_main


class FaultResponses:
    def __init__(self, channel, worker, mode):
        self.channel, self.worker, self.mode = channel, worker, mode

    def put(self, message):
        if self.worker == 0:
            if message["kind"] == "ready":
                if self.mode == "startup-error":
                    raise RuntimeError("intentional startup failure")
                if self.mode == "bad-digest":
                    message["digest"] = "incorrect"
                self.channel.put(message)
                if self.mode == "hang-before-receive":
                    time.sleep(60)
                return
            if message["kind"] == "result":
                if self.mode == "traceback":
                    raise RuntimeError("intentional expert failure")
                if self.mode == "crash":
                    os._exit(23)
                if self.mode == "timeout":
                    time.sleep(60)
                if self.mode == "wrong-request":
                    message["request_id"] += 99
                if self.mode == "wrong-run":
                    message["run_id"] = "stale-run"
                if self.mode == "wrong-worker":
                    message["worker_id"] = 9
                if self.mode == "missing-slot":
                    message["slot_indices"] = message["slot_indices"][:-1]
                if self.mode == "wrong-token":
                    message["token_indices"] = message["token_indices"] + 1
                if self.mode == "nan":
                    message["output"].fill_(float("nan"))
                if self.mode == "shape":
                    message["output"] = message["output"][:, :-1].clone()
                if self.mode == "dtype":
                    message["output"] = message["output"].double()
                if self.mode == "duration":
                    message["compute_ns"] = -1
                if self.mode == "malformed":
                    self.channel.put(None)
                    return
                if self.mode == "duplicate":
                    self.channel.put(message)
        self.channel.put(message)


def fault_worker(worker, run_id, shard, requests, responses, threads, *, mode):
    worker_main(worker, run_id, shard, requests, FaultResponses(responses, worker, mode), threads)


@pytest.mark.parametrize("mode,match", [
    ("traceback", "intentional expert failure"), ("crash", "exited unexpectedly"),
    ("wrong-request", "request ID"), ("wrong-run", "identity"), ("wrong-worker", "identity"),
    ("missing-slot", "coverage"), ("wrong-token", "coverage"), ("nan", "output"),
    ("shape", "output"), ("dtype", "output"), ("duration", "duration"),
    ("malformed", "malformed"), ("duplicate", "identity|request ID"),
])
def test_protocol_and_worker_failures_close_session(mode, match):
    config = ExperimentConfig(shutdown_timeout=0.2)
    _, state = build_reference(config)
    session = ExpertSession(config, state, _worker_target=partial(fault_worker, mode=mode))
    with pytest.raises(SessionError, match=match) as caught:
        with session:
            # A duplicate can arrive after both valid replies; next request must
            # reject it rather than discarding stale traffic.
            session.forward(torch.randn(1, 16, 64))
            if mode == "duplicate":
                session.forward(torch.randn(1, 16, 64))
    if mode == "traceback":
        assert "Traceback (most recent call last)" in str(caught.value)
        assert "test_failures.py" in str(caught.value)
    assert session._closed and not session._processes
    session.close()
    with pytest.raises(SessionError, match="not running"):
        session.forward(torch.zeros(1, 16, 64))


@pytest.mark.parametrize("mode,match", [("startup-error", "intentional startup failure"), ("bad-digest", "integrity")])
def test_partial_startup_error_reaps_both_workers(mode, match):
    config = ExperimentConfig(shutdown_timeout=0.2)
    _, state = build_reference(config)
    session = ExpertSession(config, state, _worker_target=partial(fault_worker, mode=mode))
    with pytest.raises(SessionError, match=match):
        with session:
            pytest.fail("startup should have failed")
    assert session._closed and not session._processes


def test_changed_worker_weights_are_rejected_before_readiness(monkeypatch):
    config = ExperimentConfig(shutdown_timeout=0.2)
    _, state = build_reference(config)
    original_shard = state.shard

    def changed(worker):
        shard = original_shard(worker)
        if worker == 0:
            shard.down[0, 0, 0] += 1
        return shard

    monkeypatch.setattr(state, "shard", changed)
    with pytest.raises(SessionError, match="shard integrity mismatch"):
        with ExpertSession(config, state):
            pytest.fail("corrupt shard must never acknowledge readiness")


@pytest.mark.parametrize("mode", ["timeout", "hang-before-receive"])
def test_request_deadline_and_queue_backpressure_are_bounded(mode):
    config = ExperimentConfig(request_timeout=0.3, shutdown_timeout=0.2)
    _, state = build_reference(config)
    session = ExpertSession(config, state, _worker_target=partial(fault_worker, mode=mode))
    with session:
        if mode == "hang-before-receive":
            session._requests[0].put("occupy bounded queue")
        start = time.monotonic()
        with pytest.raises(SessionTimeout, match="deadline"):
            session.forward(torch.randn(1, 16, 64))
        assert time.monotonic() - start < 4
    assert not session._processes


def test_startup_timeout_is_bounded():
    config = ExperimentConfig(startup_timeout=0.001, shutdown_timeout=0.2)
    _, state = build_reference(config)
    session = ExpertSession(config, state)
    start = time.monotonic()
    with pytest.raises(SessionTimeout, match="deadline"):
        session.__enter__()
    assert time.monotonic() - start < 5
    assert session._closed and not session._processes


def test_second_process_start_failure_reaps_first(monkeypatch):
    import torch.multiprocessing as mp
    config = ExperimentConfig(shutdown_timeout=0.2)
    _, state = build_reference(config)
    process_class = mp.get_context("spawn").Process
    original_start = process_class.start
    started = []

    def start(process):
        if started:
            raise RuntimeError("second spawn failed")
        original_start(process)
        started.append(process.pid)

    monkeypatch.setattr(process_class, "start", start)
    session = ExpertSession(config, state)
    with pytest.raises(RuntimeError, match="second spawn failed"):
        session.__enter__()
    assert len(started) == 1 and session._closed and not session._processes


def test_exceptional_context_exit_cleans_up():
    config = ExperimentConfig()
    _, state = build_reference(config)
    session = ExpertSession(config, state)
    with pytest.raises(LookupError, match="caller failed"):
        with session:
            session.forward(torch.randn(1, 16, 64))
            raise LookupError("caller failed")
    assert session.exitcodes == (0, 0)
    session.close()
