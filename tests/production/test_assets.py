"""K04 offline fixtures; no model, service, GPU, or real samples."""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock

from sirens.production.assets import (
    AMMSamples, AssetError, Candidate, SecondRoom, Worker, approved_source,
    inspect_wav, local_candidate, render_assets, selected_delivery,
)
from sirens.production.contracts import ContractError, validate_assets


def wav(path, frames=4800, value=120000, last=None):
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 3, 48000, 0, "NONE", "not compressed"))
        out.writeframes(value.to_bytes(3, "little", signed=True) * (frames - 1)
                        + (value if last is None else last).to_bytes(3, "little", signed=True))
    return path


def source(**overrides):
    return dict(dict(backend="fixture", revision="1", license="synthetic-test",
                     use="test-only", license_confirmed=True, commercial_ok=False),
                **overrides)


def request(identifier="buoy", kind="foley", **extra):
    return dict(dict(id=identifier, kind=kind, seed=101,
                     duration_seconds=.1, prompt="distant bell buoy"), **extra)


def plan(*requests):
    return dict(schema_version=1, seed=101, bpm=126, key="D minor",
                meter=[4, 4], ppq=960, total_bars=1, tail_seconds=0,
                sections=[dict(id="intro", start_bar=0, bars=1, intent="intro")],
                tracks=[], asset_requests=list(requests),
                mix=dict(target_lufs=None, ceiling_dbtp=-1))


class FixtureWorker:
    def __init__(self):
        self.calls = []

    def generate(self, req, path):
        self.calls.append(dict(req))
        wav(path)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_dir(self, name):
        root = self.root / name
        root.mkdir()
        return root

    def test_wav_hash_duration_seam_and_clipping(self):
        path = wav(self.root / "asset.wav")
        meta = inspect_wav(path, duration_seconds=.1, loop=True)
        self.assertEqual(meta["frames"], 4800)
        self.assertEqual(meta["sample_rate"], 48000)
        self.assertEqual(len(meta["sha256"]), 64)
        self.assertIsNone(meta["measured"]["bpm"])
        self.assertEqual(meta["measured"]["seam_delta"], 0)
        for value, last in ((0, 0), (8388607, None), (120000, -120000)):
            wav(path, value=value, last=last)
            with self.assertRaises(AssetError):
                inspect_wav(path, duration_seconds=.1, loop=True)
        wav(path, frames=4801)
        with self.assertRaises(AssetError):
            inspect_wav(path, duration_seconds=.09, speech=True)

    def test_license_and_safe_path(self):
        with self.assertRaises(AssetError):
            approved_source(source())
        with self.assertRaises(AssetError):
            approved_source(source(license="unknown"), allow_test=True)
        with self.assertRaises(AssetError):
            approved_source(source(use="commercial"), commercial=True)
        self.assertEqual(approved_source(source(), allow_test=True)["license"], "synthetic-test")
        with self.assertRaises(ContractError):
            local_candidate(self.root, "../escape.wav", source())

    def test_reuse_first_exact_hash_and_no_overwrite(self):
        req = request()
        p = plan(req)
        candidate = Candidate(wav(self.root / "original.wav"), source(), {})
        worker = FixtureWorker()
        root = self.run_dir("run")
        result = render_assets(p, root, resolve=lambda req: candidate,
                               worker=worker, gap_ids=["buoy"], allow_test=True)
        item = result["assets"][0]
        self.assertEqual(item["sha256"], inspect_wav(candidate.path)["sha256"])
        self.assertEqual(item["file"], "assets/buoy.wav")
        self.assertEqual(worker.calls, [])
        self.assertEqual(json.loads((root / "assets.json").read_text()), result)
        self.assertTrue((root / "asset_provenance.json").is_file())
        validate_assets(result, plan=p, root=root)
        with self.assertRaises(AssetError):
            render_assets(p, root, resolve=lambda req: candidate, allow_test=True)
        wav(root / item["file"], value=200000)
        with self.assertRaises(ContractError):
            validate_assets(result, plan=p, root=root)

    def test_gap_cache_and_unchanged_spoken_text(self):
        cue = request("voice", "speech", text="Clear head.\nCracked-open heart.")
        p = plan(request(), cue)
        worker = FixtureWorker()
        opts = dict(resolve=lambda req: None, worker=worker,
                    generated_sources={"speech": source(), "sound": source()},
                    gap_ids=["buoy", "voice"], allow_test=True, cache_dir=self.root / "cache")
        result = render_assets(p, self.run_dir("one"), **opts)
        self.assertEqual([item.get("error") for item in result["assets"]], [None, None])
        self.assertEqual(worker.calls[1]["text"], cue["text"])
        self.assertEqual(result["assets"][1]["source"]["text"], cue["text"])
        cached = render_assets(p, self.run_dir("two"), **opts)
        self.assertEqual(len(worker.calls), 2)
        self.assertTrue(all(item["cache_hit"] for item in cached["assets"]))
        self.assertEqual([a["sha256"] for a in result["assets"]],
                         [a["sha256"] for a in cached["assets"]])
        # A corrupted cache entry is not returned as successful audio.
        for file in (self.root / "cache").glob("*.wav"):
            file.write_bytes(b"corrupt")
        repaired = render_assets(p, self.run_dir("three"), **opts)
        self.assertEqual(len(worker.calls), 4)
        self.assertFalse(any(a["cache_hit"] for a in repaired["assets"]))

    def test_error_coverage_gap_cancel_and_missing_lease(self):
        p = plan(request(), request("sample", "sample"))
        result = render_assets(p, self.run_dir("blocked"), resolve=lambda req: None)
        self.assertEqual(len(result["assets"]), 2)
        self.assertTrue(all("error" in x for x in result["assets"]))
        cancelled = render_assets(p, self.run_dir("cancel"), resolve=Mock(side_effect=AssertionError),
                                  cancelled=lambda: True)
        self.assertTrue(all("cancelled" in x["error"] for x in cancelled["assets"]))
        with self.assertRaisesRegex(AssetError, "lease"):
            Worker(sys.executable).generate(request(), self.root / "no.wav")

    def test_loop_requires_measured_tempo_and_tonal_key(self):
        p = plan(request("loop", "loop", tonal=True))
        path = wav(self.root / "loop.wav")
        result = render_assets(p, self.run_dir("unmeasured"),
                               resolve=lambda req: Candidate(path, source(), {}), allow_test=True)
        self.assertIn("BPM", result["assets"][0]["error"])
        result = render_assets(p, self.run_dir("verified"),
                               resolve=lambda req: Candidate(path, source(), {"bpm": 126, "key": "D minor"}),
                               allow_test=True)
        self.assertEqual(result["assets"][0]["measured"]["key"], "D minor")

    def test_secondroom_existing_paths_and_guard(self):
        transport = Mock()
        sr = SecondRoom(transport)
        transport.request.return_value = {"safe_to_generate": False}
        with self.assertRaises(AssetError):
            sr.generate("project", kind="texture", prompt="sea", op_id="op", seconds=4, seed=101)
        transport.request.assert_called_once_with("GET", "/api/status")
        transport.request.reset_mock()
        transport.request.side_effect = [{"safe_to_generate": True}, {"job_id": "job"}]
        sr.generate("project", kind="texture", prompt="sea", op_id="op", seconds=4, seed=101)
        self.assertEqual(transport.request.call_args.args[2]["seeds"], [101])
        transport.request.side_effect = None
        path = wav(self.root / "delivery.wav")
        transport.request.side_effect = [[dict(id="delivery", fits=True, path_exists=True,
                                               host_path=str(path), license="CC0",
                                               commercial_ok=True, job_id="job", bpm=126)],
                                         {"status": "succeeded"}]
        self.assertEqual(selected_delivery(sr, "project", "delivery", self.root,
                                           commercial=True).path, path)

    def test_amm_selected_sample_and_licence(self):
        transport = Mock()
        amm = AMMSamples(transport)
        data = wav(self.root / "source.wav").read_bytes()
        row = dict(id="sample", status="active", quality_tier="A",
                   license=dict(id="CC0", commercial_ok=True), bpm=126)
        transport.request.side_effect = [row, data]
        candidate = amm.selected("sample", self.root, commercial=True)
        self.assertEqual(candidate.path.read_bytes(), data)
        self.assertEqual(candidate.source["sample_id"], "sample")
        transport.request.side_effect = [{**row, "license": {"id": "unknown"}}]
        with self.assertRaises(AssetError):
            amm.selected("sample", self.root)
        transport.request.side_effect = None
        transport.request.return_value = {"results": []}
        amm.search("bell buoy", commercial=True, pack="Signature")
        self.assertIn("commercial_safe=true", transport.request.call_args.args[1])
        self.assertIn("pack=Signature", transport.request.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
