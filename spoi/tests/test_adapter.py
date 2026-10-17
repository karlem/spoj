from dataclasses import replace

import pytest
import torch

from spoi.baseline import baseline
from spoi.config import ExperimentConfig
from spoi.partition import aggregate, pack
from spoi.qwen3_adapter import (CompatibilityError, FrozenState, build_reference,
                               compatibility, evaluate_shard, tensor_digest)


@pytest.mark.parametrize("platform,version,accepted", [
    ("linux", "2.14.1+cu130", True), ("darwin", "2.14.1", True),
    ("linux", "2.14.1", False), ("linux", "2.14.1+cpu", False),
    ("linux", "2.14.1+cu129", False), ("linux", "2.14.2+cu130", False),
    ("linux", "2.15.0.dev1+cu130", False),
    ("darwin", "2.14.1+cu130", False), ("win32", "2.14.1", False),
])
def test_exact_platform_build_guard(monkeypatch, platform, version, accepted):
    import spoi.qwen3_adapter as adapter
    monkeypatch.setattr(adapter.sys, "platform", platform)
    monkeypatch.setattr(adapter.torch, "__version__", version)
    if accepted:
        assert compatibility()["torch"] == version
    else:
        with pytest.raises(CompatibilityError, match="unsupported"):
            compatibility()


@pytest.mark.parametrize("changes", [
    {"hidden_size": 0}, {"moe_intermediate_size": -1}, {"num_experts": 0},
    {"threads": 0}, {"hidden_size": True}, {"top_k": 0}, {"top_k": 5},
    {"partitions": 1}, {"partitions": 3}, {"hidden_act": "relu"},
    {"norm_topk_prob": 1}, {"seed": -1}, {"seed": 2**63},
    {"startup_timeout": 0}, {"request_timeout": float("inf")},
    {"shutdown_timeout": float("nan")}, {"placement": (0, 1)},
    {"placement": (0, 0, 1, 2)}, {"placement": (0, 0, 1, True)},
])
def test_config_rejects_invalid_before_allocation(changes):
    with pytest.raises(ValueError):
        ExperimentConfig(**changes)


def test_initialized_reference_snapshot_and_hash_are_reproducible():
    config = ExperimentConfig(seed=8)
    block, first = build_reference(config)
    other, second = build_reference(config)
    assert first.hash == second.hash
    _, different = build_reference(replace(config, seed=9))
    assert different.hash != first.hash
    exported = first.state_dict()
    assert tensor_digest(dict(reversed(list(exported.items())))) == first.hash
    for name, value in exported.items():
        assert torch.isfinite(value).all() and value.dtype == torch.float32
        assert value.device.type == "cpu" and torch.count_nonzero(value) == value.numel()
        torch.testing.assert_close(value, block.state_dict()[name], rtol=0, atol=0)
    exported["gate.weight"][0, 0] += 1
    assert tensor_digest(exported) != first.hash
    assert tensor_digest(first.state_dict()) == first.hash
    x = torch.randn(1, 16, 64)
    torch.testing.assert_close(baseline(block, x), baseline(other, x), rtol=0, atol=0)
    assert block.experts.config._experts_implementation == "eager"
    assert compatibility()["transformers"] == "5.20.1"


def test_version_source_and_state_guards(monkeypatch):
    config = ExperimentConfig()
    _, snapshot = build_reference(config)
    import spoi.qwen3_adapter as adapter
    with monkeypatch.context() as context:
        context.setattr(adapter.transformers, "__version__", "unexpected")
        with pytest.raises(CompatibilityError, match="unsupported"):
            build_reference(config)
    with monkeypatch.context() as context:
        context.setattr(adapter, "SOURCE_SHA256", "unexpected")
        with pytest.raises(CompatibilityError, match="unsupported"):
            build_reference(config)
    constructor = adapter.hf.Qwen3MoeSparseMoeBlock
    def unsupported_backend(hf_config):
        block = constructor(hf_config)
        block.experts.config._experts_implementation = "unexpected"
        return block
    with monkeypatch.context() as context:
        context.setattr(adapter.hf, "Qwen3MoeSparseMoeBlock", unsupported_backend)
        with pytest.raises(CompatibilityError, match="backend"):
            build_reference(config)
    bad = snapshot.state_dict()
    del bad["gate.weight"]
    with pytest.raises(CompatibilityError, match="keys"):
        FrozenState(config, bad)
    for invalid in (torch.zeros(4, 65), torch.zeros(4, 64, dtype=torch.float64), torch.full((4, 64), float("nan"))):
        bad = snapshot.state_dict()
        bad["gate.weight"] = invalid
        with pytest.raises(CompatibilityError):
            FrozenState(config, bad)


@pytest.mark.parametrize("experts", [1, 4, 5])
def test_shards_are_exact_compact_copies(experts):
    config = ExperimentConfig(num_experts=experts, top_k=1)
    _, snapshot = build_reference(config)
    exported = snapshot.state_dict()
    ids = []
    for worker in (0, 1):
        shard = snapshot.shard(worker)
        ids.extend(shard.expert_ids)
        torch.testing.assert_close(shard.gate_up, exported["experts.gate_up_proj"][list(shard.expert_ids)], rtol=0, atol=0)
        torch.testing.assert_close(shard.down, exported["experts.down_proj"][list(shard.expert_ids)], rtol=0, atol=0)
        assert shard.storage_bytes == tuple(t.numel()*4 for t in (shard.gate_up, shard.down))
        assert shard.actual_digest() == shard.digest and shard.state_hash == snapshot.hash
        if shard.gate_up.numel():
            shard.gate_up[0, 0, 0] += 1
            assert shard.actual_digest() != shard.digest
            assert tensor_digest(snapshot.state_dict()) == snapshot.hash
    assert sorted(ids) == list(range(experts)) and len(set(ids)) == experts


def test_changed_expert_values_cause_numerical_failure_if_integrity_is_bypassed():
    config = ExperimentConfig()
    block, snapshot = build_reference(config)
    x = torch.randn(1, 16, 64)
    _, weights, selected = snapshot.router()(x)
    assignments = pack(x, selected, weights, config.owners)
    shards = [snapshot.shard(w) for w in (0, 1)]
    for shard in shards:
        shard.down.mul_(3)
    actual = aggregate(x.shape, assignments, [evaluate_shard(shard, a.rows, a.expert_ids, a.weights)
                                             for shard, a in zip(shards, assignments, strict=True)])
    with pytest.raises(AssertionError):
        torch.testing.assert_close(actual, baseline(block, x), rtol=1e-5, atol=1e-6)
