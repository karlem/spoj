"""Bounded design arithmetic; no model or hardware performance is measured."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import random


def direct(q, keys, values, positions):
    """Independent monolithic reference; None means no visible key."""
    if not positions:
        return None
    logits = [sum(a * b for a, b in zip(q, keys[i])) / math.sqrt(len(q))
              for i in positions]
    peak = max(logits)
    probabilities = [math.exp(x - peak) for x in logits]
    denominator = sum(probabilities)
    return [sum(probabilities[j] * values[i][d]
                for j, i in enumerate(positions)) / denominator
            for d in range(len(q))]


def summarize(q, keys, values, positions):
    """Streaming stable (m, l, u) summary; u is unnormalized weighted V."""
    if not positions:
        return None
    peak, total, vector = -math.inf, 0.0, [0.0] * len(q)
    for i in positions:
        score = math.fsum(q[d] * keys[i][d] for d in range(len(q))) / math.sqrt(len(q))
        next_peak = max(peak, score)
        rescale, weight = math.exp(peak - next_peak), math.exp(score - next_peak)
        vector = [v * rescale + weight * x for v, x in zip(vector, values[i])]
        total = total * rescale + weight
        peak = next_peak
    return peak, total, vector


def merge(a, b):
    if a is None:
        return b
    if b is None:
        return a
    m = max(a[0], b[0])
    wa, wb = math.exp(a[0] - m), math.exp(b[0] - m)
    return m, wa * a[1] + wb * b[1], [wa*x + wb*y for x, y in zip(a[2], b[2])]


def finish(summary):
    return None if summary is None else [v / summary[1] for v in summary[2]]


def verify():
    rng = random.Random(20261018)
    hq, hkv, dim = 4, 2, 3
    cases, max_error = 0, 0.0
    empty_cases = 0
    for length, nshards, scale in itertools.product((0, 1, 17), (1, 2, 4), (1, 10000)):
        keys = [[[rng.uniform(-1, 1) * scale for _ in range(dim)]
                 for _ in range(length)] for _ in range(hkv)]
        values = [[[rng.uniform(-1, 1) for _ in range(dim)]
                   for _ in range(length)] for _ in range(hkv)]
        queries = [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(hq)]
        for visible in (list(range(length)), list(range(0, length, 2)), []):
            for head, q in enumerate(queries):
                kvhead = head // (hq // hkv)
                expected = direct(q, keys[kvhead], values[kvhead], visible)
                summaries = [summarize(q, keys[kvhead], values[kvhead],
                                      [i for i in visible if i % nshards == shard])
                             for shard in range(nshards)]
                for order in (range(nshards), reversed(range(nshards))):
                    merged = None
                    for shard in order:
                        merged = merge(merged, summaries[shard])
                    actual = finish(merged)
                    cases += 1
                    if expected is None:
                        assert actual is None
                        empty_cases += 1
                    else:
                        assert all(math.isfinite(x) for x in actual)
                        error = max(abs(a-b) for a, b in zip(actual, expected))
                        max_error = max(error, max_error)
                        assert error <= 1e-10, (length, nshards, scale, head, error)
    # GQA uses contiguous groups in this declared layout, not head % hkv.
    keys = [[[1.0, 0.0, 0.0]], [[0.0, 1.0, 0.0]]]
    values = [[[1.0, 2.0, 3.0]], [[7.0, 8.0, 9.0]]]
    q = [1.0, 1.0, 1.0]
    correct = direct(q, keys[0], values[0], [0])
    wrong = direct(q, keys[1], values[1], [0])
    assert max(abs(a-b) for a, b in zip(correct, wrong)) > 1
    return dict(comparisons=cases, empty_comparisons=empty_cases,
                max_absolute_error=max_error, tolerance=1e-10,
                deliberate_wrong_gqa_mapping_detected=True,
                scope="Binary64 fixture only; no GPU kernel, FP16 or inference validation")


def ledger():
    layers, hq, hkv, dim, kv_bytes, summary_bytes = 32, 32, 8, 128, 2, 4
    state_per_token = layers * 2 * hkv * dim * kv_bytes
    query = hq * dim * kv_bytes
    summary = hq * (dim + 2) * summary_bytes
    append = 2 * hkv * dim * kv_bytes
    rows = []
    for context, remote in itertools.product((8192, 65536), (1, 3, 7)):
        total_kv = context * state_per_token
        rows.append(dict(context=context, remote_workers=remote,
                         total_kv_bytes=total_kv,
                         ideal_equal_shard_bytes=total_kv // (remote+1),
                         raw_remote_kv_copy_bytes_per_decode_token=total_kv*remote//(remote+1),
                         query_broadcast_bytes_per_decode_token=layers*remote*query,
                         summary_return_bytes_per_decode_token=layers*remote*summary,
                         new_kv_append_bytes_if_remote=layers*append,
                         caveat="Payload only; excludes framing, registration, copies, workspaces and recompute. KV scan remains distributed."))
    return dict(kv_bytes_per_token_all_layers=state_per_token,
                branch_example=dict(prefix_tokens=8192, branches=4, suffix_tokens_each=1024,
                                    naive_copy_bytes=4*(8192+1024)*state_per_token,
                                    existing_prefix_sharing_bytes=(8192+4*1024)*state_per_token,
                                    proposed_prefix_sharing_bytes=(8192+4*1024)*state_per_token,
                                    saving_over_existing_sharing=0),
                per_remote_per_layer=dict(query_bytes=query, summary_bytes=summary),
                new_kv_append_bytes_per_layer_if_remote=append,
                dependent_32_layer_RTT_floor_ms={str(rtt): layers*rtt for rtt in (0.02, 0.2, 1)},
                little_law_example=dict(blocked_arrivals_per_s=4, mean_tool_wait_s=20,
                                        mean_blocked_sessions=80, gib_per_session=1,
                                        mean_retained_gib=80,
                                        scope="Stable-flow illustrative averages, not tail bounds; admission changes arrivals."),
                rows=rows)


if __name__ == "__main__":
    print(json.dumps(dict(seed=20261018, checks=verify(), ledger=ledger(),
                         source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2))
