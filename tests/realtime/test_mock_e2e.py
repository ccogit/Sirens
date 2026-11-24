"""Vertragsgrenzen für den Mock-Durchstich (ohne GPU)."""
import unittest

from sirens.contracts import Ablehnung
from sirens.realtime.contracts import (
    SESSION_TRANSITIONS, transition, validate_command, source_path,
)
from tempfile import TemporaryDirectory
from pathlib import Path


class MockE2EContractTests(unittest.TestCase):
    def test_session_transitions(self):
        state = "created"
        for target in ("loading", "ready", "playing", "paused", "playing",
                       "stopping", "closed"):
            state = transition(SESSION_TRANSITIONS, state, target)
        with self.assertRaises(Ablehnung):
            transition(SESSION_TRANSITIONS, state, "playing")

    def test_old_epoch_rejected(self):
        with self.assertRaises(Ablehnung):
            validate_command({"command": "play", "epoch": 0, "seq": 0,
                              "args": {}}, 1)

    def test_source_traversal_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            (root.parent / "outside.wav").touch()
            with self.assertRaises(Ablehnung):
                source_path(root, "../outside.wav")


import base64
import hashlib
import socket
import struct
import time
from dataclasses import replace

from hilfe import ServerFall
from sirens.realtime.pcm import unpack
from sirens.realtime.schemas import validate
from sirens.realtime.sessions import FIXTURE_ID, fixture_pcm


class MockHTTP(ServerFall):
    PREFIX = "/api/rt/v1/"

    def setUp(self):
        super().setUp()
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)

    def request(self, method, path, body=None, expected=200):
        status, value, _ = self.http(method, self.PREFIX + path, body)
        self.assertEqual(status, expected, value)
        return value

    def wait_state(self, sid, wanted):
        end = time.monotonic() + 12
        while time.monotonic() < end:
            result = self.request("GET", "sessions/" + sid)
            if result["state"] == wanted:
                return result
            if result["state"] in ("closed", "error"):
                self.fail(str(result))
            time.sleep(.05)
        self.fail("Sitzungszustand nicht erreicht: " + wanted)

    def command(self, s, name, args=None, expected=200):
        return self.request("POST", "sessions/" + s["id"] + "/commands",
                            {"epoch": s["epoch"], "seq": 0 if s["seq"] is None else s["seq"]+1,
                             "command": name, "args": args or {}}, expected)

    def create(self):
        s = self.request("POST", "sessions", {"capability_id": "mock", "sample_rate": 48000}, 201)
        validate("session", s)
        self.command(s, "load", {"asset_id": FIXTURE_ID})
        return self.wait_state(s["id"], "ready")

    def ws(self, transport, token, origin):
        conn = socket.create_connection(("127.0.0.1", transport["port"]), timeout=5)
        self.addCleanup(conn.close)
        key = base64.b64encode(b"0123456789abcdef").decode()
        request = (
            "GET /pcm HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nOrigin: %s\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Protocol: sirens.pcm.v1, %s\r\n\r\n"
        ) % (transport["port"], origin, key, token)
        conn.sendall(request.encode("ascii"))
        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            b = conn.recv(1)
            if not b:
                break
            response.extend(b)
        return conn, bytes(response)

    def read_exact(self, conn, count):
        data = bytearray()
        while len(data) < count:
            piece = conn.recv(count-len(data))
            self.assertTrue(piece, "WebSocket geschlossen")
            data.extend(piece)
        return bytes(data)

    def test_lifecycle_and_real_worker_pcm(self):
        before = {p: hashlib.sha256(p.read_bytes()).digest()
                  for p in self.cfg.music_root.rglob("*") if p.is_file()}
        s = self.create()
        validate("job", self.request("GET", "jobs/" + s["job_id"]))
        validate("asset", self.request("GET", "assets/" + FIXTURE_ID))
        path = "sessions/" + s["id"]
        t = self.request("POST", path + "/transport", {})
        _, denied = self.ws(t, "x"*43, self.basis)
        self.assertIn(b"403 Forbidden", denied)
        _, denied = self.ws(t, t["token"], "https://example.invalid")
        self.assertIn(b"403 Forbidden", denied)
        conn, response = self.ws(t, t["token"], self.basis)
        self.assertIn(b"101 Switching Protocols", response)
        s = self.command(s, "set_param", {"name": "gain", "value": .5})
        s = self.command(s, "play")
        self.request("POST", path + "/render",
                     {"epoch": s["epoch"], "seq": 0, "source_frame": 0,
                      "start_frame": 0, "nframes": 256}, 202)
        a, b = self.read_exact(conn, 2)
        self.assertEqual(a, 0x82)
        length = struct.unpack("!H", self.read_exact(conn, 2))[0] if b == 126 else b
        header, raw = unpack(self.read_exact(conn, length))
        self.assertEqual((header["start_frame"], header["nframes"]), (0, 256))
        dry = struct.unpack("<512f", fixture_pcm(0, 256))
        self.assertEqual(struct.unpack("<512f", raw), tuple(v*.5 for v in dry))
        s = self.command(s, "pause")
        old = s
        s = self.command(s, "seek", {"source_frame": 128})
        self.assertEqual(self.command(old, "play", expected=409)["error"], "stale_epoch")
        s = self.command(s, "play")
        session = self.server.app.rt_sessions.get(s["id"])
        worker = session.worker.worker.process
        sidecar = session.sidecar.process
        closed = self.request("POST", path + "/close", {})
        self.assertEqual(closed["state"], "closed")
        self.assertEqual(closed, self.request("POST", path + "/close", {}))
        self.assertIsNotNone(worker.poll())
        self.assertIsNotNone(sidecar.poll())
        after = {p: hashlib.sha256(p.read_bytes()).digest()
                 for p in self.cfg.music_root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_worker_kill_closes_sidecar(self):
        s = self.create()
        session = self.server.app.rt_sessions.get(s["id"])
        p = session.worker.worker.process
        sidecar = session.sidecar.process
        p.kill()
        self.wait_state(s["id"], "error")
        self.request("POST", "sessions/" + s["id"] + "/close", {})
        self.assertIsNotNone(p.poll())
        self.assertIsNotNone(sidecar.poll())

    def test_flag_and_origin(self):
        self.server.app.cfg = replace(self.cfg, rt_enabled=False)
        for method, path, body in (
            ("GET", "capabilities", None), ("GET", "gpu", None),
            ("POST", "sessions", {}), ("GET", "jobs/" + FIXTURE_ID, None),
            ("GET", "assets/" + FIXTURE_ID, None),
            ("POST", "sessions/" + FIXTURE_ID + "/close", {}),
        ):
            self.assertEqual(self.request(method, path, body, 503)["error"], "unavailable")
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)
        self.assertEqual(self.http("POST", self.PREFIX + "sessions", {},
                                   headers={"Origin": "https://example.invalid"})[0], 403)
        self.assertEqual(self.request("GET", "assets/" + FIXTURE_ID)["id"], FIXTURE_ID)
        self.assertEqual(self.http("GET", "/api/health")[1]["status"], "ok")
