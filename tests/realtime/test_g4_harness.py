"""CPU-/Mock-Regressionsprüfungen für den G4-Mess-Harness (WP32)."""
import contextlib
import http.client
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from benchmarks import system_suite as suite
from workers.stable_audio import adapter


@contextlib.contextmanager
def server(module, *args):
    with subprocess.Popen([sys.executable, "-m", module, *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8")) as proc:
        try:
            lines = queue.Queue()
            threading.Thread(target=lambda: lines.put(proc.stdout.readline()), daemon=True).start()
            line = lines.get(timeout=15)
            if not line.startswith("http://127.0.0.1:"):
                raise AssertionError("Messserver nicht gestartet: " + line)
            yield int(line.split(":")[2].split("/")[0])
        finally:
            proc.kill()
            proc.wait(timeout=10)


def request(port, path, host=None, method="GET"):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path, headers={"Host": host or f"127.0.0.1:{port}"})
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


class G4Harness(unittest.TestCase):
    def test_module_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            for module, prefix, args in (
                ("benchmarks.audio_core.serve", "/web/js/realtime/", ["--port", "0"]),
                ("benchmarks.recorder.browser", "/js/", ["--scratch", tmp, "--out",
                                                        str(Path(tmp) / "result.json"), "--seconds", "1"]),
            ):
                with self.subTest(module=module), server(module, *args) as port:
                    for name in ("effects/rack.js", "effects/spectral.js", "audio_core.js"):
                        self.assertEqual(request(port, prefix + name), 200)
                    for name in ("../audio_core.js", "effects/../audio_core.js", "%2e%2e/audio_core.js",
                                 "/effects/rack.js", "effects\\rack.js", "effects/not-a-module.txt"):
                        self.assertEqual(request(port, prefix + name), 404)
                    self.assertEqual(request(port, "http://127.0.0.1:" + str(port) + prefix + "effects/rack.js"), 404)
                    self.assertEqual(request(port, prefix + "effects/rack.js", host="example.invalid"), 404)

    def test_snapshot_retry(self):
        row = {"ProcessId": 3, "ParentProcessId": 1, "CommandLine": None}
        with patch.object(suite, "os", SimpleNamespace(name="nt")), \
             patch.object(suite.time, "sleep"), \
             patch.object(suite.subprocess, "check_output", side_effect=[
                 "kaputt", subprocess.TimeoutExpired("powershell", 60), json.dumps(row)]) as call:
            self.assertEqual(suite.process_snapshot(), [row])
            self.assertEqual(call.call_count, 3)
        with patch.object(suite, "os", SimpleNamespace(name="nt")), \
             patch.object(suite.time, "sleep"), \
             patch.object(suite.subprocess, "check_output", return_value="kaputt") as call:
            with self.assertRaisesRegex(RuntimeError, "5 Versuchen"):
                suite.process_snapshot()
            self.assertEqual(call.call_count, 5)

    def test_snapshot_failure_isolated(self):
        rows = [dict(id=cid, modus="offline", freigegeben=True, g1=None)
                for cid in ("first", "second")]
        first, second = MagicMock(), MagicMock()
        first.__enter__.return_value = first
        first.poll.return_value = None
        second.__enter__.return_value = second
        second.poll.return_value = 0
        second.returncode = 0
        snapshot = MagicMock(side_effect=[[], RuntimeError("Prozessinventar nach 5 Versuchen"), []])
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(suite, "inventory", return_value=rows), \
             patch.object(suite.subprocess, "Popen", side_effect=[first, second]), \
             patch.object(suite, "read", return_value={"modus": "offline", "gate": "nicht_gemessen"}), \
             patch.object(suite, "report") as report:
            self.assertEqual(suite.run(Path(tmp) / "out", None,
                                      {cid: {"argv": ["test"]} for cid in ("first", "second")},
                                      snapshot=snapshot), 1)
            first.kill.assert_called_once()
            self.assertEqual(rows[0]["status"], "fehler")
            self.assertEqual(rows[1]["status"], "messdatei_vorhanden")
            self.assertEqual(len(report.call_args.args[2]), 1)

    def test_separation_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            steps = [["python", "-m", "benchmarks.separation.product_job", "song.wav", "output"]]
            for rate, channels in ((48000, 2), (44100, 1), (44100, 2)):
                with wave.open(str(root / "song.wav"), "wb") as stream:
                    stream.setparams((channels, 2, rate, 0, "NONE", ""))
                    stream.writeframes(bytes(channels * 2 * 16))
                if (rate, channels) == (44100, 2):
                    suite.preflight("separation", steps, root)
                else:
                    with self.assertRaisesRegex(ValueError, f"Testdaten: {rate} Hz, {channels} Kanäle"):
                        suite.preflight("separation", steps, root)

    def test_cache_search_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "workers/stable_audio/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"python_dirs": [".venv-stable-audio",
                                                            ".venv-spike-stable-audio-3"]}), encoding="utf-8")
            cache = root / ".venv-spike-stable-audio-3/weights"
            (cache / adapter.MODEL / "snapshots" / adapter.REVISION).mkdir(parents=True)
            with patch.dict(os.environ, {"SIRENS_RT_STABLE_AUDIO_CACHE": ""}):
                self.assertEqual(adapter.find_cache(root), cache)
            explicit = root / "explicit"
            with patch.dict(os.environ, {"SIRENS_RT_STABLE_AUDIO_CACHE": str(explicit)}):
                self.assertEqual(adapter.find_cache(root), explicit)
