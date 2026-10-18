"""Exact-rational sensitivity arithmetic, not an inference/runtime benchmark."""
from __future__ import annotations

import hashlib
import itertools
import json
from fractions import Fraction
from pathlib import Path

GIB = 1 << 30


def nonnegative(value, name, *, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a numeric cost")
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name}: finite number required") from exc
    if result < 0 or (positive and result == 0):
        raise ValueError(f"{name}: {'positive' if positive else 'nonnegative'} required")
    return result


def kv_bytes(layers, kv_heads, head_dim, scalar_bytes, tokens):
    values = [layers, kv_heads, head_dim, scalar_bytes, tokens]
    if any(type(v) is not int or v <= 0 for v in values):
        raise ValueError("KV dimensions must be positive integers")
    result = 2
    for value in values:
        result *= value
    return result


def evaluate(*, size_bytes, tokens, wait_s, write_gib_s, read_gib_s,
             prefill_tokens_s, domain, allocator_releases, compatible=True,
             export_fixed_s='0.005', restore_fixed_s='0.005',
             replay_fixed_s='0.02', min_saving='0.25', max_resume_s='0.25'):
    if type(size_bytes) is not int or size_bytes <= 0:
        raise ValueError("size_bytes must be a positive integer")
    if type(tokens) is not int or tokens <= 0:
        raise ValueError("tokens must be a positive integer")
    if domain not in ('separate', 'same'):
        raise ValueError("unknown capacity domain")
    if type(allocator_releases) is not bool or type(compatible) is not bool:
        raise ValueError("capability flags must be boolean")
    w = nonnegative(wait_s, 'wait', positive=True)
    bw = nonnegative(write_gib_s, 'write bandwidth', positive=True)
    br = nonnegative(read_gib_s, 'read bandwidth', positive=True)
    rate = nonnegative(prefill_tokens_s, 'prefill', positive=True)
    ef = nonnegative(export_fixed_s, 'export overhead')
    rf = nonnegative(restore_fixed_s, 'restore overhead')
    pf = nonnegative(replay_fixed_s, 'replay overhead')
    threshold = nonnegative(min_saving, 'saving threshold')
    if threshold > 1:
        raise ValueError("saving threshold exceeds one")
    latency_limit = nonnegative(max_resume_s, 'resume limit')
    s = Fraction(size_bytes, GIB)
    export = ef + s / bw
    restore = rf + s / br
    replay = pf + Fraction(tokens) / rate
    slot_saved = s * max(w - export, 0)
    export_delay = max(export - w, 0) + restore

    def outcome(policy, slot_credit, physical_credit, delay, transfer, checkpoint,
                source_peak, total_peak, post_return_charge):
        slot_fraction = slot_credit / (s * w)
        physical_fraction = physical_credit / (s * w)
        return {
            'policy': policy,
            'reusable_slot_saved_gib_s': float(slot_credit),
            'reusable_slot_saving_fraction': float(slot_fraction),
            'physical_saved_gib_s': float(physical_credit),
            'physical_saving_fraction': float(physical_fraction),
            'added_resume_seconds': float(delay),
            'kv_transfer_bytes': transfer,
            'checkpoint_bytes': checkpoint,
            'source_domain_payload_peak_bytes': source_peak,
            'total_live_payload_peak_bytes': total_peak,
            'post_return_kv_reservation_gib_s_upper_bound': float(post_return_charge),
            'slot_economic_candidate': bool(compatible and slot_fraction >= threshold
                                             and delay <= latency_limit),
            'physical_economic_candidate': bool(compatible and physical_fraction >= threshold
                                                 and delay <= latency_limit),
            'correctness': 'unverified' if compatible else 'incompatible_metadata',
            'accepted_inference_result': False,
        }

    return {
        'export_seconds': float(export),
        'restore_seconds': float(restore),
        'replay_seconds': float(replay),
        'min_wait_for_25pct_slot_saving_seconds': float(export / Fraction(3, 4)),
        'token_transcript_bytes': 4 * tokens,
        'policies': [
            outcome('resident', 0, 0, Fraction(0), 0, 0,
                    size_bytes, size_bytes, Fraction(0)),
            outcome('replay', s * w, s * w if allocator_releases else 0,
                    replay, 0, 0, size_bytes, size_bytes, s * replay),
            outcome('snapshot', slot_saved,
                    slot_saved if allocator_releases and domain == 'separate' else 0,
                    export_delay, 2 * size_bytes, size_bytes,
                    size_bytes if domain == 'separate' else 2 * size_bytes,
                    2 * size_bytes, s * export_delay),
        ],
    }


def run(config):
    rows = []
    for tokens, wait, bandwidth, rate, domain, releases in itertools.product(
            config['contexts'], config['wait_seconds'], config['bandwidth_gib_s'],
            config['prefill_tokens_s'], config['capacity_domains'],
            config['allocator_releases']):
        size = kv_bytes(config['layers'], config['kv_heads'], config['head_dim'],
                        config['scalar_bytes'], tokens)
        rows.append({
            'tokens': tokens, 'kv_bytes': size, 'wait_seconds': wait,
            'bandwidth_gib_s': bandwidth, 'prefill_tokens_s': rate,
            'domain': domain, 'allocator_releases': releases,
            **evaluate(size_bytes=size, tokens=tokens, wait_s=wait,
                       write_gib_s=bandwidth, read_gib_s=bandwidth,
                       prefill_tokens_s=rate, domain=domain,
                       allocator_releases=releases, compatible=config['state_compatible'],
                       export_fixed_s=config['export_fixed_seconds'],
                       restore_fixed_s=config['restore_fixed_seconds'],
                       replay_fixed_s=config['replay_fixed_seconds'],
                       min_saving=config['min_wait_saving_fraction'],
                       max_resume_s=config['max_resume_seconds'])})
    counts = {policy: {gate: sum(p[gate] for row in rows for p in row['policies']
                                  if p['policy'] == policy)
                       for gate in ('slot_economic_candidate', 'physical_economic_candidate')}
              for policy in ('resident', 'replay', 'snapshot')}
    return {'label': 'assumed-input exact arithmetic; not measured performance',
            'correctness': 'unverified for every cell',
            'case_count': len(rows), 'candidate_counts_not_probabilities': counts,
            'rows': rows}


if __name__ == '__main__':
    source = Path(__file__).with_name('inputs.json')
    data = source.read_bytes()
    result = run(json.loads(data))
    result['input_sha256'] = hashlib.sha256(data).hexdigest()
    print(json.dumps(result, sort_keys=True, indent=2))
