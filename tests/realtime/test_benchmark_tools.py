import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks import baseline, manifest, result


def fake_run(args, **kwargs):
    outputs = {("git", "rev-parse", "HEAD"): b"a" * 40 + b"\n",
               ("git", "status", "--porcelain"): b"?? /home/private-user/music.wav\n",
               ("node", "--version"): b"v22.1.0\n",
               ("wsl", "--list", "--quiet"): b"PrivateDistro\n"}
    if tuple(args) not in outputs:
        raise FileNotFoundError("/home/private-user/bin/tool")
    return subprocess.CompletedProcess(args, 0, stdout=outputs[tuple(args)], stderr=b"")


class Baseline(unittest.TestCase):
    def test_fehlende_werkzeuge_und_datensparsamkeit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(baseline.subprocess, "run", side_effect=fake_run):
            data = baseline.collect(Path(tmp))
        self.assertIsNone(data["ffmpeg"])
        self.assertIsNone(data["gpus"])
        self.assertFalse(data["git"]["clean"])
        self.assertEqual(data["git"]["sha"], "a" * 40)
        self.assertTrue(data["wsl"])
        self.assertEqual(data["node"], "22.1.0")
        self.assertTrue(any("ffmpeg" in n for n in data["notes"]))
        self.assertTrue(any("nvidia-smi" in n for n in data["notes"]))
        for private in ("private-user", "PrivateDistro", tmp):
            self.assertNotIn(private, json.dumps(data))

    def test_gpu_csv(self):
        def gpu_run(args, **kwargs):
            if args[0] == "nvidia-smi":
                return subprocess.CompletedProcess(args, 0, stdout=b"580.1, NVIDIA GeForce RTX 5080, 16384, 8000\n", stderr=b"")
            return fake_run(args, **kwargs)
        with tempfile.TemporaryDirectory() as tmp, patch.object(baseline.subprocess, "run", side_effect=gpu_run):
            gpu = baseline.collect(Path(tmp))["gpus"][0]
        self.assertEqual(gpu["vram_free_mib"], 8000)
        self.assertEqual(gpu["vram_total_mib"], 16384)
        self.assertEqual(gpu["driver"], "580.1")


class Manifest(unittest.TestCase):
    def test_fehlt_oder_hash_falsch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tracks.json"
            path.write_text(json.dumps({"tracks": [{"pfad": "track.bin", "sha256": "a" * 64,
                                                     "genre": "Techno", "lizenz": "synthetischer Test"}]}))
            with self.assertRaisesRegex(ValueError, "Datei fehlt"):
                manifest.validate(path)
            (path.parent / "track.bin").write_bytes(b"synthetischer Test")
            with self.assertRaisesRegex(ValueError, "SHA-256 stimmt nicht"):
                manifest.validate(path)
            with self.assertRaisesRegex(ValueError, "SHA-256 stimmt nicht"):
                manifest.validate(path, fill_hashes=True)

    def test_hash_eintragen_und_pruefen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tracks.json"
            audio = path.parent / "track.bin"
            audio.write_bytes(b"abc")
            path.write_text(json.dumps({"tracks": [{"pfad": "track.bin", "sha256": None,
                                                     "genre": "House", "lizenz": "Test", "bpm": 120}]}))
            self.assertEqual(manifest.validate(path, fill_hashes=True)["tracks"][0]["sha256"],
                             "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            manifest.validate(path)
            self.assertEqual(audio.read_bytes(), b"abc")


class Result(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(baseline.subprocess, "run", side_effect=fake_run):
            machine = baseline.collect(Path(tmp))
        self.data = {"wp": "WP00", "kandidat": "Test", "gate": "nicht_gemessen", "modus": "unbekannt",
                     "zeitpunkt": "2026-01-01T00:00:00+00:00", "rechner": machine,
                     "messwerte": {phase: dict.fromkeys(result.METRICS) for phase in ("warm", "kalt")},
                     "notizen": ["Nur ein Format-Test"], "befehl": "python -m unittest discover -s tests -v"}

    def test_gueltig_und_bericht(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            result.write(path, self.data)
            self.assertEqual(result.read(path), self.data)
            self.assertIn("| p50_ms | nicht gemessen | nicht gemessen |", result.markdown(self.data))

    def test_pflichtfeld_und_gate(self):
        for field in self.data:
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                del data[field]
                with self.assertRaisesRegex(ValueError, field):
                    result.validate(data)
        self.data["gate"] = "unbekannt"
        with self.assertRaisesRegex(ValueError, "gate: unbekannter Wert"):
            result.validate(self.data)

    def test_messwert_und_perzentile(self):
        warm = self.data["messwerte"]["warm"]
        warm["rtf"] = float("nan")
        with self.assertRaisesRegex(ValueError, "rtf"):
            result.validate(self.data)
        warm["rtf"] = None
        warm.update(p50_ms=10, p95_ms=5)
        with self.assertRaisesRegex(ValueError, "Perzentile"):
            result.validate(self.data)
