import hashlib
import io
import json
import math
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from sirens.production.mixing import fetch_chain, mix, analyze_return


def fixture(root, with_bass=True):
    frames = 48000
    tracks, stems = [], []
    names = [("kick", "drums")] + ([("sub", "bass"), ("tone", "synths")] if with_bass else [])
    for name, role in names:
        path = root / (name + ".wav")
        channels = 1 if name != "tone" else 2
        samples = bytearray()
        for i in range(frames):
            if name == "kick":
                val = 7000000 if i == 12000 else 0
            else:
                val = round(2500000 * math.sin(2 * math.pi * (55 if name == "sub" else 1000) * i / 48000))
            samples.extend(val.to_bytes(3, "little", signed=True) * channels)
        with wave.open(str(path), "wb") as wav:
            wav.setparams((channels, 3, 48000, frames, "NONE", ""))
            wav.writeframes(samples)
        tracks.append(dict(id=name, role=role, backend="instrument", patch=name,
                           events=[], automation=[]))
        stems.append(dict(track_id=name, role=role, file=path.name, channels=channels,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          source=dict(backend="test", patch=name, revision="1")))
    plan = dict(schema_version=1, seed=1, bpm=240, key=None, meter=[4, 4],
                ppq=960, total_bars=1, tail_seconds=0,
                sections=[dict(id="one", start_bar=0, bars=1, intent="test")],
                tracks=tracks, asset_requests=[], mix=dict(target_lufs=-12, ceiling_dbtp=-1))
    if with_bass:
        plan["mix"]["tracks"] = {"tone": {"pan": .7, "eq_db": -2}}
    return plan, dict(schema_version=1, sample_rate=48000, frames=frames, stems=stems)


class MixingTests(unittest.TestCase):
    def test_chain_readonly(self):
        calls = []
        def open_mock(url, timeout):
            calls.append((url, timeout))
            return io.BytesIO(b'{"status":"degraded","steps":[]}')
        self.assertEqual(fetch_chain("bass", opener=open_mock)["status"], "degraded")
        self.assertEqual(calls[0][0], "http://127.0.0.1:8099/api/chains/bass")
        with self.assertRaises(ValueError):
            fetch_chain("../master", opener=open_mock)
        self.assertEqual(len(calls), 1)

    @unittest.skipUnless(shutil.which("ffmpeg"), "local ffmpeg required")
    def test_mix_sinus_and_impulse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, stems = fixture(root)
            report = mix(plan, stems, root)
            self.assertEqual(report, json.loads((root / "mix_report.json").read_text()))
            for name in ("dry.wav", "mix.wav", "master.wav"):
                with wave.open(str(root / name), "rb") as wav:
                    self.assertEqual((wav.getnframes(), wav.getframerate(),
                                      wav.getsampwidth(), wav.getnchannels()),
                                     (48000, 48000, 3, 2))
            for name, limit in (("dry", -6), ("premaster", -6), ("measured", -1)):
                m = report[name]
                self.assertEqual(m["clipped_samples"], 0)
                self.assertLessEqual(m["true_peak_dbtp"], limit)
                self.assertTrue(math.isfinite(m["lufs"]))
                self.assertTrue(math.isfinite(m["lra"]))
            self.assertLess(report["measured"]["sub_side_mid_db"], -15)
            for stem in stems["stems"]:
                self.assertEqual(hashlib.sha256((root / stem["file"]).read_bytes()).hexdigest(),
                                 stem["sha256"])
            before = (root / "master.wav").read_bytes()
            returned = analyze_return(root / "master.wav")
            self.assertIsNone(returned["stems"])
            self.assertEqual(returned["measured"], report["measured"])
            with self.assertRaises(FileExistsError):
                mix(plan, stems, root)
            self.assertEqual(before, (root / "master.wav").read_bytes())

    @unittest.skipUnless(shutil.which("ffmpeg"), "local ffmpeg required")
    def test_impulse_alignment_and_optional_loudness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, stems = fixture(root, with_bass=False)
            plan["mix"]["target_lufs"] = None
            report = mix(plan, stems, root)
            with wave.open(str(root / "dry.wav"), "rb") as wav:
                data = wav.readframes(48000)
            self.assertEqual(data[:12000*6], bytes(12000*6))
            self.assertNotEqual(data[12000*6:12001*6], bytes(6))
            self.assertEqual(report["mastering"]["requested_gain_db"], 0)

    def test_invalid_stem_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, stems = fixture(root, with_bass=False)
            stems["stems"][0]["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                mix(plan, stems, root)
            self.assertFalse((root / "master.wav").exists())
