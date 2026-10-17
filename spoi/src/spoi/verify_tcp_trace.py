"""Offline evidence verifier: decode actual frames and run unchanged HF oracles."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import torch

from .config import ExperimentConfig
from .qwen3_adapter import ExpertShard, build_reference, compatibility, tensor_digest
from .tcp_wire import PREFIX, MAX_HEADER, MAX_PAYLOAD, decode


def require(value, message):
    if not value:
        raise ValueError(message)


def same(actual, expected, message):
    require(actual.dtype == expected.dtype and actual.shape == expected.shape
            and torch.equal(actual, expected), message)


def verify(path):
    path = Path(path)
    require(path.stat().st_size <= 16*1024*1024, 'trace file budget exceeded')
    data = json.loads(path.read_text())
    require(data['schema_version'] == 1 and data['versions'] == compatibility(), 'trace versions mismatch')
    config = dict(data['config'])
    if config.get('placement') is not None: config['placement'] = tuple(config['placement'])
    block, seeded = build_reference(ExperimentConfig(**config))
    require(config['num_experts'] == 5 and config['hidden_size'] == 64 and config['top_k'] == 2,
            'not the bounded five-expert demonstration')
    require(data['owners'] == [0, 0, 1, 1, 2], 'ownership mismatch')
    require(data['exitcodes'] == [0, 0, 0], 'unclean worker exit')
    require(len(data['events']) <= 128 and len(data['records']) == 3, 'trace event/request budget')
    frames, total, runs, pids = {}, 0, set(), set()
    for event in data['events']:
        raw = base64.b64decode(event['frame_base64'], validate=True)
        total += len(raw)
        require(total <= 4*1024*1024 and len(raw) >= 8, 'raw frame budget')
        require(len(raw) == event['bytes'] and hashlib.sha256(raw).hexdigest() == event['sha256'], 'raw frame digest/length')
        hsize, psize = PREFIX.unpack(raw[:8])
        require(0 < hsize <= MAX_HEADER and psize <= MAX_PAYLOAD and len(raw) == 8+hsize+psize, 'raw prefix')
        meta, tensors = decode(raw[8:8+hsize], raw[8+hsize:])
        require(meta == event['meta'], 'frame metadata mismatch')
        require(type(meta['worker']) is int and meta['worker'] in (0, 1, 2), 'frame worker')
        require(event['local'][0] == event['peer'][0] == '127.0.0.1', 'nonloopback endpoint')
        runs.add(meta['run'])
        kind = meta['kind']
        require(kind in ('hello', 'init', 'ready', 'execute', 'result', 'stop', 'stopped'), 'unexpected frame kind')
        direction = 'send' if kind in ('init', 'execute', 'stop') else 'recv'
        require(event['direction'] == direction, 'frame direction')
        key = (meta['worker'], kind, meta['request'])
        require(key not in frames, 'duplicate frame identity')
        frames[key] = (meta, tensors, event)
    require(len(runs) == 1 and len(frames) == 33, 'incomplete frame transcript')
    state = seeded.state_dict()
    router = torch.tensor(data['router_weight'], dtype=torch.float32)
    controlled = torch.zeros_like(state['gate.weight'])
    for expert in range(5): controlled[expert, expert] = 4
    same(router, controlled, 'controlled router provenance')
    state['gate.weight'] = router
    for worker in range(3):
        hello, hello_t, _ = frames[(worker, 'hello', 0)]
        init, tensors, event = frames[(worker, 'init', 0)]
        ready, ready_t, _ = frames[(worker, 'ready', 0)]
        ids = [i for i, owner in enumerate(data['owners']) if owner == worker]
        require(init['config'] == data['config'] and init['ids'] == ids, 'init configuration/ownership')
        require(hello['versions'] == data['versions'] and hello['pid'] == ready['pid'] and type(ready['pid']) is int,
                'worker version/PID mismatch')
        pids.add(ready['pid'])
        require(not hello_t and not ready_t and set(tensors) == {'gate_up', 'down'}, 'init/ready tensor schema')
        same(tensors['gate_up'], state['experts.gate_up_proj'][ids], 'seeded gate/up provenance')
        same(tensors['down'], state['experts.down_proj'][ids], 'seeded down provenance')
        shard = ExpertShard(tuple(ids), tensors['gate_up'], tensors['down'], data['state_hash'], init['digest'])
        require(shard.actual_digest() == init['digest'] == ready['digest'], 'shard digest')
        require(ready['ids'] == ids and ready['storage'] == list(shard.storage_bytes), 'ready ownership/storage')
        require(ready['received_init'] == event['sha256'], 'worker init receipt mismatch')
        require(init['hash'] == ready['hash'] == data['state_hash'], 'state provenance mismatch')
    require(len(pids) == 3 and data['ready'] == [frames[(w, 'ready', 0)][0] for w in range(3)], 'readiness trace mismatch')
    require(tensor_digest(state) == data['state_hash'], 'whole snapshot hash')
    block.load_state_dict(state)
    contributions_count, max_error = 0, 0.0
    with torch.inference_mode():
        for request, record in enumerate(data['records'], 1):
            require(record['request'] == request, 'request sequence mismatch')
            x = torch.tensor(record['input'], dtype=torch.float32)
            require(x.ndim == 3 and 0 < x.shape[0]*x.shape[1] <= 16 and x.shape[-1] == 64, 'trace input bounds')
            logits, weights, selected = block.gate(x)
            same(torch.tensor(record['logits']), logits, 'recorded logits')
            same(torch.tensor(record['weights']), weights, 'recorded weights')
            same(torch.tensor(record['selected']), selected, 'recorded selection')
            flat = x.reshape(-1, 64)
            reconstructed = torch.zeros_like(flat)
            contribution_records = {(c['token'], c['slot']): c for c in record['contributions']}
            require(len(contribution_records) == len(record['contributions']) == len(flat)*2, 'contribution coverage')
            pairs = set()
            for worker in range(3):
                execute, sent, sent_event = frames[(worker, 'execute', request)]
                result, received, _ = frames[(worker, 'result', request)]
                require(set(execute) == {'kind', 'run', 'worker', 'request'}, 'execute metadata schema')
                require(set(result) == {'kind', 'run', 'worker', 'request', 'received_request'}, 'result metadata schema')
                require(result['received_request'] == sent_event['sha256'], 'worker request receipt mismatch')
                require(set(sent) == {'rows', 'tokens', 'slots', 'experts', 'weights'}, 'request tensor schema')
                require(set(received) == {'output', 'tokens', 'slots', 'experts', 'weights'}, 'result tensor schema')
                expected_pairs = [(t, s) for t in range(len(flat)) for s in range(2)
                                  if data['owners'][int(selected[t, s])] == worker]
                tokens = torch.tensor([t for t, s in expected_pairs], dtype=torch.int64)
                slots = torch.tensor([s for t, s in expected_pairs], dtype=torch.int64)
                for key, wanted in dict(tokens=tokens, slots=slots, experts=selected[tokens, slots], weights=weights[tokens, slots]).items():
                    same(sent[key], wanted, 'sent assignment mismatch')
                    same(received[key], wanted, 'returned assignment mismatch')
                same(sent['rows'], flat[tokens], 'sent token rows mismatch')
                hf = block.experts(flat[tokens], selected[tokens, slots][:, None], weights[tokens, slots][:, None])
                torch.testing.assert_close(received['output'], hf, rtol=1e-5, atol=1e-6)
                reconstructed.index_add_(0, tokens, received['output'])
                for i, pair in enumerate(expected_pairs):
                    require(pair not in pairs, 'duplicate token/slot contribution')
                    pairs.add(pair)
                    c = contribution_records[pair]
                    require(c['worker'] == worker and c['expert'] == int(selected[pair]), 'contribution ownership')
                    require(c['weight'] == float(weights[pair]), 'contribution weight')
                    same(torch.tensor(c['input']), flat[pair[0]], 'trace input row')
                    same(torch.tensor(c['output']), received['output'][i], 'trace result bytes')
                    same(torch.tensor(c['hf_output']), hf[i], 'trace HF contribution')
                    contributions_count += 1
            require(pairs == {(t, s) for t in range(len(flat)) for s in range(2)}, 'missing contribution')
            direct = block(x)
            actual = reconstructed.reshape_as(x)
            torch.testing.assert_close(actual, direct, rtol=1e-5, atol=1e-6)
            same(torch.tensor(record['output']), actual, 'recorded reconstruction')
            same(torch.tensor(record['hf_output']), direct, 'recorded HF output')
            error = float((actual-direct).abs().max())
            require(record['max_absolute_error'] == error, 'recorded parity error')
            max_error = max(max_error, error)
    for worker in range(3):
        for kind in ('stop', 'stopped'):
            meta, tensors, _ = frames[(worker, kind, 4)]
            require(set(meta) == {'kind', 'run', 'worker', 'request'} and not tensors, 'shutdown schema')
    return dict(verified=True, frames=len(frames), contributions=contributions_count,
                requests=3, workers=3, max_absolute_error=max_error,
                trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    print(json.dumps(verify(parser.parse_args().trace)))


if __name__ == '__main__':
    main()
