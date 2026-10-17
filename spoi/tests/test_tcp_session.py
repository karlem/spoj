from dataclasses import replace
import itertools
from pathlib import Path
import socket
import time

import pytest
import torch

from spoi.config import ExperimentConfig
from spoi.qwen3_adapter import FrozenState, build_reference
from spoi.tcp_session import TCPSession, TCPError, owners_for
from spoi.tcp_wire import ProtocolError


CASES = list(itertools.product(range(1, 5), (0, 1), (1, 2), (False, True)))


@pytest.fixture(scope='class', params=CASES)
def running(request):
    workers, seed, top_k, norm = request.param
    block, state = build_reference(ExperimentConfig(num_experts=5, seed=seed, top_k=top_k, norm_topk_prob=norm))
    session = TCPSession(block, state, workers)
    with session:
        yield block, state, session
    assert session.exitcodes == [0]*workers


class TestSeededTCPParity:
    @pytest.mark.parametrize('shape', [(1, 16, 64), (1, 128, 64), (8, 128, 64)])
    def test_seeded_tcp_contribution_and_final_parity(self, running, shape):
        block, state, session = running
        x = torch.randn(shape, generator=torch.Generator().manual_seed(state.config.seed+121))
        pids = [r['pid'] for r in session.ready]
        value = session.forward(x)  # validates every HF contribution, coverage and final output
        with torch.inference_mode():
            torch.testing.assert_close(value, block(x), rtol=1e-5, atol=1e-6)
        assert [r['pid'] for r in session.ready] == pids and len(set(pids)) == session.count


def controlled():
    block, state = build_reference(ExperimentConfig(num_experts=5))
    values = state.state_dict()
    values['gate.weight'].zero_()
    for i in range(5): values['gate.weight'][i, i] = 4
    block.load_state_dict(values)
    return block, FrozenState(state.config, values)


def test_controlled_all_worker_and_zero_hit_trace_and_cleanup():
    block, state = controlled()
    session = TCPSession(block, state, trace=True)
    x = torch.zeros(1, 3, 64)
    for token, (a, b) in enumerate([(0, 2), (1, 4), (2, 4)]):
        x[0, token, a], x[0, token, b] = 2, 1
    with session:
        session.forward(x)
        assert {c['worker'] for c in session.records[0]['contributions']} == {0, 1, 2}
        y = torch.zeros(1, 1, 64); y[0, 0, 0], y[0, 0, 1] = 2, 1
        session.forward(y)
        assert {c['worker'] for c in session.records[1]['contributions']} == {0}
        # All workers, including zero-hit, returned matching explicit frames.
        assert sum(e['meta']['kind'] == 'result' for e in session.events) == 6
        addresses = [s.getsockname() for s in session.sockets]
    assert session.exitcodes == [0, 0, 0]
    assert all(p.poll() == 0 for p in session.processes)
    assert all(s.fileno() == -1 for s in session.sockets+session.listeners)
    session.close()
    with pytest.raises(TCPError, match='not running'): session.forward(x)
    # Coordinator listener ports are released (SO_REUSEADDR for TIME_WAIT semantics).
    for address in addresses:
        probe = socket.socket(); probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: probe.bind(address)
        finally: probe.close()


def test_empty_worker_partition_and_empty_tokens():
    block, state = build_reference(ExperimentConfig(num_experts=1, top_k=1))
    with TCPSession(block, state, workers=3) as session:
        assert [r['ids'] for r in session.ready] == [[0], [], []]
        session.forward(torch.randn(1, 2, 64))
        assert session.forward(torch.empty(1, 0, 64)).shape == (1, 0, 64)


FAULTS = [
    ('startup-crash', 'truncated'), ('startup-stall', 'timed out|deadline'),
    ('bad-ready', 'readiness'), ('corrupt-shard', 'digest'), ('wrong-shard-shape', 'shape'),
    ('wrong-run', 'identity'), ('wrong-request', 'identity'), ('wrong-worker', 'identity'),
    ('missing-slot', 'assignment'), ('duplicate-slot', 'assignment'), ('changed-weight', 'assignment'),
    ('bad-contribution', 'HF contribution'), ('swap-contributions', 'HF contribution'),
    ('wrong-output-dtype', 'dtype'), ('duplicate', 'identity'),
    ('duplicate-final', 'shutdown'), ('bad-stopped', 'shutdown'), ('nonzero-stop', 'shutdown'),
    ('disconnect', 'truncated|reset'), ('truncated-result', 'truncated|reset'), ('stall', 'timed out|deadline'),
]


@pytest.mark.parametrize('mode,match', FAULTS)
def test_injected_fault_fails_and_reaps_children(monkeypatch, mode, match):
    monkeypatch.setenv('SPOI_TCP_FAULT', mode)
    block, state = build_reference(ExperimentConfig(num_experts=5, startup_timeout=20, request_timeout=0.5, shutdown_timeout=0.15))
    if mode == 'startup-stall':
        state = FrozenState(replace(state.config, startup_timeout=4), state.state_dict())
    session = TCPSession(block, state, workers=1, _worker_script=str(Path(__file__).with_name('tcp_fault_worker.py')))
    expected = AssertionError if mode in ('bad-contribution', 'swap-contributions') else (TCPError, ProtocolError, OSError)
    start = time.monotonic()
    with pytest.raises(expected, match=match):
        with session:
            x = torch.randn(1, 6, 64)
            session.forward(x)
            if mode == 'duplicate': session.forward(x)
    assert time.monotonic()-start < 22
    assert session.closed and all(p.poll() is not None for p in session.processes)
    assert all(s.fileno() == -1 for s in session.sockets+session.listeners)
    session.close()


def test_shutdown_stall_has_collective_deadline(monkeypatch):
    monkeypatch.setenv('SPOI_TCP_FAULT', 'shutdown-stall')
    block, state = build_reference(ExperimentConfig(shutdown_timeout=0.15))
    session = TCPSession(block, state, workers=1, _worker_script=str(Path(__file__).with_name('tcp_fault_worker.py')))
    with pytest.raises(TCPError, match='shutdown'):
        with session: session.forward(torch.randn(1, 2, 64))
    assert session.exitcodes[0] != 0 and session.processes[0].poll() is not None


@pytest.mark.parametrize('workers', [0, 5, -1, True, 1.5])
def test_worker_bounds(workers):
    with pytest.raises(ValueError): owners_for(5, workers)
