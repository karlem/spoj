"""Bounded independent review driver; writes only reviewer scratch."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT = Path('/workspace/spoj-inference-designs-review')
PACKET = ROOT / 'research/manager/inference-designs-20261018'
OUT = Path('/workspace/scratch/inference-validator')
def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2**31, 2**31))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*2**20, 16*2**20))

started = utc()
records = []
for label, command, cwd in [
    ('author-rerun', [sys.executable, '-B', str(PACKET / 'check_designs.py')], PACKET),
    ('independent-audit', [sys.executable, '-B', str(OUT / 'audit.py')], OUT),
]:
    begin = utc()
    start = time.monotonic()
    with (OUT / f'{label}.stdout.json').open('wb') as stdout, (OUT / f'{label}.stderr.txt').open('wb') as stderr:
        result = subprocess.run(command, cwd=cwd, stdout=stdout, stderr=stderr,
                                timeout=300, preexec_fn=limits,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    records.append(dict(label=label, command=command, cwd=str(cwd), started_at=begin,
                        elapsed_seconds=time.monotonic()-start, exit_code=result.returncode))
out = dict(run_id='inference-designs-20261018-1841', worker_id='/root/inference_design_validator',
           provider_model_id=None, started_at=started, ended_at=utc(),
           evaluated_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           environment=dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                            extra_environment={'PYTHONDONTWRITEBYTECODE': '1'}),
           limits=dict(wall_seconds_per_child=300, address_space_bytes=2**31,
                       cpu_seconds_per_child=60, output_file_bytes=16*2**20),
           executions=records,
           source_sha256=hashlib.sha256((PACKET / 'check_designs.py').read_bytes()).hexdigest())
(OUT / 'execution.json').write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out, indent=2))
sys.exit(any(r['exit_code'] for r in records))
