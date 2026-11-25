"""CPU-Tests der Sitzungsgrenze; der unveränderte Sidecar ist separat geprüft."""
import queue
import threading
import time
import unittest
from types import SimpleNamespace

from sirens.contracts import Ablehnung
from sirens.realtime.pcm import pack, unpack
from sirens.realtime.sessions import Session, fixture_pcm
from sirens.realtime.sidecar import Hub


class Worker:
    def __init__(self):
        self.worker = SimpleNamespace(alive=lambda: True)
        self.started = threading.Event()
        self.release = threading.Event()

    def start(self, **kwargs):
        pass

    def request(self, kind, params=None, audio=None):
        if kind == "process":
            self.started.set()
            if not self.release.wait(5):
                raise ValueError("Test-Worker nicht freigegeben")
            return {}, audio
        return {}, b""

    def close(self):
        self.release.set()


class Sidecar:
    def __init__(self):
        self.process = SimpleNamespace(poll=lambda: None)
        self.blocks = queue.Queue()

    def json(self, **kwargs):
        return {"token": "test"}

    def request(self, data):
        self.blocks.put(unpack(data[33:])[0])
        return {"ok": True}

    def close(self):
        pass


class TwoEpochs(unittest.TestCase):
    def setUp(self):
        self.worker, self.sidecar = Worker(), Sidecar()
        manager = SimpleNamespace(
            sources=SimpleNamespace(load=lambda _: fixture_pcm(0, 4096)),
            supervisor=lambda *args, **kwargs: self.worker,
            registry=None, gpu=None, origins=set(),
            sidecar_factory=lambda _: self.sidecar,
            recordings=SimpleNamespace(close_session=lambda _: None),
        )
        self.session = Session(manager, "mock", 48000)
        self.session.asset = {"id": "fixture", "nframes": 4096}
        self.session.data["state"] = "loading"
        self.session.job = {"state": "queued", "progress": 0}
        self.session.thread = threading.Thread(target=self.session._run, daemon=True)
        self.session.thread.start()
        self.addCleanup(self.shutdown)
        deadline = time.monotonic() + 5
        while self.session.snapshot()["state"] == "loading" and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertEqual(self.session.snapshot()["state"], "ready")
        with self.session.lock:
            self.session._state("playing")

    def shutdown(self):
        self.worker.release.set()
        self.session.close()

    def render(self, audio_epoch, seq, **extra):
        body = dict(epoch=self.session.snapshot()["epoch"], audio_epoch=audio_epoch,
                    seq=seq, source_frame=seq * 256, start_frame=seq * 256,
                    nframes=256)
        body.update(extra)
        return self.session.render(body)

    def packets(self, count):
        self.worker.release.set()
        return [(h["epoch"], h["seq"]) for h in
                (self.sidecar.blocks.get(timeout=5) for _ in range(count))]

    def rejected(self, code, *args, **kwargs):
        with self.assertRaises(Ablehnung) as raised:
            self.render(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def test_alternating_epochs(self):
        self.render(10, 0)
        self.assertTrue(self.worker.started.wait(5))
        self.render(11, 0)
        self.render(10, 1)
        self.render(11, 1)
        self.rejected("invalid", 10, 1)
        self.assertEqual(self.packets(4), [(10, 0), (11, 0), (10, 1), (11, 1)])

    def test_third_epoch_evicts_oldest_even_in_flight(self):
        self.render(10, 0)
        self.assertTrue(self.worker.started.wait(5))
        self.render(11, 0)
        self.render(10, 1)
        self.render(12, 0)
        self.rejected("stale_epoch", 9, 0)
        self.rejected("stale_epoch", 10, 2)
        self.assertEqual(self.packets(2), [(11, 0), (12, 0)])

    def test_control_epoch_discards_both(self):
        self.render(10, 0)
        self.assertTrue(self.worker.started.wait(5))
        self.render(11, 0)
        with self.session.lock:
            self.session._epoch()
        self.rejected("stale_epoch", 11, 1, epoch=0)
        self.render(12, 0)
        self.assertEqual(self.packets(1), [(12, 0)])

    def test_seek_type_and_pcm_flag(self):
        self.rejected("invalid", 10, 0, seek=1)
        self.rejected("invalid", 10, 0, seek="true")
        self.render(10, 0, seek=True)
        self.render(10, 1, seek=False)
        self.worker.release.set()
        first = self.sidecar.blocks.get(timeout=5)
        second = self.sidecar.blocks.get(timeout=5)
        self.assertEqual((first["flags"], first["seek"]), (1, True))
        self.assertEqual((second["flags"], second["seek"]), (0, False))


class SidecarBoundary(unittest.TestCase):
    def test_interleaved_epochs_survive_real_sidecar(self):
        hub = Hub()
        sid = "a" * 32
        hub.issue(sid, [1])
        for epoch, seq in ((10, 0), (11, 0), (10, 1), (11, 1)):
            block = pack(dict(protocol_version=1, stream_id=1, epoch=epoch, seq=seq,
                              start_frame=seq * 256, nframes=256, channels=2,
                              flags=0, sample_rate=48000), bytes(256 * 8))
            self.assertTrue(hub.publish(sid, block))
        self.assertEqual([(h["epoch"], h["seq"]) for h in
                          (unpack(hub.take(hub.sessions[sid]))[0] for _ in range(4))],
                         [(10, 0), (11, 0), (10, 1), (11, 1)])

    def test_third_epoch_and_reset(self):
        hub = Hub()
        sid = "a" * 32
        hub.issue(sid, [1])
        def block(epoch, seq=0):
            return pack(dict(protocol_version=1, stream_id=1, epoch=epoch, seq=seq,
                             start_frame=seq * 256, nframes=256, channels=2,
                             flags=0, sample_rate=48000), bytes(256 * 8))
        for epoch in (10, 11, 12):
            self.assertTrue(hub.publish(sid, block(epoch)))
        for epoch in (9, 10, 11):
            self.assertFalse(hub.publish(sid, block(epoch)))
        self.assertTrue(hub.publish(sid, block(11, 1)))
        self.assertEqual([unpack(hub.take(hub.sessions[sid]))[0]["epoch"]
                          for _ in range(3)], [11, 12, 11])
        self.assertTrue(hub.publish(sid, block(12, 1)))
        hub.reset(sid)
        self.assertIsNone(hub.take(hub.sessions[sid]))
        self.assertTrue(hub.publish(sid, block(13)))

    def test_pcm_flags(self):
        h = dict(protocol_version=1, stream_id=1, epoch=10, seq=0,
                 start_frame=0, nframes=256, channels=2, flags=1, sample_rate=48000)
        payload = bytes(256 * 8)
        block = bytearray(pack(h, payload))
        self.assertEqual(block[27], 1)
        self.assertIs(unpack(block)[0]["seek"], True)
        self.assertIs(unpack(pack(dict(h, flags=0), payload))[0]["seek"], False)
        with self.assertRaises(Ablehnung):
            pack(dict(h, flags=2), payload)
        block[27] = 2
        with self.assertRaises(Ablehnung):
            unpack(block)


if __name__ == "__main__":
    unittest.main()
