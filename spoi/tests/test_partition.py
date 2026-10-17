import pytest
import torch

from spoi.config import ExperimentConfig
from spoi.partition import aggregate, pack
from spoi.qwen3_adapter import build_reference


def test_token_slot_coverage_with_duplicate_token_assignments():
    x = torch.arange(3*4, dtype=torch.float32).reshape(1, 3, 4)
    selected = torch.tensor([[0, 1], [1, 4], [4, 2]])
    weights = torch.tensor([[0.7, 0.3], [0.6, 0.4], [0.9, 0.1]])
    owners = ExperimentConfig(num_experts=5).owners
    assignments = pack(x, selected, weights, owners)
    all_pairs = []
    for worker, a in enumerate(assignments):
        all_pairs.extend(zip(a.token_indices.tolist(), a.slot_indices.tolist()))
        assert all(owners[e] == worker for e in a.expert_ids.tolist())
        torch.testing.assert_close(a.rows, x.reshape(-1, 4)[a.token_indices])
        torch.testing.assert_close(a.weights, weights[a.token_indices, a.slot_indices])
    assert sorted(all_pairs) == [(token, slot) for token in range(3) for slot in range(2)]
    assert len(set(all_pairs)) == 6
    # Token 0 has both experts on worker 0; token 1 crosses workers.
    actual = aggregate(x.shape, assignments, [a.rows*a.weights[:, None] for a in assignments])
    torch.testing.assert_close(actual, x)


@pytest.mark.parametrize("norm", [False, True])
@pytest.mark.parametrize("top_k", [1, 2])
def test_actual_router_matches_installed_selection_semantics(norm, top_k):
    config = ExperimentConfig(top_k=top_k, norm_topk_prob=norm, num_experts=5)
    block, state = build_reference(config)
    x = torch.randn(1, 16, 64)
    logits, actual_weights, actual_ids = state.router()(x)
    ref_logits, ref_weights, ref_ids = block.gate(x)
    torch.testing.assert_close(logits, ref_logits, rtol=0, atol=0)
    torch.testing.assert_close(actual_weights, ref_weights, rtol=0, atol=0)
    assert torch.equal(actual_ids, ref_ids)
    values, ids = torch.topk(torch.softmax(logits, dtype=torch.float32, dim=-1), top_k, dim=-1)
    if norm:
        values = values / values.sum(dim=-1, keepdim=True)
    assert torch.equal(ids, actual_ids)
    torch.testing.assert_close(actual_weights, values, rtol=0, atol=0)
