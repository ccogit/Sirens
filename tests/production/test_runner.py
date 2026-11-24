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
from production.fixtures import generate, load


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
