"""Offline tests of the K08 composition root."""
import tempfile
import time
import threading
import wave
from copy import deepcopy
import unittest
from pathlib import Path
from unittest.mock import patch

from sirens.config import Config
from sirens.production import integration
from sirens.production.contracts import ContractError, expected_frames, sha256_file
from production.fixtures import load
from production.test_runner import MockBackend
from sirens.production.jobs import RunStore


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cfg = Config(music_root=root / "music", data_dir=root / "data")

    def test_dispatch_without_whole_stage_cache(self):
        backend = integration.RealBackend(self.cfg, {})
        self.assertFalse(hasattr(backend, "revision"))
        with patch("sirens.production.mixing.mix", return_value={"ok": True}) as mix:
            self.assertEqual(backend.mix({}, {}, self.cfg.data_dir, lambda: None), {"ok": True})
            mix.assert_called_once()

    def test_unfinished_or_invalid_run_cannot_export(self):
        store = RunStore(self.cfg)
        run_id, _ = store.create()
        for value in (run_id, "../outside"):
            with self.assertRaises(ContractError):
                integration.export_master(store, value, "song", {})

    def test_missing_instrument_configuration(self):
        backend = integration.RealBackend(self.cfg, {})
        with self.assertRaises(ContractError):
            backend.stems({"tracks": [{"backend": "instrument"}]}, {}, self.cfg.data_dir, lambda: None)


    def test_service_create_preview_full_revision_and_exports(self):
        class FastBackend(MockBackend):
            # Test-only sparse PCM24, no model or musical quality claim.
            @staticmethod
            def pcm(path, frames, seed, channels=1):
                path.parent.mkdir(exist_ok=True, parents=True)
                with wave.open(str(path), "wb") as stream:
                    stream.setparams((channels, 3, 48000, frames, "NONE", ""))
                    sample = seed.to_bytes(3, "little", signed=True) * channels
                    stream.writeframes(sample + b"\0" * ((frames - 1) * 3 * channels))
                return sha256_file(path)

            def assets(self, brief, plan, root, cancelled):
                request = plan["asset_requests"][0]
                frames = round(request["duration_seconds"] * 48000)
                file = "assets/cue1.wav"
                digest = self.pcm(root / file, frames, plan["seed"])
                return {"schema_version": 1, "assets": [
                    dict(id="cue1", kind="speech", file=file, sample_rate=48000,
                         channels=1, frames=frames, sha256=digest,
                         source=dict(backend="mock", revision="1", seed=request["seed"],
                                     license="synthetic-test", use="test-only"),
                         measured=dict(bpm=None, key=None))]}

            def stems(self, plan, assets, root, cancelled):
                frames = expected_frames(plan)
                file = "stems/voice.wav"
                digest = self.pcm(root / file, frames, plan["seed"])
                return {"schema_version": 1, "sample_rate": 48000, "frames": frames,
                        "stems": [dict(track_id="voice", role="spoken", file=file, channels=1,
                                       sha256=digest, source=dict(backend="mock",
                                       patch="spoken_calm", revision="1"))]}

            def mix(self, plan, stems, root, cancelled):
                for name in ("mix.wav", "master.wav"):
                    self.pcm(root / name, stems["frames"], plan["seed"], 2)
                return load("mix_report")

        brief, plan = load("brief"), load("plan")
        plan["tracks"] = [t for t in plan["tracks"] if t["backend"] == "asset"]
        plan["total_bars"] = plan["sections"][0]["bars"] = 16
        brief["target_seconds"] = 32
        preview = deepcopy(plan)
        preview["total_bars"] = preview["sections"][0]["bars"] = 15
        preview_brief = dict(brief, target_seconds=30)
        service = integration.ProductionService(self.cfg, backend_factory=lambda *_: FastBackend(),
                                                options_factory=lambda: {})
        first = self.wait(service, service.start(dict(brief=brief, plan=plan, mode="full",
                                 preview_brief=preview_brief, preview_plan=preview))["run_id"])
        self.assertEqual(first["status"], "succeeded")
        self.assertTrue(first["validated"])
        root = service.store.get(first["run_id"])
        self.assertTrue((root / "preview.json").is_file())
        self.assertEqual(service.audio(first["run_id"]), root / "master.wav")
        before = {p.relative_to(root): sha256_file(p) for p in root.rglob("*") if p.is_file()}
        revised = deepcopy(plan)
        revised["seed"] += 1
        second = self.wait(service, service.revise({"run": first["run_id"], "plan": revised})["run_id"])
        self.assertEqual(second["status"], "succeeded")
        self.assertNotEqual(sha256_file(service.audio(first["run_id"])),
                            sha256_file(service.audio(second["run_id"])))
        self.assertEqual(before, {p.relative_to(root): sha256_file(p)
                                 for p in root.rglob("*") if p.is_file()})
        exported = service.export(first["run_id"])
        self.assertEqual(exported["mode"], "import_bundle")
        self.assertTrue(exported["validated"])
        export_id = exported["export_id"]
        self.assertFalse(service.check_return(export_id)["validated"])
        inbox = integration.ableton_root(service.store) / "return" / export_id
        FastBackend.pcm(inbox / "master.wav", 64, 101, 2)
        self.assertTrue(service.check_return(export_id)["validated"])
        returned = service.take_return(export_id, True)
        self.assertEqual(returned["status"], "succeeded")
        self.assertEqual(returned["parent_run_id"], first["run_id"])
        self.assertEqual(before, {p.relative_to(root): sha256_file(p)
                                 for p in root.rglob("*") if p.is_file()})
        approved = self.cfg.data_dir / "exports"
        approved.mkdir()
        opts = {"export_root": str(approved)}
        a = integration.export_master(service.store, first["run_id"], "song", opts)
        b = integration.export_master(service.store, first["run_id"], "song", opts)
        self.assertNotEqual(a["export_id"], b["export_id"])
        with self.assertRaises(ContractError):
            integration.export_master(service.store, first["run_id"], "../escape", opts)

    def wait(self, service, run_id):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            result = service.status(run_id)
            if result["status"] not in ("queued", "running"):
                return result
            time.sleep(.02)
        self.fail("production job did not finish")

    def test_service_cancel_and_crash(self):
        entered, release = threading.Event(), threading.Event()
        class Waiting(MockBackend):
            def assets(self, brief, plan, root, cancelled):
                entered.set()
                release.wait(5)
                cancelled()
                raise RuntimeError("should cancel first")
        class Crashing(MockBackend):
            def assets(self, *args):
                raise RuntimeError("synthetic crash")
        brief, plan = load("brief"), load("plan")
        plan["total_bars"] = plan["sections"][0]["bars"] = 15
        brief["target_seconds"] = 30
        req = dict(brief=brief, plan=plan, mode="preview")
        service = integration.ProductionService(self.cfg, backend_factory=lambda *_: Waiting(),
                                                options_factory=lambda: {})
        job = service.start(req)["run_id"]
        try:
            self.assertTrue(entered.wait(5))
            service.cancel(job)
        finally:
            release.set()
        self.assertEqual(self.wait(service, job)["status"], "cancelled")
        service.backend_factory = lambda *_: Crashing()
        job = service.start(req)["run_id"]
        self.assertEqual(self.wait(service, job)["status"], "failed")
