import datetime, hashlib, importlib.util, json, os, platform, resource, sqlite3, subprocess, sys, tempfile, time
from pathlib import Path

root = Path(__file__).resolve().parent
origin = root.parent / 'implementer'
revision = '571d5dde2aac38a59f01022b39eac10150fc42bf'
source = subprocess.check_output(['git', '-C', str(origin), 'show', revision + ':recovery_fixture.py'])
sha = hashlib.sha256(source).hexdigest()
assert sha == 'f61e3dce52afde95f05c7d1cc62d8da110bae7b2e71806d90d0bd7e31102e62d'
(root / 'recovery_fixture.py').write_bytes(source)
previous = json.loads((origin / 'evidence.json').read_text())
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024**2, 10 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
cmd = ['timeout', '--kill-after=2s', '300s', sys.executable, '-B', 'recovery_fixture.py']
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
t = time.monotonic()
p = subprocess.run(cmd, cwd=root, text=True, capture_output=True, preexec_fn=limits, timeout=305)
elapsed = time.monotonic() - t
assert p.returncode == 0, p.stderr
actual = json.loads(p.stdout)
assert actual == json.loads(previous['raw_stdout']), 'Full parsed output differs'
expected = [['job-a', 3, 9], ['job-b', 7, 49], ['job-c', 11, 121]]
assert actual['reopened_rows'] == expected
assert len(actual['naive_rows']) == 5
assert len(actual['naive_rows']) - len({row[0] for row in actual['naive_rows']}) == 2
assert actual['negative_checks_rejected'] == ['wrong-result-new-id', 'wrong-result-existing-id', 'conflicting-input-same-id']
assert [e['status'] for e in actual['events']] == ['precommit failure', 'committed', 'postcommit acknowledgement lost', 'duplicate-suppressed', 'committed', 'duplicate-suppressed']
input_hash = hashlib.sha256(json.dumps(actual['input'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert actual['input_sha256'] == input_hash == previous['input_sha256']
# Independent assertions on the transaction API, including reopening before retry.
limits()
spec = importlib.util.spec_from_file_location('fixture', root / 'recovery_fixture.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(dir=root) as d:
    dbpath = Path(d) / 'independent.sqlite'
    db = sqlite3.connect(dbpath)
    db.execute('CREATE TABLE results (job_id TEXT PRIMARY KEY, operand INTEGER NOT NULL, result INTEGER NOT NULL)')
    db.commit()
    try:
        m.deliver(db, 'x', 6, 36, 'precommit')
        raise AssertionError('precommit failed to throw')
    except m.InjectedFailure:
        pass
    db.close()
    db = sqlite3.connect(dbpath)
    assert db.execute('SELECT * FROM results').fetchall() == []
    try:
        m.deliver(db, 'x', 6, 36, 'lost-ack')
        raise AssertionError('lost ack failed to throw')
    except m.InjectedFailure:
        pass
    db.close()
    db = sqlite3.connect(dbpath)
    assert db.execute('SELECT * FROM results').fetchall() == [('x', 6, 36)]
    assert m.deliver(db, 'x', 6, 36) == 'duplicate-suppressed'
    for args, exception in [(('bad', 3, 8), ValueError), (('x', 6, 35), ValueError), (('x', 7, 49), m.Conflict)]:
        try:
            m.deliver(db, *args)
            raise AssertionError('negative accepted')
        except exception:
            pass
    assert db.execute('SELECT * FROM results').fetchall() == [('x', 6, 36)]
    assert not db.in_transaction
    db.close()
report = {
    'verdict': 'APPROVED_FOR_LOCAL_ORCHESTRATION_FIXTURE_ONLY',
    'validator': '/root/startup_validator', 'model_id': 'unavailable',
    'source_revision': revision, 'source_sha256': sha,
    'input_sha256': input_hash, 'implementer_evidence_sha256': hashlib.sha256((origin / 'evidence.json').read_bytes()).hexdigest(),
    'command': cmd, 'cwd': str(root), 'started_at_utc': started, 'elapsed_seconds': elapsed,
    'exit_code': p.returncode, 'raw_stdout': p.stdout, 'raw_stderr': p.stderr,
    'environment': {'python': sys.version, 'sqlite': sqlite3.sqlite_version, 'platform': platform.platform()},
    'limits': {'wall_seconds': 300, 'address_space_bytes': 2 * 1024**3, 'cpu_seconds': 30, 'per_file_bytes': 10 * 1024**2},
    'checks': {'full_parsed_output_matches': True, 'three_correct_unique_reopened_rows': True, 'baseline_five_rows_two_duplicates': True, 'three_negative_cases_rejected': True, 'independent_reopen_before_retry_and_negative_immutability': True},
    'limitations': [
        'Injected Python exceptions and orderly connection close/reopen, not process death, power loss or real ACK transport loss.',
        'Single local SQLite database with sequential deliveries; no concurrent or distributed workers, SPOJ product, hardware/performance or novelty proof.',
        'Append-only baseline is a sanity counterexample, not the strongest feasible research baseline.',
        'Input plan is duplicated as executable loops and output metadata; inspected equal for this pinned source, not a general workload parser.',
        'Same host and runtime as implementer, independent agent and directory; no cross-machine replication.',
        'Per-file and address-space limits enforced; this tiny fixed fixture creates bounded files, no general aggregate disk quota installed.'
    ]
}
report['total_directory_bytes_before_report'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
assert report['total_directory_bytes_before_report'] < 100 * 1024**2
(root / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'verdict': report['verdict'], 'validation': str(root / 'validation.json'), 'elapsed_seconds': elapsed, 'input_sha256': input_hash, 'source_sha256': sha}))
