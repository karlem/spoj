import json
import socket
import struct
import threading
import time

import pytest
import torch

from spoi import tcp_wire as wire


class Fragmented:
    def __init__(self, sock):
        self.sock = sock
    def settimeout(self, value):
        self.sock.settimeout(value)
    def send(self, value):
        return self.sock.send(value[:3])
    def recv(self, count):
        return self.sock.recv(min(count, 2))


def pair():
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    left = socket.create_connection(listener.getsockname())
    right, _ = listener.accept()
    listener.close()
    return left, right


def test_real_tcp_fragmented_and_coalesced_frames():
    a, b = pair()
    errors = []
    def sender():
        try:
            for i in range(2):
                wire.send_frame(Fragmented(a), {'request': i}, {'x': torch.arange(12).reshape(3, 4)}, time.monotonic()+5)
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=sender)
    thread.start()
    try:
        for i in range(2):
            meta, tensors, event = wire.recv_frame(Fragmented(b), time.monotonic()+5)
            assert meta == {'request': i} and event['bytes'] > 96
            assert torch.equal(tensors['x'], torch.arange(12).reshape(3, 4))
    finally:
        a.close(); b.close(); thread.join(5)
    assert not errors and not thread.is_alive()


@pytest.mark.parametrize('cut', [0, 1, 7, 8, 10, -1])
def test_truncated_frame_rejected(cut):
    a, b = pair()
    raw = wire.encode({'kind': 'test'}, {'x': torch.ones(3)})
    a.sendall(raw[:cut]); a.close()
    try:
        with pytest.raises(wire.ProtocolError, match='truncated'):
            wire.recv_frame(b, time.monotonic()+1)
    finally:
        b.close()


@pytest.mark.parametrize('prefix', [(0, 0), (wire.MAX_HEADER+1, 0), (1, wire.MAX_PAYLOAD+1)])
def test_oversized_prefix_rejected_before_payload(prefix):
    a, b = pair()
    a.sendall(wire.PREFIX.pack(*prefix))
    try:
        with pytest.raises(wire.ProtocolError, match='prefix'):
            wire.recv_frame(b, time.monotonic()+1)
    finally:
        a.close(); b.close()


@pytest.mark.parametrize('change', ['version', 'dtype', 'shape', 'size', 'offset', 'extra', 'duplicate'])
def test_invalid_tensor_schema(change):
    raw = wire.encode({}, {'x': torch.ones(3)})
    hsize, _ = wire.PREFIX.unpack(raw[:8])
    header, payload = json.loads(raw[8:8+hsize]), raw[8+hsize:]
    if change == 'version': header['version'] = 2
    if change == 'dtype': header['tensors'][0]['dtype'] = 'pickle'
    if change == 'shape': header['tensors'][0]['shape'] = [wire.MAX_PAYLOAD+1]
    if change == 'size': header['tensors'][0]['size'] += 4
    if change == 'offset': header['tensors'][0]['offset'] = 1
    if change == 'extra': header['extra'] = 'bad'
    if change == 'duplicate': header['tensors'] *= 2
    with pytest.raises(wire.ProtocolError):
        wire.decode(json.dumps(header).encode(), payload)


@pytest.mark.parametrize('header', [b'{', b'{"version":1,"version":1}', b'{"version":NaN}', b'[]'])
def test_malformed_json(header):
    with pytest.raises(wire.ProtocolError): wire.decode(header, b'')


def test_nonfinite_wrong_type_and_payload_are_rejected():
    with pytest.raises(wire.ProtocolError, match='nonfinite'):
        wire.encode({}, {'x': torch.tensor([float('nan')])})
    with pytest.raises(wire.ProtocolError, match='unsupported'):
        wire.encode({}, {'x': torch.ones(3, dtype=torch.float64)})
    raw = wire.encode({}, {'x': torch.ones(1)})
    hsize, _ = wire.PREFIX.unpack(raw[:8])
    with pytest.raises(wire.ProtocolError, match='nonfinite'):
        wire.decode(raw[8:8+hsize], struct.pack('<f', float('inf')))
    with pytest.raises(wire.ProtocolError, match='unclaimed'):
        wire.decode(b'{"version":1,"meta":{},"tensors":[]}', b'garbage')


def test_real_kernel_backpressure_has_absolute_deadline():
    a, b = pair()
    a.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    b.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
    tensor = torch.zeros(1024*1024, dtype=torch.float32)
    start = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            wire.send_frame(a, {}, {'x': tensor}, start+0.15)
        assert time.monotonic()-start < 2
    finally:
        a.close(); b.close()


def test_fragment_progress_cannot_reset_deadline():
    a, b = pair()
    raw = wire.encode({}, {})
    def drip():
        try:
            for byte in raw:
                a.sendall(bytes([byte])); time.sleep(0.02)
        except OSError:
            pass
    thread = threading.Thread(target=drip)
    thread.start()
    start = time.monotonic()
    try:
        with pytest.raises(TimeoutError): wire.recv_frame(b, start+0.1)
        assert time.monotonic()-start < 0.5
    finally:
        b.close(); a.close(); thread.join(1)
    assert not thread.is_alive()


def test_encoder_budget_rejected_and_empty_tensor_preserved():
    with pytest.raises(wire.ProtocolError, match='oversized header'):
        wire.encode({'text': 'a'*wire.MAX_HEADER}, {})
    with pytest.raises(wire.ProtocolError, match='oversized payload'):
        wire.encode({}, {'x': torch.zeros(wire.MAX_PAYLOAD//4+1)})
    raw = wire.encode({}, {'x': torch.empty(0, 64)})
    size, _ = wire.PREFIX.unpack(raw[:8])
    _, values = wire.decode(raw[8:8+size], raw[8+size:])
    assert values['x'].shape == (0, 64)
