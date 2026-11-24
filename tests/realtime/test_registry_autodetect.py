"""Die Registry findet installierte Worker-Umgebungen ohne .env-Eintrag."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from sirens.realtime.model_registry import ModelRegistry

CAP = {"id": "probe", "mock": False, "available": True, "mode": "offline", "sample_rates": [48000],
       "channels": 2, "context_frames": 0, "hop_frames": 1024, "latency_frames": 0, "controls": [],
       "vram_peak_bytes": "unknown", "device": "cuda", "license": "MIT", "model_revision": "test"}


class Autodetect(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        ordner = self.root / "workers" / "probe"
        ordner.mkdir(parents=True)
        (ordner / "worker.py").write_text("", encoding="utf-8")
        self.manifest = ordner / "manifest.json"
        self.schreiben([".venv-probe", ".venv-spike-probe"])

    def schreiben(self, dirs, available=True):
        self.manifest.write_text(json.dumps({
            "version": 1, "name": "probe", "interpreter_env": "SIRENS_RT_PROBE_PYTHON", "python_dirs": dirs,
            "script": "worker.py", "args": [], "capability": {**CAP, "available": available}}), encoding="utf-8")

    def umgebung(self, name):
        teil = ("Scripts", "python.exe") if sys.platform == "win32" else ("bin", "python")
        pfad = self.root.joinpath(name, *teil)
        pfad.parent.mkdir(parents=True)
        pfad.write_bytes(b"")
        return pfad

    def cap(self, env=None):
        caps = {c["id"]: c for c in ModelRegistry(self.root, env=env or {"SIRENS_RT_AUTODETECT": "an"}).capabilities()}
        return caps["probe"]

    def test_ohne_umgebung_nicht_verfuegbar(self):
        self.assertFalse(self.cap()["available"])

    def test_messumgebung_wird_gefunden(self):
        python = self.umgebung(".venv-spike-probe")
        registry = ModelRegistry(self.root, env={"SIRENS_RT_AUTODETECT": "an"})
        self.assertTrue(registry.capabilities()[0]["available"])
        self.assertEqual(registry.entries["probe"]["command"][0], str(python))

    def test_regulaere_umgebung_hat_vorrang(self):
        self.umgebung(".venv-spike-probe")
        python = self.umgebung(".venv-probe")
        self.assertEqual(ModelRegistry(self.root, env={"SIRENS_RT_AUTODETECT": "an"}).entries["probe"]["command"][0], str(python))

    def test_env_eintrag_hat_vorrang(self):
        self.umgebung(".venv-probe")
        eigen = self.umgebung(".venv-eigen")
        registry = ModelRegistry(self.root, env={"SIRENS_RT_AUTODETECT": "an", "SIRENS_RT_PROBE_PYTHON": str(eigen)})
        self.assertEqual(registry.entries["probe"]["command"][0], str(eigen))

    def test_nicht_freigegeben_bleibt_aus(self):
        self.umgebung(".venv-probe")
        self.schreiben([".venv-probe"], available=False)
        self.assertFalse(self.cap()["available"])

    def test_nur_venv_ordner_im_sirens_ordner(self):
        for boese in ("../draussen", "C:/Windows", ".venv/../../x", "venv-ohne-punkt"):
            self.schreiben([boese])
            self.assertFalse(self.cap()["available"], boese)


if __name__ == "__main__":
    unittest.main()
