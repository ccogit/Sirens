import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Magenta RealTime läuft über WSL2 statt einer Windows-Umgebung .venv-spike-*; eigener Test in
# tests/realtime/test_magenta_spike.py.
WSL = {"magenta-realtime"}


class SpikeRunner(unittest.TestCase):
    def test_dry_runs(self):
        for script in sorted((ROOT / "benchmarks/spikes").glob("*/messen.py")):
            with self.subTest(script=script):
                module = ".".join(script.relative_to(ROOT).with_suffix("").parts)
                p = subprocess.run([sys.executable, "-m", module, "--dry-run"],
                                   cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn("Dry-Run OK", p.stdout)
                if script.parent.name in WSL:
                    continue
                p = subprocess.run([sys.executable, "-m", module],
                                   cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(".venv-spike-", p.stderr)

    def test_install_guards(self):
        scripts = list((ROOT / "benchmarks/spikes").glob("*/install.ps1"))
        self.assertEqual(len(scripts), 10)
        for script in scripts:
            text = script.read_text(encoding="utf-8")
            self.assertIn("$ModelleLaden", text)
            self.assertIn("$Entfernen", text)
            if script.parent.name not in WSL:
                self.assertIn("if ($ModelleLaden)", text)
                self.assertIn("if ($Entfernen)", text)
            self.assertNotIn("pip install", text.lower())
            for cmd in ("invoke-webrequest", "curl ", "wget ", "git clone", "huggingface-cli"):
                self.assertNotIn(cmd, text.lower())
