"""Versioned bounded tensor frames over TCP. No pickle or shared storage."""
import hashlib
import base64
import json
import math
import socket
import struct
import time

import numpy as np
import torch

MAX_HEADER = 65536
MAX_PAYLOAD = 8 * 1024 * 1024
PREFIX = struct.Struct('!II')
DTYPES = {'f32': (np.dtype('<f4'), torch.float32), 'i64': (np.dtype('<i8'), torch.int64)}


class ProtocolError(RuntimeError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError('duplicate JSON key')
        result[key] = value
    return result


def encode(meta, tensors):
    if not isinstance(meta, dict) or not isinstance(tensors, dict) or len(tensors) > 8:
        raise ProtocolError('invalid frame objects')
    descriptors, pieces, offset = [], [], 0
    for name, tensor in tensors.items():
        if (not isinstance(name, str) or not isinstance(tensor, torch.Tensor)
                or tensor.device.type != 'cpu' or tensor.ndim > 4
                or tensor.dtype not in (torch.float32, torch.int64)):
            raise ProtocolError('unsupported tensor')
        if not torch.isfinite(tensor).all():
            raise ProtocolError('nonfinite tensor')
        dtype = 'f32' if tensor.dtype == torch.float32 else 'i64'
        size = tensor.numel() * tensor.element_size()
        if offset + size > MAX_PAYLOAD:
            raise ProtocolError('oversized payload')
        raw = tensor.detach().contiguous().numpy().astype(DTYPES[dtype][0], copy=False).tobytes()
        descriptors.append(dict(name=name, dtype=dtype, shape=list(tensor.shape), offset=offset, size=size))
        pieces.append(raw)
        offset += size
    try:
        header = json.dumps(dict(version=1, meta=meta, tensors=descriptors),
                            allow_nan=False, separators=(',', ':')).encode()
    except (ValueError, TypeError) as exc:
        raise ProtocolError('invalid metadata') from exc
    if len(header) > MAX_HEADER:
        raise ProtocolError('oversized header')
    return PREFIX.pack(len(header), offset) + header + b''.join(pieces)


def decode(header, payload):
    if not 0 < len(header) <= MAX_HEADER or len(payload) > MAX_PAYLOAD:
        raise ProtocolError('invalid frame lengths')
    try:
        data = json.loads(header, object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ProtocolError('nonfinite JSON')))
    except (ValueError, UnicodeError) as exc:
        raise ProtocolError('invalid JSON') from exc
    if (not isinstance(data, dict) or set(data) != {'version', 'meta', 'tensors'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['meta'], dict) or not isinstance(data['tensors'], list)
            or len(data['tensors']) > 8):
        raise ProtocolError('invalid frame schema/version')
    result, offset = {}, 0
    for d in data['tensors']:
        if (not isinstance(d, dict) or set(d) != {'name', 'dtype', 'shape', 'offset', 'size'}
                or not isinstance(d['name'], str) or d['name'] in result
                or not isinstance(d['dtype'], str) or d['dtype'] not in DTYPES
                or not isinstance(d['shape'], list) or len(d['shape']) > 4
                or any(type(n) is not int or n < 0 or n > MAX_PAYLOAD for n in d['shape'])
                or type(d['offset']) is not int or type(d['size']) is not int):
            raise ProtocolError('invalid tensor descriptor')
        dtype, _ = DTYPES[d['dtype']]
        size = math.prod(d['shape']) * dtype.itemsize
        if d['offset'] != offset or d['size'] != size or offset + size > len(payload):
            raise ProtocolError('tensor size/offset mismatch')
        array = np.frombuffer(payload[offset:offset+size], dtype=dtype).copy().reshape(d['shape'])
        tensor = torch.from_numpy(array.astype(dtype.newbyteorder('='), copy=False))
        if not torch.isfinite(tensor).all():
            raise ProtocolError('nonfinite tensor')
        result[d['name']] = tensor
        offset += size
    if offset != len(payload):
        raise ProtocolError('unclaimed payload')
    return data['meta'], result


def _timeout(sock, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('TCP deadline exceeded')
    sock.settimeout(remaining)


def _read(sock, count, deadline):
    pieces = bytearray()
    while len(pieces) < count:
        _timeout(sock, deadline)
        chunk = sock.recv(count-len(pieces))
        if not chunk:
            raise ProtocolError('truncated frame/disconnected peer')
        pieces.extend(chunk)
    return bytes(pieces)


def _event(raw, meta, direction, capture=False):
    event = dict(direction=direction, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), meta=meta)
    if capture:
        event['frame_base64'] = base64.b64encode(raw).decode()
    return event


def send_frame(sock, meta, tensors, deadline, *, capture=False):
    raw = encode(meta, tensors)
    view = memoryview(raw)
    while view:
        _timeout(sock, deadline)
        count = sock.send(view)
        if count <= 0:
            raise ProtocolError('disconnected while sending')
        view = view[count:]
    return _event(raw, meta, 'send', capture)


def recv_frame(sock, deadline, *, capture=False):
    prefix = _read(sock, PREFIX.size, deadline)
    hsize, psize = PREFIX.unpack(prefix)
    if not 0 < hsize <= MAX_HEADER or psize > MAX_PAYLOAD:
        raise ProtocolError('oversized/invalid frame prefix')
    header = _read(sock, hsize, deadline)
    payload = _read(sock, psize, deadline)
    meta, tensors = decode(header, payload)
    return meta, tensors, _event(prefix+header+payload, meta, 'recv', capture)
