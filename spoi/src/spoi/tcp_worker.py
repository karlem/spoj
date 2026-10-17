"""Independent loopback worker. All weights and tensors arrive via TCP."""
import argparse
import os
import socket
import time

import torch

from .config import ExperimentConfig
from .qwen3_adapter import ExpertShard, compatibility, configure_threads, evaluate_shard
from .tcp_wire import ProtocolError, recv_frame, send_frame


def identity(meta, kind, run, worker, request):
    if (meta.get('kind') != kind or meta.get('run') != run
            or type(meta.get('worker')) is not int or meta['worker'] != worker
            or type(meta.get('request')) is not int or meta['request'] != request):
        raise ProtocolError('message identity/kind mismatch')


def serve(port, worker, run, startup_timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    deadline = time.monotonic() + startup_timeout
    sock.settimeout(startup_timeout)
    try:
        sock.connect(('127.0.0.1', port))
        def meta(kind, request, **extra):
            return dict(kind=kind, run=run, worker=worker, request=request, **extra)
        send_frame(sock, meta('hello', 0, pid=os.getpid(), versions=compatibility()), {}, deadline)
        init, tensors, init_event = recv_frame(sock, deadline)
        identity(init, 'init', run, worker, 0)
        if set(init) != {'kind', 'run', 'worker', 'request', 'config', 'ids', 'hash', 'digest'}:
            raise ProtocolError('invalid init schema')
        if set(tensors) != {'gate_up', 'down'}:
            raise ProtocolError('invalid init tensors')
        values = dict(init['config'])
        if values.get('placement') is not None:
            values['placement'] = tuple(values['placement'])
        config = ExperimentConfig(**values)
        configure_threads(config.threads)
        ids = init['ids']
        if (not isinstance(ids, list) or any(type(i) is not int for i in ids)
                or ids != sorted(set(ids)) or any(not 0 <= i < config.num_experts for i in ids)):
            raise ProtocolError('invalid owned expert IDs')
        shard = ExpertShard(tuple(ids), tensors['gate_up'], tensors['down'], init['hash'], init['digest'])
        for tensor, shape in ((shard.gate_up, (len(ids), 2*config.moe_intermediate_size, config.hidden_size)),
                              (shard.down, (len(ids), config.hidden_size, config.moe_intermediate_size))):
            if tensor.dtype != torch.float32 or tuple(tensor.shape) != shape:
                raise ProtocolError('invalid shard shape/dtype')
            if tensor.untyped_storage().nbytes() != tensor.numel()*tensor.element_size():
                raise ProtocolError('noncompact shard')
        if shard.actual_digest() != shard.digest:
            raise ProtocolError('shard digest mismatch')
        del tensors
        send_frame(sock, meta('ready', 0, pid=os.getpid(), ids=ids, hash=shard.state_hash,
                             digest=shard.actual_digest(), storage=list(shard.storage_bytes), received_init=init_event['sha256']), {}, deadline)
        request = 1
        while True:
            # One local request at a time; bounded idle lifetime as well as I/O.
            deadline = time.monotonic() + config.startup_timeout
            message, tensors, request_event = recv_frame(sock, deadline)
            deadline = time.monotonic() + config.request_timeout
            if message.get('kind') == 'stop':
                identity(message, 'stop', run, worker, request)
                if set(message) != {'kind', 'run', 'worker', 'request'} or tensors:
                    raise ProtocolError('invalid stop schema')
                send_frame(sock, meta('stopped', request), {}, deadline)
                return
            identity(message, 'execute', run, worker, request)
            if set(message) != {'kind', 'run', 'worker', 'request'}:
                raise ProtocolError('invalid execute schema')
            if set(tensors) != {'rows', 'tokens', 'slots', 'experts', 'weights'}:
                raise ProtocolError('invalid execute tensors')
            rows = tensors['rows']
            n = rows.shape[0] if rows.ndim == 2 else -1
            if rows.dtype != torch.float32 or rows.shape != (n, config.hidden_size):
                raise ProtocolError('invalid request rows')
            for name in ('tokens', 'slots', 'experts'):
                value = tensors[name]
                if value.dtype != torch.int64 or value.shape != (n,) or (value < 0).any():
                    raise ProtocolError('invalid request index')
            if ((tensors['slots'] >= config.top_k).any()
                    or len(set(zip(tensors['tokens'].tolist(), tensors['slots'].tolist()))) != n
                    or tensors['weights'].dtype != torch.float32 or tensors['weights'].shape != (n,)
                    or (tensors['weights'] < 0).any() or (tensors['weights'] > 1).any()):
                raise ProtocolError('invalid assignment/weights')
            with torch.inference_mode():
                output = evaluate_shard(shard, rows, tensors['experts'], tensors['weights'])
            reply = {key: tensors[key] for key in ('tokens', 'slots', 'experts', 'weights')}
            reply['output'] = output
            send_frame(sock, meta('result', request, received_request=request_event['sha256']), reply, deadline)
            request += 1
    except Exception as exc:
        try:
            send_frame(sock, dict(kind='error', run=run, worker=worker, request=locals().get('request', 0),
                                 message=f'{type(exc).__name__}: {exc}'[:2000]), {}, time.monotonic()+0.2)
        except Exception:
            pass
        raise
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--worker', type=int, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--startup-timeout', type=float, default=60)
    args = parser.parse_args()
    serve(args.port, args.worker, args.run, args.startup_timeout)


if __name__ == '__main__':
    main()
