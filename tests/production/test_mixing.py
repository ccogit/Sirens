import hashlib
import io
import json
import math
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from sirens.production.mixing import fetch_chain, mix as run_mix, analyze_return as run_analyze_return


def mix(*args, **kwargs):
    # Worker uses stdlib + external ffmpeg only; explicit interpreter for tests.
    return run_mix(*args, worker_python=sys.executable, **kwargs)


def analyze_return(*args, **kwargs):
    return run_analyze_return(*args, worker_python=sys.executable, **kwargs)


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
        with tempfile.TemporaryDirectory(prefix="mix Umlaute ä ") as tmp:
            root = Path(tmp)
            plan, stems = fixture(root)
            report = mix(plan, stems, root)
            self.assertEqual(report, json.loads((root / "mix_report.json").read_text(encoding="utf-8")))
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


    @unittest.skipUnless(shutil.which("ffmpeg"), "local ffmpeg required")
    def test_reproducible_revision_and_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "first", Path(tmp) / "second"
            first.mkdir()
            second.mkdir()
            plan, stems = fixture(first)
            second_plan, second_stems = fixture(second)
            report = mix(plan, stems, first, reference=first / "tone.wav")
            comparison = report["comparison"]
            self.assertLessEqual(abs(comparison["master"]["lufs"] -
                                     comparison["reference"]["lufs"]), .5)
            for variant in ("master", "reference"):
                self.assertLessEqual(comparison[variant]["true_peak_dbtp"], -1)
            before = (first / "master.wav").read_bytes()
            same = mix(second_plan, second_stems, second)
            self.assertEqual(before, (second / "master.wav").read_bytes())
            self.assertEqual(same["measured"], report["measured"])
            third = Path(tmp) / "third"
            third.mkdir()
            revised_plan, revised_stems = fixture(third)
            revised_plan["mix"]["tracks"]["tone"]["gain_db"] = -20
            revised = mix(revised_plan, revised_stems, third)
            self.assertNotEqual(revised["measured"]["bands_dbfs"],
                                report["measured"]["bands_dbfs"])
            self.assertEqual(before, (first / "master.wav").read_bytes())


    def test_worker_failure_no_publication(self):
        # Real child process, no ffmpeg dependency. A Python executable
        # is intentionally not a usable ffmpeg binary.
        with tempfile.TemporaryDirectory(prefix="mix Umlaute ä ") as tmp:
            root = Path(tmp)
            plan, stems = fixture(root, with_bass=False)
            with self.assertRaisesRegex(RuntimeError, "mix worker failed"):
                mix(plan, stems, root, ffmpeg=sys.executable)
            self.assertFalse((root / "master.wav").exists())
            self.assertFalse((root / "mix_report.json").exists())
            self.assertFalse(list(root.glob(".mix-*")))
            self.assertEqual(hashlib.sha256((root / stems["stems"][0]["file"]).read_bytes()).hexdigest(),
                             stems["stems"][0]["sha256"])

    def test_missing_worker_no_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, stems = fixture(root, with_bass=False)
            with self.assertRaisesRegex(RuntimeError, "mix worker Python unavailable"):
                run_mix(plan, stems, root, ffmpeg=sys.executable,
                        worker_python=root / "missing-python")
            self.assertFalse((root / "master.wav").exists())
            self.assertFalse(list(root.glob(".mix-*")))


    def test_cancel_worker_no_publication(self):
        class Cancelled(Exception):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, stems = fixture(root, with_bass=False)
            calls = 0

            def cancelled():
                nonlocal calls
                calls += 1
                if calls >= 2:
                    raise Cancelled()

            with self.assertRaises(Cancelled):
                mix(plan, stems, root, cancelled, ffmpeg=sys.executable)
            self.assertGreaterEqual(calls, 2)
            self.assertFalse((root / "master.wav").exists())
            self.assertFalse((root / "mix_report.json").exists())
            self.assertFalse(list(root.glob(".mix-*")))
