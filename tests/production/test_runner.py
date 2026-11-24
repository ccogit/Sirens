import contextlib
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path

from sirens.config import Config
from sirens.production.__main__ import main
from sirens.production.cache import HashCache, cache_key
from sirens.production.contracts import ContractError, sha256_file
from sirens.production.jobs import RunStore
from sirens.production.runner import Runner
from production.fixtures import generate, load, wav
from sirens.production.contracts import expected_frames, tick_to_sample
from sirens.production.runner import LocalServices


class MockBackend:
    """Test-only generated PCM24, no real quality or model claim."""
    def assets(self, brief, plan, root, cancelled):
        self.assets_data, self.stems_data = generate(root, plan)
        return self.assets_data

    def stems(self, plan, assets, root, cancelled):
        return self.stems_data

    def mix(self, plan, stems, root, cancelled):
        sources = []
        for stem in stems["stems"]:
            with wave.open(str(root / stem["file"]), "rb") as stream:
                sources.append(stream.readframes(stems["frames"]))
        samples = bytearray()
        for offset in range(0, len(sources[0]), 3):
            value = sum(int.from_bytes(source[offset:offset+3], "little", signed=True)
                        for source in sources)
            samples.extend(value.to_bytes(3, "little", signed=True) * 2)
        for name in ("mix.wav", "master.wav"):
            with wave.open(str(root / name), "wb") as stream:
                stream.setparams((2, 3, 48000, stems["frames"], "NONE", "not compressed"))
                stream.writeframes(samples)
        return load("mix_report")

    def report(self, brief, plan, assets, stems, mix, root, cancelled):
        return load("report")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cfg = Config(music_root=root / "music", data_dir=root / "data")

    def test_mock_cli_and_revision(self):
        runner = Runner(self.cfg, MockBackend())
        brief, plan = load("brief"), load("plan")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            from production.fixtures import HERE
            code = main(["render", "--brief", str(HERE / "brief.json"), "--plan",
                         str(HERE / "plan.json"), "--mode", "full"],
                        cfg=self.cfg, backend=runner.backend)
        self.assertEqual(code, 0, output.getvalue())
        first = json.loads(output.getvalue())
        self.assertEqual(first["status"], "succeeded")
        old = runner.store.get(first["run_id"])
        old_hashes = {str(p.relative_to(old)): sha256_file(p)
                      for p in old.rglob("*") if p.is_file()}
        plan["seed"] += 1
        second = runner.revise(first["run_id"], plan)
        self.assertEqual(second["status"], "succeeded")
        self.assertEqual(second["parent_run_id"], first["run_id"])
        new = runner.store.get(second["run_id"])
        self.assertNotEqual(sha256_file(old / "master.wav"), sha256_file(new / "master.wav"))
        self.assertEqual(old_hashes, {str(p.relative_to(old)): sha256_file(p)
                                     for p in old.rglob("*") if p.is_file()})
        self.assertFalse(self.cfg.orders_dir.exists())

    def test_crash_cancel_resume(self):
        runner = Runner(self.cfg, MockBackend())

        class Crashing(MockBackend):
            def mix(self, *args):
                raise RuntimeError("private diagnostic")

        runner.backend = Crashing()
        result = runner.render(load("brief"), load("plan"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "RuntimeError")
        runner.backend = MockBackend()
        resumed = runner.resume(result["run_id"])
        self.assertEqual(resumed["status"], "succeeded")

        class Cancelling(MockBackend):
            def assets(self, brief, plan, root, cancelled):
                runner.store.cancel(root.name)
                cancelled()

        runner.backend = Cancelling()
        result = runner.render(load("brief"), load("plan"))
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["stage"], "assets")

    def test_recovery_and_path(self):
        store = RunStore(self.cfg)
        run_id, path = store.create()
        store.status(run_id, "running", "assets", 0.2)
        self.assertEqual(store.recover(run_id)["status"], "failed")
        with self.assertRaises(ContractError):
            store.status(run_id, "running")
        with self.assertRaises(ContractError):
            store.get("../orders")

    def test_hash_cache(self):
        store = RunStore(self.cfg)
        _, src = store.create()
        _, dst = store.create()
        (src / "x").write_bytes(b"synthetic")
        cache = HashCache(store.root)
        key = cache_key("track", {"patch": "kick"}, "mock", "1", 101)
        self.assertNotEqual(key, cache_key("track", {"patch": "kick"}, "mock", "1", 102))
        self.assertFalse(cache.restore(key, dst))
        cache.publish(key, src, ["x"])
        self.assertTrue(cache.restore(key, dst))
        (dst / "x").write_bytes(b"changed")
        self.assertEqual((src / "x").read_bytes(), b"synthetic")
        self.assertEqual((cache.entry(key) / "x").read_bytes(), b"synthetic")
        _, other = store.create()
        (cache.entry(key) / "x").write_bytes(b"corrupt")
        with self.assertRaises(ContractError):
            cache.restore(key, other)


    def test_partial_track_revision(self):
        class Independent(MockBackend):
            name = "mock-independent"
            revision = "1"
            independent_tracks = True

            def __init__(self):
                self.calls = []

            def assets(self, brief, plan, root, cancelled):
                result = []
                for req in plan["asset_requests"]:
                    path = "assets/" + req["id"] + ".wav"
                    frames = round(req["duration_seconds"] * 48000)
                    digest = wav(root / path, frames, req["seed"])
                    result.append(dict(id=req["id"], file=path, kind=req["kind"],
                                       sample_rate=48000, channels=1, frames=frames,
                                       sha256=digest, source=dict(backend=self.name,
                                       revision=self.revision, seed=req["seed"],
                                       license="synthetic-test", use="test-only"),
                                       measured=dict(bpm=None, key=None)))
                return dict(schema_version=1, assets=result)

            def stem(self, plan, assets, track, root, cancelled):
                self.calls.append(track["id"])
                relative = "stems/" + track["id"] + ".wav"
                event = track["events"][0]
                seed = plan["seed"] + event.get("note", 0)
                start = tick_to_sample(event["tick"], plan["bpm"])
                end = tick_to_sample(event["tick"] + event["duration_ticks"], plan["bpm"])
                digest = wav(root / relative, expected_frames(plan), seed,
                             offset=start, duration=end - start)
                return dict(track_id=track["id"], role=track["role"], file=relative,
                            channels=1, sha256=digest, source=dict(backend=self.name,
                            patch=track["patch"], revision=self.revision))

        backend = Independent()
        runner = Runner(self.cfg, backend)
        plan = load("plan")
        first = runner.render(load("brief"), plan)
        self.assertEqual(first["status"], "succeeded", first)
        self.assertEqual(backend.calls, ["kick", "voice"])
        backend.calls.clear()
        plan["tracks"][0]["events"][0]["note"] = 37
        second = runner.revise(first["run_id"], plan)
        self.assertEqual(second["status"], "succeeded", second)
        self.assertEqual(backend.calls, ["kick"])
        old, new = (runner.store.get(r["run_id"]) for r in (first, second))
        self.assertEqual(sha256_file(old / "stems/voice.wav"), sha256_file(new / "stems/voice.wav"))
        self.assertNotEqual(sha256_file(old / "stems/kick.wav"), sha256_file(new / "stems/kick.wav"))

    def test_local_service_routes_no_network(self):
        calls = []
        def transport(port, path):
            calls.append((port, path))
            return {"status": "unknown"}
        services = LocalServices(transport=transport)
        services.status()
        services.guard()
        services.chain("master")
        services.job("test-001")
        self.assertEqual(calls, [(8099, "/api/status"), (8000, "/api/live-delivery/guard"),
                                 (8099, "/api/chains/master"), (8099, "/api/jobs/test-001")])
        with self.assertRaises(ContractError):
            services.job("../x")
        with self.assertRaises(ContractError):
            services.chain("unknown")
