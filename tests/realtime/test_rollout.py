"""Rollout-Vertrag, ohne GPU, Netz oder Modellgewichte."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rt-install.ps1"
WORKERS = ("demon", "rave", "after", "magenta", "sam_audio", "separation", "stable_audio")


class RolloutTest(unittest.TestCase):
    def test_opt_in_and_scope(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(source.index("if ($DryRun) { return }"), source.index("& py -3.11"))
        self.assertLess(source.index("if (!$ModelleLaden) { return }"), source.index("& $installer -ModelleLaden"))
        self.assertIn("Remove-Item -LiteralPath $target -Recurse -Force", source)
        self.assertIn(".sirens-rt-rollout", source)
        self.assertIn("ReparsePoint", source)
        self.assertNotIn("Invoke-WebRequest", source)
        for worker in WORKERS:
            self.assertTrue((ROOT / "workers" / worker / "install.ps1").is_file())

    def test_dryrun_if_powershell_available(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            self.skipTest("PowerShell nicht verfügbar")
        result = subprocess.run([shell, "-NoProfile", "-File", str(SCRIPT), "-DryRun"],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        for worker in WORKERS:
            self.assertIn("workers/" + worker + "/install.ps1", result.stdout)
        self.assertIn("SIRENS_RT_ENABLED=0", result.stdout)
