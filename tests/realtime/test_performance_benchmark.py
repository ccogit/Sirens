import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which("node"), "Node fehlt")
class PerformanceBenchmark(unittest.TestCase):
    def test_nine_wavs_and_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "demos"
            cmd = ["node", str(ROOT / "benchmarks/performance/render.mjs"), str(folder)]
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            data = json.loads((folder / "render.json").read_text())
            self.assertEqual(len(data["results"]), 9)
            for r in data["results"]:
                with wave.open(str(folder / (r["name"] + ".wav")), "rb") as audio:
                    self.assertEqual(audio.getframerate(), data["rate"])
                    self.assertEqual(audio.getnframes(), r["frames"])
                    self.assertEqual(audio.getnchannels(), 1)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, timeout=30).returncode, 0)
            baseline = Path(tmp) / "baseline.json"
            baseline.write_text(json.dumps(dict.fromkeys(
                ("os","python","node","ffmpeg","gpus","wsl","disk","git","notes"))))
            output = Path(tmp) / "result.json"
            subprocess.run([sys.executable, str(ROOT / "benchmarks/performance/report.py"),
                            str(baseline), str(folder / "render.json"), str(output),
                            "--note", "Nur Test, nicht gehört"], check=True, timeout=20)
            subprocess.run([sys.executable, str(ROOT / "benchmarks/result.py"),
                            str(output)], check=True, timeout=20)
            self.assertEqual(json.loads(output.read_text())["gate"], "nicht_gemessen")
