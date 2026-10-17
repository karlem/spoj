"""Test subprocess only; inject faults at actual TCP frame boundaries."""
import os
import time

from spoi import tcp_worker as worker
from spoi import tcp_wire as wire

mode = os.environ['SPOI_TCP_FAULT']
original_send, original_recv = worker.send_frame, worker.recv_frame


def send(sock, meta, tensors, deadline):
    if meta['worker'] == 0:
        if meta['kind'] == 'hello' and mode == 'startup-crash':
            os._exit(29)
        if meta['kind'] == 'ready' and mode == 'bad-ready':
            meta['digest'] = 'bad'
        if meta['kind'] == 'result':
            if mode == 'disconnect':
                sock.close(); os._exit(31)
            if mode == 'truncated-result':
                sock.sendall(wire.encode(meta, tensors)[:12]); sock.close(); os._exit(32)
            if mode == 'stall':
                time.sleep(60)
            if mode == 'wrong-run': meta['run'] = 'wrong'
            if mode == 'wrong-request': meta['request'] += 10
            if mode == 'wrong-worker': meta['worker'] = 3
            if mode == 'missing-slot':
                tensors['slots'] = tensors['slots'][:-1].clone()
            if mode == 'duplicate-slot':
                tensors['slots'][1] = tensors['slots'][0]
            if mode == 'changed-weight':
                tensors['weights'] = tensors['weights'] * 0.5
            if mode == 'bad-contribution':
                tensors['output'] = tensors['output'] + 1
            if mode == 'swap-contributions':
                tensors['output'] = tensors['output'].flip(0)
            if mode == 'wrong-output-dtype':
                tensors['output'] = tensors['output'].to(__import__('torch').int64)
            if mode == 'duplicate':
                original_send(sock, meta, tensors, deadline)
        if meta['kind'] == 'stopped' and mode == 'shutdown-stall':
            time.sleep(60)
    return original_send(sock, meta, tensors, deadline)


def recv(sock, deadline):
    meta, tensors, event = original_recv(sock, deadline)
    if meta.get('worker') == 0 and meta['kind'] == 'init':
        if mode == 'corrupt-shard': tensors['gate_up'][0, 0, 0] += 1
        if mode == 'wrong-shard-shape': tensors['down'] = tensors['down'][:, :, :-1].clone()
        if mode == 'startup-stall': time.sleep(60)
    return meta, tensors, event


worker.send_frame, worker.recv_frame = send, recv
worker.main()
