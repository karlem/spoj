"""Measured, bounded local TCP demonstration; no pretrained model downloads."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import torch

from .config import ExperimentConfig
from .qwen3_adapter import FrozenState, build_reference
from .tcp_session import TCPSession


def controlled_reference():
    block, original = build_reference(ExperimentConfig(num_experts=5))
    values = original.state_dict()
    values['gate.weight'].zero_()
    for expert in range(5):
        values['gate.weight'][expert, expert] = 4
    block.load_state_dict(values)
    return block, FrozenState(original.config, values)


def inputs():
    both = torch.zeros(1, 3, 64)
    for token, (first, second) in enumerate([(0, 2), (1, 4), (2, 4)]):
        both[0, token, first], both[0, token, second] = 2, 1
    zero = torch.zeros(1, 1, 64)
    zero[0, 0, 0], zero[0, 0, 1] = 2, 1
    return both, zero


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    # mkdir with exist_ok=False prevents overwriting any prior evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    block, state = controlled_reference()
    session = TCPSession(block, state, trace=True)
    both, zero = inputs()
    with session:
        session.forward(both)
        session.forward(both)  # prove persistence on the same frozen input
        session.forward(zero)  # explicit zero-hit responses from workers 1 and 2
    if session.exitcodes != [0, 0, 0]:
        raise RuntimeError(f'unclean worker exits: {session.exitcodes}')
    repo = Path(__file__).resolve().parents[3]
    git = lambda *a: subprocess.check_output(['git', '-C', str(repo), *a], text=True).strip()
    record = dict(schema_version=1, started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), command=['python', '-m', 'spoi', *sys.argv[1:]],
        commit=git('rev-parse', 'HEAD'), dirty=bool(git('status', '--porcelain')),
        lock_sha256=hashlib.sha256((repo/'spoi'/'uv.lock').read_bytes()).hexdigest(),
        python=sys.version, platform=platform.platform(), versions=session.versions,
        torch_git_version=torch.version.git_version, config=asdict(state.config),
        router_weight=state.state_dict()['gate.weight'].tolist(), state_hash=state.hash,
        owners=session.owners, ready=session.ready, events=session.events, records=session.records,
        exitcodes=session.exitcodes, limitations=['one local random-weight MoE block', 'no multi-host or capacity evidence',
            'Linux does not satisfy native Mac acceptance', 'trusted loopback peers; no remote authentication/TLS'])
    path = args.output/'trace.json'
    path.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    # Independently decode/reconstruct the stored trace before declaring success.
    from .verify_tcp_trace import verify
    result = verify(path)
    (args.output/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    rows = ['| Token | Slot | Expert | Worker | Routing weight | First output component |',
            '| --- | --- | --- | --- | --- | --- |']
    for c in session.records[0]['contributions']:
        rows.append(f"| {c['token']} | {c['slot']} | {c['expert']} | {c['worker']} | {c['weight']:.8f} | {c['output'][0]:.9g} |")
    walkthrough = '''# Measured local TCP walkthrough

This table is generated from request 1 in trace.json, not invented example data.
Full token/input/router/output vectors and base64 raw frames are retained there.
Workers receive no shard tensor through process launch; only loopback port and IDs.

## Explanatory architecture (not a measured diagram)

```mermaid
flowchart LR
 X[Input] --> R[HF router in coordinator]
 R <-->|TCP| A[Worker 0: experts 0,1]
 R <-->|TCP| B[Worker 1: experts 2,3]
 R <-->|TCP| C[Worker 2: expert 4]
 A --> S[Weighted sum by token]
 B --> S
 C --> S
 S --> P[Compare with direct HF]
```

## Observed request 1 contributions

'''+ '\n'.join(rows)+'''

Each row is one token/top-k-slot assignment. The worker returns its weighted
expert vector. The coordinator checks it against the unchanged HF experts path,
then adds contributions by token and compares to direct block(x).
Request 2 repeats the same input/PIDs. Request 3 routes only to worker 0;
workers 1/2 return explicit zero-length contributions over TCP.

## Observed frames (generated from recorded I/O)

```mermaid
sequenceDiagram
 participant C as Coordinator
'''
    for r in session.ready:
        walkthrough += f" participant W{r['worker']} as Worker {r['worker']} PID {r['pid']}\n"
    for event in session.events:
        m = event['meta']; worker=m['worker']
        arrow = f'C->>W{worker}' if event['direction']=='send' else f'W{worker}->>C'
        walkthrough += f" {arrow}: {m['kind']} request {m['request']} ({event['bytes']} bytes)\n"
    walkthrough += '''```

The full encoded frame hashes/bytes appear in trace.json. Worker readiness
attests the received initialization frame hash; results attest the received
request frame hash. verify_tcp_trace decodes these raw frames, rebuilds the
snapshot from transmitted shards plus router weights, checks snapshot/shard
hashes, re-executes real HF contributions and direct outputs, and checks the
walkthrough records against the bytes. SHA-256 links evidence; it is not a
signature or proof against a malicious producer. PIDs/endpoints show local
execution context; these data do not prove remote execution.

## Source map

- qwen3_adapter.py: locked HF source/version guard, frozen hash and custom expert math.
- partition.py: token/slot-preserving packing and indexed accumulation.
- tcp_wire.py: bounded JSON metadata and raw little-endian tensors, partial I/O, absolute deadlines.
- tcp_worker.py: standalone process, initialization digest, owned expert loop.
- tcp_session.py: launch/readiness/ownership, real socket frames, HF contribution and final checks, cleanup.
- tcp_demo.py: controlled routing, repeat/zero-hit requests and this measured report.
- verify_tcp_trace.py: offline byte decoder and independent HF reconstruction of the artifact.

## What this establishes and leaves open

This run establishes local CPU float32 contribution/output parity for its
recorded inputs through a three-worker TCP boundary. Fault and matrix tests
provide separate broader evidence. It does not establish performance, reduced
total memory, a full language model, native Mac acceptance or multiple hosts.
The coordinator retains the full reference snapshot for checking.

Only after local validation/review passes, later multi-host planning must answer:
which existing hosts/architectures are available, their usable memory budgets,
where weights/router/non-expert state reside, expected wire sizes/link behavior,
authentication/encryption and deployment/endpoint discovery, and what reproducible
cross-host parity/failure evidence is required. No hosts are provisioned here.
'''
    (args.output/'README.md').write_text(walkthrough)
    print(json.dumps(dict(output=str(args.output), **result)))


if __name__ == '__main__':
    main()
