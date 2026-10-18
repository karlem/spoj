"""Attention-reduction algebra and byte-budget probe; no remote execution.

Torch float32 CPU tensors are compared with direct PyTorch SDPA. Communication
sizes below describe a separate declared FP16-cache/FP32-partial thought model.
"""
import json
import math
import platform

import torch
import torch.nn.functional as F

RTOL, ATOL = 1e-5, 1e-6


def local_stats(q, k, v, mask):
    if k.shape[-2] == 0:
        shape = q.shape[:-1]
        return (torch.full(shape, -torch.inf), torch.zeros(shape), torch.zeros_like(q))
    groups = q.shape[1] // k.shape[1]
    k = k.repeat_interleave(groups, dim=1)
    v = v.repeat_interleave(groups, dim=1)
    logits = (q @ k.transpose(-1, -2)) / math.sqrt(q.shape[-1])
    logits = logits.masked_fill(~mask, -torch.inf)
    maximum = logits.amax(-1)
    safe_max = torch.where(torch.isfinite(maximum), maximum, 0)
    exponentials = torch.exp(logits - safe_max[..., None])
    return maximum, exponentials.sum(-1), exponentials @ v


def merge(parts):
    maximum = torch.stack([p[0] for p in parts]).amax(0)
    safe_max = torch.where(torch.isfinite(maximum), maximum, 0)
    denom, numer = torch.zeros_like(maximum), torch.zeros_like(parts[0][2])
    for m, z, u in parts:
        finite = torch.isfinite(m)
        alpha = torch.exp(torch.where(finite, m - safe_max, 0)) * finite
        denom += alpha * z
        numer += alpha[..., None] * u
    return numer / torch.where(denom > 0, denom, 1)[..., None]


def reference(q, k, v, mask):
    groups = q.shape[1] // k.shape[1]
    return F.scaled_dot_product_attention(
        q, k.repeat_interleave(groups, 1), v.repeat_interleave(groups, 1),
        attn_mask=mask, dropout_p=0.0)


def parts_for(q, k, v, mask, shards):
    # Coverage is part of the contract; duplicate or omitted KV positions fail.
    flat = sorted(i for shard in shards for i in shard)
    assert flat == list(range(k.shape[-2]))
    return [local_stats(q, k[:, :, ids], v[:, :, ids], mask[..., ids]) for ids in shards]


def main():
    cases = []
    shardings = [list(map(list, (range(0, 6), range(6, 11), range(11, 17)))),
                 [list(range(i, 17, 3)) for i in range(3)],
                 [list(range(9)), [], list(range(9, 17))]]
    sample = None
    for seed in [0, 1, 7, 42]:
        generator = torch.Generator().manual_seed(seed)
        q = torch.randn(2, 4, 4, 8, generator=generator)
        k = torch.randn(2, 2, 17, 8, generator=generator)
        v = torch.randn(2, 2, 17, 8, generator=generator)
        mask = (torch.arange(17)[None, :] <= torch.tensor([0, 3, 8, 16])[:, None])[None, None]
        mask[:, :, 2] = False  # Deliberately all-masked query; expected output zero.
        oracle = reference(q, k, v, mask)
        for n, shards in enumerate(shardings):
            parts = parts_for(q, k, v, mask, shards)
            actual = merge(parts)
            torch.testing.assert_close(actual, oracle, rtol=RTOL, atol=ATOL)
            cases.append({"seed": seed, "shard_sizes": list(map(len, shards)),
                          "max_absolute_error": (actual - oracle).abs().max().item()})
            if sample is None:
                sample = {"query": q[0, 0, 1].tolist(), "allowed_kv_positions": [0, 1, 2, 3],
                          "shards": shards, "null_maximum_means": "minus infinity; no allowed keys in this shard",
                          "local_m_z_u": [{"m": (p[0][0, 0, 1].item() if torch.isfinite(p[0][0, 0, 1]) else None),
                                           "z": p[1][0, 0, 1].item(),
                                           "u": p[2][0, 0, 1].tolist()} for p in parts],
                          "merged_output": actual[0, 0, 1].tolist(),
                          "direct_sdpa_output": oracle[0, 0, 1].tolist()}
    # A deterministic numerical-stability case, with mutually unequal shard maxima.
    q = torch.tensor([[[[1., 0.]]]])
    k = torch.tensor([[[[1000., 0.], [-1000., 0.]]]])
    v = torch.tensor([[[[1., 0.], [0., 1.]]]])
    mask = torch.ones(1, 1, 1, 2, dtype=torch.bool)
    parts = parts_for(q, k, v, mask, [[0], [1]])
    actual, oracle = merge(parts), reference(q, k, v, mask)
    torch.testing.assert_close(actual, oracle, rtol=RTOL, atol=ATOL)
    cases.append({"case": "extreme_shard_maxima", "max_absolute_error": (actual-oracle).abs().max().item()})
    bad_mean = torch.stack([u/z[..., None] for _, z, u in parts]).mean(0)
    failures = []
    try:
        torch.testing.assert_close(bad_mean, oracle, rtol=RTOL, atol=ATOL)
    except AssertionError:
        failures.append({"fault": "average_normalized_shard_outputs", "validation": "rejected",
                         "max_absolute_error": (bad_mean-oracle).abs().max().item()})
    else:
        raise AssertionError("fault injection escaped validation")
    # Mask identity is essential even when the reduction formula is correct.
    causal = torch.tensor([[[[False, True]]]])
    bad_mask = merge(parts_for(q, k, v, mask, [[0], [1]]))
    masked_oracle = reference(q, k, v, causal)
    try:
        torch.testing.assert_close(bad_mask, masked_oracle, rtol=RTOL, atol=ATOL)
    except AssertionError:
        failures.append({"fault": "ignore_required_attention_mask", "validation": "rejected",
                         "max_absolute_error": (bad_mask-masked_oracle).abs().max().item()})
    else:
        raise AssertionError("mask fault escaped validation")
    # Hypothetical wire representation, not bytes observed on any transport.
    layers, kv_heads, q_heads, dim, context, shards = 32, 8, 32, 128, 32768, 2
    kv_bytes = 2*layers*kv_heads*dim*context*2
    query_bytes = layers*shards*q_heads*dim*2
    partial_bytes = layers*shards*q_heads*dim*4
    stats_bytes = layers*shards*q_heads*2*4
    append_bytes = 2*layers*kv_heads*dim*2
    wire_total = query_bytes+partial_bytes+stats_bytes+append_bytes
    assert kv_bytes == 4*1024**3 and wire_total == 1720320
    print(json.dumps({"environment": {"python": platform.python_version(), "torch": torch.__version__},
                      "oracle": "direct PyTorch scaled_dot_product_attention, CPU float32",
                      "tolerances": {"rtol": RTOL, "atol": ATOL},
                      "positive_cases": cases, "bounded_observed_tensor_trace": sample,
                      "negative_cases": failures,
                      "derived_byte_model": {"provenance": "declared hypothetical dimensions/formats; not measured",
                        "layers": layers, "kv_heads": kv_heads, "query_heads": q_heads,
                        "head_dim": dim, "context_tokens": context, "context_shards": shards,
                        "kv_and_query_format": "FP16", "partial_output_and_stats_format": "FP32",
                        "full_kv_bytes": kv_bytes, "per_decode_query_bytes": query_bytes,
                        "per_decode_partial_bytes": partial_bytes, "per_decode_stats_bytes": stats_bytes,
                        "per_decode_kv_append_bytes": append_bytes, "per_decode_total_bytes": wire_total,
                        "serial_layer_rpc_count": layers, "assumed_RTT_seconds": .0005,
                        "serial_RTT_floor_seconds": layers*.0005,
                        "read_full_kv_at_assumed_1GBps_seconds": kv_bytes/1e9},
                      "limits": ["algebra validation only; no sockets, serialization or worker execution",
                                 "no model weights, generation, checkpoint, RL training or JEV API calls",
                                 "no measured performance, GPU/Mac acceptance, distributed cache coherence or capacity result",
                                 "FP32 tensor parity does not validate hypothetical FP16 wire representation",
                                 "no stale/mixed-model KV sharing permitted by this experiment"]}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
