import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sirens.contracts import Ablehnung
from sirens.realtime.worker_supervisor import WorkerSupervisor

WORKER = r"""
import json, struct, sys, time
def send(kind, rid, payload):
    raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload)).encode()
    sys.stdout.buffer.write(struct.pack("<I", len(raw)) + raw)
    sys.stdout.buffer.flush()
from pathlib import Path
size, = struct.unpack("<I", sys.stdin.buffer.read(4))
msg = json.loads(sys.stdin.buffer.read(size))
rid, p = msg["request_id"], msg["payload"]
out = Path(p["out_dir"])
(out / "vocals.wav").write_bytes(b"test")
send("heartbeat", rid, {"progress": .5})
mode = p["params"].get("mode", 0)
if mode == 1:
    time.sleep(10)
elif mode == 2:
    send("result", rid, {"files": ["../foreign.wav"]})
elif mode == 3:
    (out / "foreign.wav").write_bytes(b"foreign")
    send("result", rid, {"files": ["vocals.wav"]})
else:
    time.sleep(.3)
    send("result", rid, {"files": ["vocals.wav"]})
sys.stdin.buffer.read()
"""


class Registry:
    def __init__(self, root):
        self.root = root

    def resolve(self, name):
        return {"command": [sys.executable, "-u", "-c", WORKER],
                "capability": {"device": "cpu", "controls": [
                    {"name": "mode", "min": 0, "max": 3}], "mock": True}}


class FileJobs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.music = self.root / "music"
        self.music.mkdir()
        self.rt = self.root / "rt"
        self.source = self.music / "song.wav"
        self.source.write_bytes(b"original")
        self.jid = "a" * 32
        self.out = self.rt / "jobs" / self.jid
        self.ready = self.out.with_name(self.jid + ".ready")
        self.sup = WorkerSupervisor(Registry(self.root), "fake",
                                    music_root=self.music, realtime_dir=self.rt)
        self.addCleanup(self.sup.close)
        self.sup.start(user_action=True)

    def request(self, mode=0, timeout=5):
        return self.sup.request_file_job(self.jid, self.source, self.out, {"mode": mode}, timeout)

    def wait_progress(self):
        end = time.monotonic() + 3
        while self.sup.file_progress is None and time.monotonic() < end:
            time.sleep(.01)
        self.assertEqual(self.sup.file_progress, .5)

    def test_success(self):
        with ThreadPoolExecutor() as pool:
            future = pool.submit(self.request)
            self.wait_progress()
            self.assertEqual(future.result()["files"], ["vocals.wav"])
        self.assertFalse(self.out.exists())
        self.assertEqual((self.ready / "vocals.wav").read_bytes(), b"test")
        self.assertEqual(self.source.read_bytes(), b"original")

    def test_cancel(self):
        with ThreadPoolExecutor() as pool:
            future = pool.submit(self.request, 1)
            self.wait_progress()
            self.sup.cancel()
            with self.assertRaises(Ablehnung):
                future.result(timeout=5)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.ready.exists())

    def test_timeout(self):
        with self.assertRaises(Ablehnung) as ctx:
            self.request(1, .5)
        self.assertEqual(ctx.exception.code, "deadline_missed")
        self.assertFalse(self.out.exists())

    def test_paths(self):
        foreign = self.root / "foreign.wav"
        foreign.write_bytes(b"untouched")
        for source, out in [(foreign, self.out), (self.source, self.root / "escape")]:
            with self.assertRaises(Ablehnung):
                self.sup.request_file_job(self.jid, source, out, {}, 5)
        self.assertFalse(self.out.exists())
        self.assertEqual(foreign.read_bytes(), b"untouched")

    def test_result_escape(self):
        with self.assertRaises(Ablehnung):
            self.request(2)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.ready.exists())

    def test_unreported_file(self):
        with self.assertRaises(Ablehnung):
            self.request(3)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.ready.exists())
