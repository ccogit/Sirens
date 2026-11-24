"""WP11 ohne Torch, Netz, GPU und Modellgewichte."""
import unittest
from pathlib import Path
from unittest.mock import patch

from sirens.realtime.model_registry import ModelRegistry
from workers.rave.adapter import RaveAdapter, FRAMES
from workers.after.adapter import AfterAdapter, CHUNK
from workers.rave.runtime import Unavailable


class RaveModel:
    def transform(self, samples, params):
        return [(samples[i] + samples[i+1])/2 + params["latent_0"]*params["morph"]
                for i in range(0, len(samples), 2)]


class AfterModel:
    frames = CHUNK

    def reset(self):
        pass

    def transform(self, structure, timbre, params):
        return [(structure[i] + timbre[i])*0.25 + params["seed"]*0.001
                for i in range(0, len(structure), 2)]


class NeuralMutationTest(unittest.TestCase):
    def test_registry_gated(self):
        registry = ModelRegistry()
        caps = {cap["id"]: cap for cap in registry.capabilities()}
        for name in ("rave", "after"):
            self.assertIn(name, caps)
            self.assertFalse(caps[name]["available"])
            self.assertFalse(caps[name]["mock"])
            self.assertNotEqual(caps[name]["mode"], "streaming")

    def test_rave_lifecycle_and_preset(self):
        adapter = RaveAdapter(RaveModel, allow_unmeasured=True)
        self.assertFalse(adapter.health()["loaded"])
        with self.assertRaises(Unavailable):
            adapter.process([0.0]*FRAMES*2)
        source = [0.1, 0.2]*FRAMES
        adapter.load(latent_0=0.5, morph=0.5, wet=0.5, seed=17)
        adapter.warmup()
        first = adapter.process(source)
        self.assertNotEqual(first, source)
        adapter.cancel()
        with self.assertRaises(Unavailable):
            adapter.process(source)
        adapter.load(latent_0=0.5, morph=0.5, wet=0.5, seed=17)
        self.assertEqual(first, adapter.process(source))
        self.assertEqual(source, adapter.process(source, controls={"wet": 0}))
        adapter.unload()
        self.assertFalse(adapter.health()["loaded"])

    def test_after_reference_and_staged_ipc(self):
        adapter = AfterAdapter(AfterModel, allow_unmeasured=True)
        source, ref = [0.1]*CHUNK*2, [0.4]*CHUNK*2
        adapter.load(seed=17, wet=1)
        self.assertEqual([], adapter.process(source))
        self.assertEqual([], adapter.process(ref))
        first = adapter.process([])
        self.assertEqual(first, adapter.transform(source, ref))
        self.assertNotEqual(first, adapter.transform(source, [0.2]*CHUNK*2))
        adapter.load(seed=17, wet=1)
        self.assertEqual(first, adapter.transform(source, ref))
        adapter.cancel()
        with self.assertRaises(Unavailable):
            adapter.transform(source, ref)
        adapter.unload()
        self.assertFalse(adapter.health()["loaded"])
        self.assertEqual([], adapter.output)

    def test_missing_and_invalid(self):
        def missing():
            raise FileNotFoundError("Keine Gewichte")
        for cls in (RaveAdapter, AfterAdapter):
            with self.assertRaises(Unavailable):
                cls(missing, allow_unmeasured=True).load()
            with self.assertRaises(Unavailable):
                cls(missing).load()
            with self.assertRaises(ValueError):
                cls(missing, allow_unmeasured=True).load(seed=0.5)
