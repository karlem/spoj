import base64
import hashlib
import json
from pathlib import Path

import pytest
import torch

from spoi.qwen3_adapter import build_reference
from spoi.tcp_demo import controlled_reference, inputs
from spoi.tcp_session import TCPSession, TCPError
from spoi.verify_tcp_trace import verify
from spoi import tcp_wire


@pytest.fixture(scope='module')
def artifact(tmp_path_factory):
    from spoi.tcp_demo import main
    directory = tmp_path_factory.mktemp('tcp-trace')/'demo'
    main(['--output', str(directory)])
    return directory


def test_offline_raw_trace_replay_and_no_overwrite(artifact):
    from spoi.tcp_demo import main
    result = verify(artifact/'trace.json')
    assert result['verified'] and result['frames'] == 33 and result['contributions'] == 14
    assert (artifact/'README.md').is_file()
    with pytest.raises(FileExistsError): main(['--output', str(artifact)])


@pytest.mark.parametrize('fault', ['raw-byte', 'drop-contribution', 'duplicate-contribution', 'trace-output', 'rehash-changed-frame'])
def test_trace_falsification_is_rejected(artifact, tmp_path, fault):
    data = json.loads((artifact/'trace.json').read_text())
    if fault == 'raw-byte':
        raw = bytearray(base64.b64decode(data['events'][0]['frame_base64']))
        raw[-1] ^= 1
        data['events'][0]['frame_base64'] = base64.b64encode(raw).decode()
    if fault == 'drop-contribution': data['records'][0]['contributions'].pop()
    if fault == 'duplicate-contribution': data['records'][0]['contributions'][1] = data['records'][0]['contributions'][0]
    if fault == 'trace-output': data['records'][0]['contributions'][0]['output'][0] += 1
    if fault == 'rehash-changed-frame':
        event = next(e for e in data['events'] if e['meta']['kind'] == 'result' and e['meta']['request'] == 1)
        raw = base64.b64decode(event['frame_base64'])
        hsize, _ = tcp_wire.PREFIX.unpack(raw[:8])
        meta, tensors = tcp_wire.decode(raw[8:8+hsize], raw[8+hsize:])
        tensors['output'] += 1
        raw = tcp_wire.encode(meta, tensors)
        event.update(frame_base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    path = tmp_path/'corrupted.json'; path.write_text(json.dumps(data))
    with pytest.raises((ValueError, AssertionError)):
        verify(path)


def test_trace_bounds_and_concurrency_fail_explicitly():
    block, state = controlled_reference()
    session = TCPSession(block, state, workers=1, trace=True)
    with session:
        session._lock.acquire()
        try:
            with pytest.raises(TCPError, match='concurrent'):
                session.forward(inputs()[0])
        finally:
            session._lock.release()
        with pytest.raises(TCPError, match='bounded trace'):
            session.forward(torch.zeros(1, 17, 64))
    assert session.closed and all(p.poll() is not None for p in session.processes)
