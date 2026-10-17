"""Run real verifier commands against deliberately falsified copies of a trace."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from spoi import tcp_wire

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('trace', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = json.loads(args.trace.read_text())
results = []
for fault in ('raw-byte', 'rehash-output', 'drop-assignment', 'duplicate-assignment'):
    data = copy.deepcopy(source)
    if fault == 'raw-byte':
        event = data['events'][0]
        raw = bytearray(base64.b64decode(event['frame_base64'])); raw[-1] ^= 1
        event['frame_base64'] = base64.b64encode(raw).decode()
    if fault == 'rehash-output':
        event = next(e for e in data['events'] if e['meta']['kind'] == 'result' and e['meta']['request'] == 1)
        raw = base64.b64decode(event['frame_base64'])
        size, _ = tcp_wire.PREFIX.unpack(raw[:8])
        meta, tensors = tcp_wire.decode(raw[8:8+size], raw[8+size:])
        tensors['output'] += 1
        raw = tcp_wire.encode(meta, tensors)
        event.update(frame_base64=base64.b64encode(raw).decode(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if fault == 'drop-assignment': data['records'][0]['contributions'].pop()
    if fault == 'duplicate-assignment': data['records'][0]['contributions'][1] = data['records'][0]['contributions'][0]
    path = args.output/(fault+'.json'); path.write_text(json.dumps(data))
    command = [sys.executable, '-m', 'spoi.verify_tcp_trace', str(path)]
    process = subprocess.run(command, text=True, capture_output=True, timeout=30)
    transcript = args.output/(fault+'.log')
    transcript.write_text('$ '+' '.join(command)+'\nexit_code='+str(process.returncode)+'\n'+process.stdout+process.stderr)
    if process.returncode != 1:
        raise RuntimeError(f'{fault}: expected verification exit 1, observed {process.returncode}')
    results.append(dict(fault=fault, expected_exit_code=1, observed_exit_code=process.returncode,
                        result='expected rejection observed', transcript=transcript.name,
                        source_trace_sha256=hashlib.sha256(args.trace.read_bytes()).hexdigest()))
(args.output/'results.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(dict(negative_commands=len(results), all_expected_rejections=True, harness_exit_code=0)))
