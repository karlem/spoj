"""Functional deadline witness with actual successful TCP sends before timeout."""
import json
from pathlib import Path
import socket
import sys
import time

import torch
from spoi.tcp_wire import send_frame

torch.set_num_threads(1)
listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen()
a=socket.create_connection(listener.getsockname()); b,_=listener.accept(); listener.close()
a.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
b.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4096)
class Counted:
    def __init__(self,sock): self.sock,self.bytes,self.calls=sock,0,0
    def settimeout(self,value): self.sock.settimeout(value)
    def send(self,value):
        self.calls+=1
        count=self.sock.send(value); self.bytes+=count; return count
counted=Counted(a); data=torch.zeros(1024*1024)
start=time.monotonic(); expected=False
try:
    try: send_frame(counted,{'kind':'backpressure-witness'},{'x':data},start+0.2)
    except TimeoutError: expected=True
    elapsed=time.monotonic()-start
    if not expected or counted.bytes<=8 or not 0<elapsed<2:
        raise RuntimeError('did not observe successful payload send followed by bounded timeout')
    # Peer was deliberately not reading until after the sender timed out.
    b.settimeout(0.1); prefix=b.recv(8)
    result=dict(expected_exception='TimeoutError',observed=True,bytes_successfully_sent=counted.bytes,
                socket_send_calls=counted.calls,received_prefix_hex=prefix.hex(),deadline_seconds=0.2,
                elapsed_seconds=elapsed,purpose='functional deadline witness, not a performance benchmark')
    Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    a.close(); b.close()
