#!/usr/bin/env python3
"""Compile/run the preregistered bounded C experiment; no third-party packages."""
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'
RAW.mkdir(exist_ok=True)
BINARY = HERE / 'echo.bin'
MAX_BYTES = 100 * 1024 * 1024
EXPECTED = 90117120 + 256
assert EXPECTED < MAX_BYTES

def limit():
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS, (256*1024*1024, 256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16*1024*1024, 16*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def text_file(name):
    try:
        return Path(name).read_text().strip()
    except OSError as exc:
        return str(exc)

compile_command = ['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Werror', str(HERE/'echo.c'), '-o', str(BINARY)]
compile_result = subprocess.run(compile_command, capture_output=True, text=True, timeout=20)
(RAW/'compile.json').write_text(json.dumps({'command': compile_command, 'returncode': compile_result.returncode, 'stdout': compile_result.stdout, 'stderr': compile_result.stderr}, indent=2)+'\n')
if compile_result.returncode:
    sys.exit(compile_result.returncode)
metadata = {
    'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'uname': list(platform.uname()), 'python': sys.version,
    'compiler': subprocess.run(['gcc', '--version'], capture_output=True, text=True, check=True).stdout,
    'cpu_quota': text_file('/sys/fs/cgroup/cpu.max'),
    'memory_max': text_file('/sys/fs/cgroup/memory.max'),
    'affinity': sorted(os.sched_getaffinity(0)),
    'cpu_model_lines': [line for line in text_file('/proc/cpuinfo').splitlines() if line.startswith(('model name', 'processor'))],
    'git_head': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip(),
    'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'echo.c', HERE/'run.py', HERE/'PROTOCOL.md']},
    'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
    'limits': {'as_bytes_per_process': 256*1024*1024, 'cpu_s_per_process':30, 'file_bytes':16*1024*1024, 'session_timeout_s':20, 'socket_timeout_s':5},
}
(RAW/'environment.json').write_text(json.dumps(metadata, indent=2)+'\n')
summaries = []
aggregate_bytes = 0
aggregate_ok = 0
for pair in range(5):
    order = ['tcp', 'unix'] if pair % 2 == 0 else ['unix', 'tcp']
    for position, transport in enumerate(order):
        summaries.append({'pair': pair+1, 'position':position+1, 'transport':transport, 'mode':'normal'})
summaries.append({'pair':None, 'position':None, 'transport':'tcp', 'mode':'corrupt'})
for number, row in enumerate(summaries):
    name = f'{number:02d}-{row["transport"]}-{row["mode"]}'
    command = [str(BINARY), row['transport'], row['mode']]
    before = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=limit)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    elapsed = time.monotonic()-before
    (RAW/f'{name}.jsonl').write_text(out)
    (RAW/f'{name}.stderr').write_text(err)
    row.update({'name':name, 'command':command, 'exit':proc.returncode, 'wall_s':elapsed, 'timeout':timed_out})
    (RAW/f'{name}.process.json').write_text(json.dumps(row, indent=2)+'\n')
    expected_exit = 42 if row['mode']=='corrupt' else 0
    assert not timed_out and proc.returncode == expected_exit, row
    records = [json.loads(line) for line in out.splitlines()]
    final = records[-1]
    assert final['kind']=='final' and final['child_exit']==0 and final['exit']==expected_exit
    req = [r for r in records if r['kind']=='request']
    assert all(r['io_ok'] for r in req)
    if row['mode']=='normal':
        assert len(req)==152 and all(r['equal'] for r in req)
        assert [r['sequence'] for r in req]==list(range(1,153))
        assert final['completed_echo_bytes']==9011712 and final['successful_requests']==152
        row['payloads']={}
        for size, count in [(128,128),(16384,16),(1048576,2)]:
            selected=[r for r in req if r['payload_bytes']==size]
            measured=[r['rtt_verify_ns'] for r in selected if not r['warmup']]
            assert len(measured)==count and len(selected)==count+2
            row['payloads'][str(size)]={'count':count, 'median_ns':statistics.median(measured), 'mean_ns':statistics.mean(measured), 'min_ns':min(measured), 'max_ns':max(measured)}
    else:
        assert len(req)==1 and not req[0]['equal']
        assert final['completed_echo_bytes']==256 and final['successful_requests']==0
    aggregate_bytes += final['completed_echo_bytes']
    aggregate_ok += final['successful_requests']
    assert aggregate_bytes < MAX_BYTES
    row['setup_ns'] = records[0]['setup_ns']
assert aggregate_bytes==EXPECTED and aggregate_ok==1520
result={'scope':'Measured localhost C/OS request echo plus verification only; no NIC/GPU/inference measurement', 'total_payload_bytes':aggregate_bytes, 'successful_requests':aggregate_ok, 'corruption_rejected':True, 'sessions':summaries}
(RAW/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'total_payload_bytes':aggregate_bytes, 'successful_requests':aggregate_ok, 'corruption_rejected':True}))
