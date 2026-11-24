"""Rollout-Vertrag, ohne GPU, Netz oder Modellgewichte."""
import os
import tempfile
import shutil
import subprocess
import unittest
from benchmarks.rollout import result
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "rt-install.ps1"
WORKERS = ("demon", "rave", "after", "magenta", "sam_audio", "separation", "stable_audio")


class RolloutTest(unittest.TestCase):
    def test_opt_in_and_scope(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(source.index("if ($DryRun) { return }"), source.index("& py -3.11"))
        self.assertLess(source.index("if (!$ModelleLaden) { return }"), source.index("& $installer -ModelleLaden -Umgebung"))
        self.assertIn("Remove-Item -LiteralPath $target -Recurse -Force", source)
        self.assertIn(".sirens-rt-rollout", source)
        self.assertIn("ReparsePoint", source)
        self.assertIn("$MinFreeVramMiB", source)
        self.assertIn("$MinFreeDiskBytes", source)
        self.assertIn("UnvollstaendigeLocksAkzeptieren", source)
        self.assertNotIn("Invoke-WebRequest", source)
        for worker in WORKERS:
            self.assertTrue((ROOT / "workers" / worker / "install.ps1").is_file())

    def test_installation_report_not_gate(self):
        machine = dict.fromkeys(('os', 'python', 'node', 'ffmpeg', 'gpus', 'wsl', 'disk', 'git', 'notes'))
        data = result('rave', 1, machine, False)
        self.assertEqual(data['gate'], 'nicht_gemessen')
        self.assertIn('Installer-Exitcode: 1', data['notizen'])
        self.assertTrue(all(v is None for v in data['messwerte']['warm'].values()))

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

    def test_removal_owned_only_if_powershell_available(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            self.skipTest("PowerShell nicht verfügbar")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            script = scripts / SCRIPT.name
            shutil.copyfile(SCRIPT, script)
            local = root / "local"
            local.mkdir()
            env = dict(os.environ, OS="Windows_NT", LOCALAPPDATA=str(local))
            owned = root / ".venv-spike-rave"
            owned.mkdir()
            foreign = root / ".venv-spike-after"
            foreign.mkdir()
            (foreign / "keep.txt").write_text("Bestand", encoding="utf-8")
            marker = owned / ".sirens-rt-rollout"
            marker.write_text("rave", encoding="utf-8")
            def run(*args):
                return subprocess.run([shell, "-NoProfile", "-File", str(script), *args],
                                      capture_output=True, text=True, timeout=30, env=env)
            dry = run("-Worker", "rave", "-Entfernen", "-DryRun")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertTrue(marker.is_file())
            denied = run("-Worker", "after", "-Entfernen")
            self.assertNotEqual(denied.returncode, 0)
            self.assertTrue((foreign / "keep.txt").is_file())
            removed = run("-Worker", "rave", "-Entfernen")
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(owned.exists())
            self.assertTrue((foreign / "keep.txt").is_file())
