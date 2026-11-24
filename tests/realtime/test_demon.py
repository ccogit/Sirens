"""DEMON-Vertrag ohne GPU, Netzwerk oder Gewichte."""
import json
from pathlib import Path
import unittest

from sirens.realtime.schemas import validate
from workers.demon.adapter import Adapter, Unavailable


class FakeBackend:
    def __init__(self):
        self.closed = False
        self.calls = []

    def prepare(self, samples, prompt):
        self.calls.append(prompt)
        return list(samples)

    def tick(self, handle, seed, strength):
        return [x * strength for x in handle]

    def decode(self, handle, latent):
        return latent

    def close(self):
        self.closed = True


class DemonTest(unittest.TestCase):
    def test_descriptor(self):
        a = Adapter(FakeBackend)
        self.assertFalse(validate("capability", a.probe())["available"])

    def test_lifecycle_epoch_bypass(self):
        a = Adapter(FakeBackend)
        a.load(epoch=1, strength=0.5)
        a.warmup()
        self.assertEqual(a.process([1., -1.], epoch=1), [0.5, -0.5])
        a.load(epoch=2, prompt="jazz", bypass=True)
        with self.assertRaises(Unavailable):
            a.process([1., -1.], epoch=1)
        self.assertEqual(a.process([1., -1.], epoch=2), [1., -1.])
        a.load(epoch=3, prompt="jazz", strength=0.25)
        self.assertEqual(a.process([0.5, -0.5], epoch=3), [0.125, -0.125])
        self.assertEqual(a.backend.calls[-1], "jazz")
        a.cancel()
        with self.assertRaises(Unavailable):
            a.process([1., -1.])
        backend = a.backend
        a.unload()
        self.assertTrue(backend.closed)
        self.assertFalse(a.health()["loaded"])

    def test_missing_installation(self):
        def missing():
            raise FileNotFoundError("Gewichte fehlen")
        a = Adapter(missing)
        with self.assertRaisesRegex(Unavailable, "install.ps1"):
            a.load()
        self.assertFalse(a.probe()["available"])
        self.assertTrue(a.health()["failed"])

    def test_cancel_during_tick(self):
        a = Adapter(FakeBackend)
        a.load()
        original = a.backend.tick
        def cancel(*args):
            a.cancel()
            return original(*args)
        a.backend.tick = cancel
        with self.assertRaises(Unavailable):
            a.process([1., -1.])

    def test_invalid(self):
        a = Adapter(FakeBackend)
        with self.assertRaises(ValueError):
            a.load(strength=float("nan"))
        a.load()
        with self.assertRaises(ValueError):
            a.process([float("nan"), 0.])
