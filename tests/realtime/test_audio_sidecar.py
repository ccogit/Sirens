import base64
import json
import socket
import struct
import subprocess
import sys
import threading
import unittest

from sirens.realtime.pcm import pack
from sirens.realtime.sidecar import Sidecar, read_exact

ORIGIN = "http://127.0.0.1:8765"
SID = "a" * 32


def pcm(seq=0, epoch=0):
    return pack(dict(protocol_version=1, stream_id=1, epoch=epoch, seq=seq,
                     start_frame=seq*256, nframes=256, channels=2, flags=0,
                     sample_rate=48000), bytes(2048))


def connect(port, token, origin=ORIGIN):
    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    key = base64.b64encode(bytes(range(16))).decode()
    sock.sendall((f"GET /pcm HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                  f"Origin: {origin}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: {key}\r\n"
                  f"Sec-WebSocket-Protocol: sirens.pcm.v1, {token}\r\n\r\n").encode())
    response = bytearray()
    while not response.endswith(b"\r\n\r\n"):
        response.extend(read_exact(sock, 1))
    return sock, bytes(response)


class SidecarTests(unittest.TestCase):
    def setUp(self):
        self.server = Sidecar([ORIGIN])
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .01})
        self.thread.start()
        self.addCleanup(self.finish)
        self.port = self.server.server_address[1]
        self.token = self.server.hub.issue(SID, [1])

    def finish(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def test_valid_stream(self):
        sock, response = connect(self.port, self.token)
        with sock:
            self.assertIn(b"101 Switching Protocols", response)
            self.assertIn(b"Sec-WebSocket-Accept: Bz3qJYTGdOe8gUSpLosEdiLKDrk=", response)
            self.assertTrue(self.server.hub.publish(SID, pcm()))
            self.assertEqual(read_exact(sock,2), b"\x82\x7e")
            size = struct.unpack("!H",read_exact(sock,2))[0]
            self.assertEqual(read_exact(sock,size),pcm())
            other, res = connect(self.port,self.token)
            with other:
                self.assertIn(b"403 Forbidden",res)

    def test_auth(self):
        for token, origin in [("x"*32,ORIGIN),(self.token,"http://evil.example")]:
            sock,response = connect(self.port,token,origin)
            with sock:
                self.assertIn(b"403 Forbidden",response)

    def test_bad_pcm_and_backpressure(self):
        bad = bytearray(pcm())
        bad[0] = 2
        for block in (b"x", bytes(16417), bad, pcm()[:-1]):
            with self.assertRaises(Exception):
                self.server.hub.publish(SID,block)
        for seq in range(8):
            self.assertTrue(self.server.hub.publish(SID,pcm(seq)))
        self.assertFalse(self.server.hub.publish(SID,pcm(8)))
        self.assertFalse(self.server.hub.publish(SID,pcm(0,1)))
        self.server.hub.take(self.server.hub.sessions[SID])
        self.assertTrue(self.server.hub.publish(SID,pcm(0,1)))
        self.server.hub.take(self.server.hub.sessions[SID])
        self.assertTrue(self.server.hub.publish(SID,pcm(9,0)))

    def test_client_data_rejected(self):
        sock,response=connect(self.port,self.token)
        with sock:
            self.assertIn(b"101",response)
            sock.sendall(b"\x82\x80")
            self.assertEqual(read_exact(sock,4),b"\x88\x02\x03\xea")

    def test_process_shutdown(self):
        proc = subprocess.Popen([sys.executable,"-m","sirens.realtime.sidecar","--origin",ORIGIN],
                                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            # communicate schließt stdin, EOF ist ebenfalls ein sauberer Shutdown.
            data = b'{"op":"stop"}'
            out,err = proc.communicate(struct.pack("<I",len(data)+1)+b"J"+data,timeout=10)
            self.assertEqual(proc.returncode,0,err)
            rows = [json.loads(line) for line in out.splitlines()]
            self.assertGreater(rows[0]["port"],0)
            self.assertEqual(rows[1],{"ok":True})
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
