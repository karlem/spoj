import itertools

import pytest
import torch

from spoi.baseline import baseline
from spoi.config import ExperimentConfig
from spoi.coordinator import ExpertSession, SessionError
from spoi.qwen3_adapter import FrozenState, build_reference


CONFIGS = list(itertools.product((0, 1), (1, 2), (False, True), (4, 5)))
SHAPES = [(1, 16, 64), (1, 128, 64), (8, 128, 64)]


@pytest.fixture(scope="module", params=CONFIGS, ids=lambda c: f"seed{c[0]}-k{c[1]}-norm{c[2]}-E{c[3]}")
def running_reference(request):
    seed, top_k, norm, experts = request.param
    config = ExperimentConfig(seed=seed, top_k=top_k, norm_topk_prob=norm, num_experts=experts)
    block, state = build_reference(config)
    with ExpertSession(config, state) as session:
        yield block, state, session
    assert session.exitcodes == (0, 0)


@pytest.mark.parametrize("shape", SHAPES)
def test_48_process_parity_scenarios(running_reference, shape):
    block, state, session = running_reference
    x = torch.randn(shape, generator=torch.Generator().manual_seed(state.config.seed + 77))
    pids = session.worker_pids
    result = session.forward(x)
    torch.testing.assert_close(result.output, baseline(block, x), rtol=1e-5, atol=1e-6)
    assert sum(result.assignment_counts) == shape[0]*shape[1]*state.config.top_k
    assert all(count > 0 for count in result.assignment_counts)
    assert session.worker_pids == pids and len(set(pids)) == 2
    assert all(duration >= 0 for duration in result.worker_compute_ns)
    assert all(duration >= 0 for duration in result.timings_ns.values())
    assert all(worker["state_hash"] == state.hash for worker in session.workers)
    assert sorted(e for worker in session.workers for e in worker["expert_ids"]) == list(range(state.config.num_experts))


@pytest.mark.parametrize("active_experts", [(0, 1), (2, 3), (0, 2)])
def test_controlled_zero_and_both_worker_hits(active_experts):
    config = ExperimentConfig()
    block, snapshot = build_reference(config)
    values = snapshot.state_dict()
    values["gate.weight"].zero_()
    for rank, expert in enumerate(active_experts):
        values["gate.weight"][expert, 0] = 4-rank
    block.load_state_dict(values)
    state = FrozenState(config, values)
    x = torch.zeros(1, 16, 64)
    x[:, :, 0] = 1
    with ExpertSession(config, state) as session:
        result = session.forward(x)
        torch.testing.assert_close(result.output, baseline(block, x), rtol=1e-5, atol=1e-6)
        assert result.assignment_counts == tuple(sum(config.owners[e] == w for e in active_experts)*16 for w in (0, 1))


def test_single_expert_empty_partition_and_empty_token_batch():
    config = ExperimentConfig(num_experts=1, top_k=1)
    block, state = build_reference(config)
    session = ExpertSession(config, state)
    with pytest.raises(SessionError, match="not running"):
        session.forward(torch.zeros(1, 16, 64))
    with session:
        for x in (torch.randn(1, 16, 64), torch.empty(1, 0, 64)):
            actual = session.forward(x)
            torch.testing.assert_close(actual.output, baseline(block, x), rtol=1e-5, atol=1e-6)
            assert actual.assignment_counts[1] == 0
    session.close()
    with pytest.raises(SessionError):
        session.forward(torch.zeros(1, 16, 64))


def test_concurrent_calls_are_rejected_without_disrupting_session():
    config = ExperimentConfig()
    _, state = build_reference(config)
    with ExpertSession(config, state) as session:
        session._forward_lock.acquire()
        try:
            with pytest.raises(SessionError, match="concurrent"):
                session.forward(torch.zeros(1, 16, 64))
        finally:
            session._forward_lock.release()
        assert session.forward(torch.zeros(1, 16, 64)).request_id == 1
