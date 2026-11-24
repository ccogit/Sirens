"""VoiceDesign tests without Torch, Qwen, audio libraries, GPU or network."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import wave
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from sirens.production.assets import AssetError, Worker, render_assets

REVISION = "a" * 40


def request(name, seed):
    return dict(id=name, kind="speech", text="Exact words.\nA pause.",
                prompt="Quiet close speech", seed=seed, duration_seconds=1)


def plan(*requests):
    return dict(schema_version=1, seed=101, bpm=126, key="D minor",
                meter=[4, 4], ppq=960, total_bars=1, tail_seconds=0,
                sections=[dict(id="intro", start_bar=0, bars=1, intent="intro")],
                tracks=[], asset_requests=list(requests),
                mix=dict(target_lufs=None, ceiling_dbtp=-1))


def fixture_wav(path):
    with wave.open(str(path), "wb") as f:
        f.setparams((1, 3, 48000, 0, "NONE", "not compressed"))
        f.writeframes((100000).to_bytes(3, "little", signed=True) * 4800)


class VoiceDesignTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.snapshot = self.root / REVISION
        self.snapshot.mkdir()
        (self.snapshot / "config.json").write_text(
            json.dumps({"tts_model_type": "voice_design"}), encoding="utf-8")
        self.source = dict(backend="qwen3-tts-voicedesign", revision=REVISION,
                           license="Apache-2.0", license_confirmed=True,
                           use="production")

    def test_worker_voice_design_api_and_one_load(self):
        path = Path(__file__).resolve().parents[2] / "workers" / "production_assets" / "worker.py"
        spec = importlib.util.spec_from_file_location("test_voicedesign_worker", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ):
            spec.loader.exec_module(module)
        torch = Mock()
        qwen = Mock()
        model = qwen.Qwen3TTSModel.from_pretrained.return_value
        model.generate_voice_design.return_value = ([[.1, .2]], 24000)
        jobs = [dict(request=request("a", 101), output=str(self.root / "a.wav")),
                dict(request=request("b", 102), output=str(self.root / "b.wav"))]
        with patch.dict(sys.modules, {"torch": torch, "qwen_tts": qwen}), patch.object(module, "write_wav") as write:
            module.speech_batch(jobs, self.snapshot)
        qwen.Qwen3TTSModel.from_pretrained.assert_called_once_with(
            str(self.snapshot.resolve()), device_map="cuda:0", dtype=torch.bfloat16,
            attn_implementation="sdpa", local_files_only=True)
        self.assertEqual(model.generate_voice_design.call_count, 2)
        model.generate_voice_design.assert_called_with(
            text=jobs[1]["request"]["text"], instruct=jobs[1]["request"]["prompt"],
            language="English")
        self.assertEqual([c.args[0] for c in torch.manual_seed.call_args_list], [101, 102])
        self.assertEqual([c.args[0] for c in torch.cuda.manual_seed_all.call_args_list], [101, 102])
        self.assertEqual(write.call_count, 2)
        write.assert_called_with(self.root / "b.wav", [.1, .2], 24000)

    def test_run_batches_only_uncached_speech_and_records_provenance(self):
        lease = Mock(side_effect=nullcontext)
        worker = Worker(sys.executable, lease=lease, tts_model=self.snapshot)
        def invoke(payload, dest):
            self.assertEqual(payload["kind"], "speech_batch")
            for job in payload["jobs"]:
                fixture_wav(Path(job["output"]))
        worker._invoke = Mock(side_effect=invoke)
        opts = dict(resolve=lambda req: None, worker=worker,
                    generated_sources={"speech": self.source},
                    gap_ids=["a", "b"], cache_dir=self.root / "cache")
        p = plan(request("a", 101), request("b", 102))
        for name in ("one", "two"):
            run = self.root / name
            run.mkdir()
            result = render_assets(p, run, **opts)
            self.assertEqual([e["id"] for e in result["assets"]], ["a", "b"])
            for index, entry in enumerate(result["assets"]):
                self.assertNotIn("error", entry)
                self.assertEqual(entry["source"]["seed"], 101 + index)
                self.assertEqual(entry["source"]["revision"], REVISION)
                self.assertEqual(entry["source"]["license"], "Apache-2.0")
                self.assertEqual(entry["source"]["model"], "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
                self.assertEqual(entry["measured"]["duration_seconds"], .1)
                self.assertEqual(entry["cache_hit"], name == "two")
            self.assertEqual(json.loads((run / "assets.json").read_text(encoding="utf-8")), result)
        worker._invoke.assert_called_once()
        lease.assert_called_once()
        self.assertEqual(len(worker._invoke.call_args.args[0]["jobs"]), 2)

    def test_model_configuration_and_provenance_errors(self):
        req = request("a", 101)
        with patch("sirens.production.integration.settings", return_value={"tts_model": str(self.snapshot)}):
            worker = Worker(sys.executable)
            worker.verify_source(req, dict(self.source))
        with patch("sirens.production.integration.settings", return_value={}):
            with self.assertRaisesRegex(AssetError, "tts_model"):
                Worker(sys.executable).verify_source(req, dict(self.source))
        worker = Worker(sys.executable, tts_model=self.snapshot)
        with self.assertRaisesRegex(AssetError, "provenance"):
            worker.verify_source(req, dict(self.source, revision="wrong"))
        with self.assertRaisesRegex(AssetError, "prompt"):
            worker.verify_source(dict(req, prompt=" "), dict(self.source))
        (self.snapshot / "config.json").write_text(
            json.dumps({"tts_model_type": "custom_voice"}), encoding="utf-8")
        with self.assertRaisesRegex(AssetError, "VoiceDesign"):
            worker.verify_source(req, dict(self.source))
