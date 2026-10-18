"""Independent accounting/source audit and adversarial arithmetic only."""
import decimal
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT = Path('/workspace/spoj-inference-designs-review/research/manager/inference-designs-20261018')
OUT = Path('/workspace/scratch/inference-validator')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text())
author = read(ROOT / 'evidence/analysis-attempt-1/stdout.json')
rerun = read(OUT / 'author-rerun.stdout.json')
assert author == rerun
assert (ROOT / 'evidence/analysis-attempt-1/stdout.json').read_bytes() == (OUT / 'author-rerun.stdout.json').read_bytes()
assert author['checks']['comparisons'] == 3*3*2*3*4*2 == 432
assert author['checks']['empty_comparisons'] == 3*2*3*4*2 + 2*3*2*4*2 == 240
ledger = author['ledger']
assert ledger['kv_bytes_per_token_all_layers'] == 32*2*8*128*2 == 131072
assert ledger['per_remote_per_layer'] == {'query_bytes': 8192, 'summary_bytes': 16640}
assert ledger['new_kv_append_bytes_per_layer_if_remote'] == 4096
assert (8192+16640)*32 == 794624
b = ledger['branch_example']
assert b['naive_copy_bytes'] == int(4.5*2**30)
assert b['existing_prefix_sharing_bytes'] == b['proposed_prefix_sharing_bytes'] == int(1.5*2**30)
assert b['saving_over_existing_sharing'] == 0
for row in ledger['rows']:
    n, r = row['context'], row['remote_workers']
    assert row['total_kv_bytes'] == n*131072
    assert row['ideal_equal_shard_bytes'] == n*131072//(r+1)
    assert row['raw_remote_kv_copy_bytes_per_decode_token'] == n*131072*r//(r+1)
    assert row['query_broadcast_bytes_per_decode_token'] == 32*r*8192
    assert row['summary_return_bytes_per_decode_token'] == 32*r*16640
    assert row['new_kv_append_bytes_if_remote'] == 131072
assert ledger['dependent_32_layer_RTT_floor_ms'] == {'0.02': .64, '0.2': 6.4, '1': 32}
ll = ledger['little_law_example']
assert ll['blocked_arrivals_per_s']*ll['mean_tool_wait_s'] == ll['mean_blocked_sessions'] == 80
assert ll['mean_retained_gib'] == 80

source_checks = {}
for family in ('fundamentals', 'prior-art'):
    rawroot = Path('/workspace/scratch/inference-'+family)
    public = ROOT / 'sources' / family
    if family == 'fundamentals':
        records = read(public / 'provenance.json')['records']
        successful = [r for r in records if r.get('status') == 200]
        rawpaths = {r['url']: rawroot / r['path'] for r in successful}
        for r in successful:
            p = rawpaths[r['url']]
            assert sha(p) == r['sha256'], p
            assert p.stat().st_size == r['bytes'], p
        excerpts = read(public / 'public-evidence.json')['evidence']
        for e in excerpts:
            p = rawpaths[e['url']]
            assert sha(p) == e['sha256']
            if p.suffix == '.pdf':
                p = p.with_suffix('.txt')
            assert ' '.join(e['bounded_excerpt'].split()) in ' '.join(p.read_text().split()), e['locator']
        manifests = [public / 'MANIFEST.sha256']
    else:
        records = read(public / 'manifest.json')
        successful = [r for r in records if r.get('status') == 200]
        rawpaths = {r['id']: Path(r['raw_path']) for r in successful}
        for r in successful:
            p = rawpaths[r['id']]
            assert sha(p) == r['sha256'], p
            assert p.stat().st_size == r['size'], p
        excerpts = read(public / 'public-evidence.json')
        for e in excerpts:
            p = rawpaths[e['id']]
            assert sha(p) == e['sha256']
            lines = p.read_text().splitlines()
            for ex in e.get('extracts', []):
                assert lines[ex['line']-1] == ex['text'], (e['id'], ex['line'])
        manifests = [rawroot / 'SHA256SUMS']
    manifest_files = 0
    for manifest in manifests:
        for line in manifest.read_text().splitlines():
            digest, rel = line.split('  ', 1)
            p = manifest.parent / rel
            assert sha(p) == digest, p
            manifest_files += 1
    source_checks[family] = dict(retrieval_records=len(records), raw_files_verified=len(successful),
                                retained_failed_retrievals=len(records)-len(successful),
                                excerpt_records_verified=len(excerpts), manifest_files_verified=manifest_files,
                                raw_bytes_verified=sum(p.stat().st_size for p in rawpaths.values()))

spec = importlib.util.spec_from_file_location('candidate', ROOT / 'check_designs.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
decimal.getcontext().prec = 90
D = decimal.Decimal
fixtures = [
    ([0.0]*7, [1., -1., .5, -.25, .75, -.125, .0625]),
    ([-1000., -200., -1., 0., 1., 200., 1000.], [float(i)/8 for i in range(7)]),
    ([-10000.]*7, [float(i-3)/8 for i in range(7)]),
    ([1000., 1000., -1000., 999., 998., 0., 999.5], [.125, -.25, .5, -.75, 1., -.5, .25]),
    ([0., 1e-12, -1e-12, 2e-12, -2e-12, 3e-12, -3e-12], [.125, -.25, .5, -.75, 1., -.5, .25]),
    ([10000., 10000.125, 9999.875, 10000.25, 9999.75, 10000.5, 9999.5], [.125, -.25, .5, -.75, 1., -.5, .25]),
    ([-10000., -9999.875, -10000.125, -9999.75, -10000.25, -9999.5, -10000.5], [.125, -.25, .5, -.75, 1., -.5, .25]),
    ([80., 79., 78., -80., 1., 0., -1.], [1., -1., .5, -.25, .75, -.125, .0625]),
]
comparisons, max_error = 0, 0.
rng = random.Random(202610181851)
for scores, values in fixtures:
    peak = max(D.from_float(x) for x in scores)
    weights = [(D.from_float(x)-peak).exp() for x in scores]
    expected = sum(w*D.from_float(v) for w,v in zip(weights,values))/sum(weights)
    for shards in (1, 2, 4, 9):
        summaries = [candidate.summarize([1.], [[s] for s in scores], [[v] for v in values],
                                        [i for i in range(7) if i%shards == shard]) for shard in range(shards)]
        shuffled = list(range(shards)); rng.shuffle(shuffled)
        for order in (list(range(shards)), list(reversed(range(shards))), shuffled):
            merged = None
            for shard in order:
                merged = candidate.merge(merged, summaries[shard])
            actual = candidate.finish(merged)[0]
            error = float(abs(D.from_float(actual)-expected))
            assert math.isfinite(actual) and error <= 1e-10
            comparisons += 1
            max_error = max(max_error, error)

# Deliberately invalid duplicate coverage is NOT rejected by an algebra helper.
# This demonstrates why the future protocol must separately validate coverage.
a = candidate.summarize([1.], [[0.], [0.]], [[0.], [1.]], [0])
b = candidate.summarize([1.], [[0.], [0.]], [[0.], [1.]], [1])
valid = candidate.finish(candidate.merge(a, b))[0]
invalid = candidate.finish(candidate.merge(candidate.merge(a, a), b))[0]
assert valid == .5 and invalid == 1/3
print(json.dumps(dict(author_rerun_byte_identical=True, author_comparisons_verified=432,
    author_empty_comparisons_verified=240, accounting_rows_verified=len(ledger['rows']),
    source_checks=source_checks, decimal_adversarial=dict(precision_digits=90, fixtures=len(fixtures),
        comparisons=comparisons, max_absolute_error=max_error, tolerance=1e-10),
    duplicate_coverage_counterexample=dict(valid_output=valid, duplicated_output=invalid,
        interpretation='Exploratory reviewer demonstration of stated protocol precondition; not a defect in the claimed arithmetic fixture.'),
    scope='Arithmetic, source identity/excerpts and design review only; no inference or physical performance validation.'),indent=2))
