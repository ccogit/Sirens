"""Lokaler PCM-WebSocket-Sidecar. Vertrauenswürdige Producer über privates IPC."""
import argparse
import base64
import collections
import hashlib
import json
import re
import secrets
import select
import socket
import socketserver
import struct
import sys
import threading
import time
from urllib.parse import urlsplit

from .pcm import unpack

MAX_BLOCK = 16416
MAX_SESSIONS = 4
MAX_STREAMS = 8
MAX_QUEUE = 8
PROTOCOL = "sirens.pcm.v1"
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class Stream:
    def __init__(self):
        self.queue = collections.deque()
        self.epoch = -1
        self.seq = -1
        self.credit = MAX_QUEUE * 2048
        self.stamp = time.monotonic()


class Session:
    def __init__(self, streams):
        self.token = secrets.token_urlsafe(32)
        self.expiry = time.monotonic() + 60
        self.streams = {i: Stream() for i in streams}
        self.connected = False
        self.closed = False


class Hub:
    """Keine fremden Pfade/Kommandos; alle Mutationen unter einem Lock."""
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}

    def issue(self, session_id, streams):
        if not isinstance(session_id, str) or not re.fullmatch(r"[0-9a-f]{32}", session_id):
            raise ValueError("Sitzungs-ID")
        if (not isinstance(streams, list) or not 1 <= len(streams) <= MAX_STREAMS
                or any(type(i) is not int or not 1 <= i <= 2**32-1 for i in streams)
                or len(set(streams)) != len(streams)):
            raise ValueError("Streams")
        with self.lock:
            now = time.monotonic()
            for key, s in list(self.sessions.items()):
                if not s.connected and s.expiry <= now:
                    s.closed = True
                    del self.sessions[key]
            if session_id in self.sessions or len(self.sessions) >= MAX_SESSIONS:
                raise ValueError("Sitzung belegt")
            s = self.sessions[session_id] = Session(streams)
            return s.token

    def claim(self, token):
        with self.lock:
            for s in self.sessions.values():
                if (not s.connected and not s.closed and s.expiry > time.monotonic()
                        and secrets.compare_digest(s.token, token)):
                    s.connected = True
                    s.token = ""
                    return s
        return None

    def revoke(self, session_id):
        with self.lock:
            s = self.sessions.pop(session_id, None)
            if s:
                s.closed = True

    def release(self, s):
        with self.lock:
            s.closed = True
            for key, item in list(self.sessions.items()):
                if item is s:
                    del self.sessions[key]

    def publish(self, session_id, block):
        if len(block) > MAX_BLOCK:
            raise ValueError("PCM zu groß")
        h, _ = unpack(block)
        with self.lock:
            s = self.sessions.get(session_id)
            if not s or s.closed or h["stream_id"] not in s.streams:
                return False
            st = s.streams[h["stream_id"]]
            if h["epoch"] < st.epoch or (h["epoch"] == st.epoch and h["seq"] <= st.seq):
                return False
            now = time.monotonic()
            st.credit = min(MAX_QUEUE * 2048, st.credit + (now - st.stamp) * h["sample_rate"])
            st.stamp = now
            if h["nframes"] > st.credit:
                return False
            if h["epoch"] > st.epoch:
                st.queue.clear()
                st.epoch, st.seq = h["epoch"], -1
            if len(st.queue) >= MAX_QUEUE:
                return False
            st.credit -= h["nframes"]
            st.seq = h["seq"]
            st.queue.append(bytes(block))
            return True

    def take(self, s):
        with self.lock:
            if s.closed:
                return None
            # Eine Nachricht pro Iteration, Rundlauf statt Verhungern.
            for key, st in list(s.streams.items()):
                if st.queue:
                    del s.streams[key]
                    s.streams[key] = st
                    return st.queue.popleft()
        return None


def read_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        data = sock.recv(n - len(buf))
        if not data:
            raise EOFError
        buf.extend(data)
    return bytes(buf)


def send_frame(sock, opcode, data=b""):
    n = len(data)
    head = bytes((0x80 | opcode, n)) if n < 126 else bytes((0x80 | opcode, 126)) + struct.pack("!H", n)
    sock.sendall(head + data)


def receive_control(sock):
    a, b = read_exact(sock, 2)
    # Browser ist nur Empfänger; ausschließlich maskierte, unfragmentierte
    # Kontrollframes sind zulässig. Client-Daten werden nie als PCM akzeptiert.
    opcode, n = a & 15, b & 127
    if a & 0xf0 != 0x80 or not b & 0x80 or opcode not in (8, 9, 10) or n > 125:
        raise ValueError("WebSocket-Frame")
    mask = read_exact(sock, 4)
    data = bytes(v ^ mask[i % 4] for i, v in enumerate(read_exact(sock, n)))
    if opcode == 8:
        if n == 1:
            raise ValueError("Close-Frame")
        if n >= 2:
            code = int.from_bytes(data[:2], "big")
            if not (code in (1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014)
                    or 3000 <= code <= 4999):
                raise ValueError("Close-Code")
            data[2:].decode("utf-8")
    return opcode, data


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        sock, server = self.request, self.server
        sock.settimeout(2)
        session = None
        upgraded = False
        try:
            # Kein unbeschränktes readline, keine Token- oder Header-Logs.
            buf = bytearray()
            deadline = time.monotonic() + 2
            while not buf.endswith(b"\r\n\r\n"):
                if len(buf) >= 8192 or time.monotonic() > deadline:
                    raise ValueError("Handshake")
                buf.extend(read_exact(sock, 1))
            lines = buf.decode("ascii").split("\r\n")
            if lines[0] != "GET /pcm HTTP/1.1":
                raise ValueError("Pfad")
            headers = {}
            for line in lines[1:-2]:
                k, v = line.split(":", 1)
                k = k.lower()
                if k in headers:
                    raise ValueError("Doppelter Header")
                headers[k] = v.strip()
            key = headers.get("sec-websocket-key", "")
            protocols = [v.strip() for v in headers.get("sec-websocket-protocol", "").split(",")]
            if (headers.get("host") != f"127.0.0.1:{server.server_address[1]}"
                    or headers.get("origin") not in server.origins
                    or headers.get("upgrade", "").lower() != "websocket"
                    or "upgrade" not in [v.strip().lower() for v in headers.get("connection", "").split(",")]
                    or headers.get("sec-websocket-version") != "13"
                    or len(base64.b64decode(key, validate=True)) != 16
                    or len(protocols) != 2 or protocols[0] != PROTOCOL
                    or not re.fullmatch(r"[A-Za-z0-9_-]{22,128}", protocols[1])
                    or "content-length" in headers or "transfer-encoding" in headers):
                raise ValueError("Handshake")
            session = server.hub.claim(protocols[1])
            if session is None:
                raise ValueError("Token")
            accept = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
            sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                          "Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept +
                          "\r\nSec-WebSocket-Protocol: " + PROTOCOL + "\r\n\r\n").encode("ascii"))
            upgraded = True
            credit, stamp = 30., time.monotonic()
            while not server.stopping.is_set() and not session.closed:
                readable, _, _ = select.select([sock], [], [], .005)
                if readable:
                    opcode, data = receive_control(sock)
                    now = time.monotonic()
                    credit = min(30., credit + (now - stamp) * 30)
                    stamp = now
                    if credit < 1:
                        raise ValueError("Ratenlimit")
                    credit -= 1
                    if opcode == 8:
                        send_frame(sock, 8, data)
                        return
                    if opcode == 9:
                        send_frame(sock, 10, data)
                block = server.hub.take(session)
                if block is not None:
                    send_frame(sock, 2, block)
            send_frame(sock, 8, struct.pack("!H", 1001))
        except (ValueError, UnicodeError, KeyError):
            try:
                if upgraded:
                    send_frame(sock, 8, struct.pack("!H", 1002))
                else:
                    sock.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
        except (OSError, EOFError):
            pass
        finally:
            if session is not None:
                server.hub.release(session)


class Sidecar(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False
    request_queue_size = 8

    def __init__(self, origins, port=0):
        self.origins = frozenset(origins)
        for origin in self.origins:
            u = urlsplit(origin)
            if (u.scheme not in ("http", "https") or u.hostname not in ("127.0.0.1", "localhost")
                    or u.username or u.password or u.path or u.query or u.fragment or u.port is None):
                raise ValueError("Nur exakte lokale Origin")
        if not self.origins:
            raise ValueError("Origin fehlt")
        self.hub = Hub()
        self.stopping = threading.Event()
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(("127.0.0.1", port), Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def shutdown(self):
        self.stopping.set()
        super().shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", action="append", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    # Privates IPC: uint32 LE Länge, dann Typ J (JSON) oder P
    # (32 ASCII-Zeichen Sitzungs-ID + unveränderter PCM-Block).
    # Antworten sind einzelne JSON-Zeilen ausschließlich auf der privaten Pipe.
    with Sidecar(args.origin, args.port) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .05})
        thread.start()
        def reply(obj):
            print(json.dumps(obj), flush=True)
        reply({"port": server.server_address[1]})
        try:
            while True:
                prefix = sys.stdin.buffer.read(4)
                if not prefix:
                    break
                if len(prefix) != 4:
                    break
                n = struct.unpack("<I", prefix)[0]
                if not 1 <= n <= MAX_BLOCK + 33:
                    reply({"error": "invalid"})
                    break
                data = sys.stdin.buffer.read(n)
                if len(data) != n:
                    break
                try:
                    if data[:1] == b"J":
                        req = json.loads(data[1:])
                        if req["op"] == "issue":
                            reply({"token": server.hub.issue(req["session"], req["streams"])})
                        elif req["op"] == "revoke":
                            server.hub.revoke(req["session"])
                            reply({"ok": True})
                        elif req["op"] == "stop":
                            reply({"ok": True})
                            break
                        else:
                            raise ValueError("IPC")
                    elif data[:1] == b"P":
                        reply({"ok": server.hub.publish(data[1:33].decode("ascii"), data[33:])})
                    else:
                        raise ValueError("IPC")
                except Exception:
                    # Keine untrusted Details oder Token auf stderr.
                    reply({"error": "invalid"})
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
