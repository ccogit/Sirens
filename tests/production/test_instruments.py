import copy
import tempfile
import unittest
from pathlib import Path

from sirens.production.instruments import (
    digest, expected_frames, read_pcm, render_section, render_stems,
    tick_to_sample, write_pcm,
)


def fixture():
    return {"schema_version": 1, "seed": 101, "bpm": 126, "key": None,
            "meter": [4, 4], "ppq": 960, "total_bars": 2, "tail_seconds": 0,
            "sections": [{"id": "a", "start_bar": 0, "bars": 1, "intent": "a"},
                         {"id": "b", "start_bar": 1, "bars": 1, "intent": "b"}],
            "tracks": [{"id": "kick", "role": "drums", "backend": "instrument",
                        "patch": "tight_kick", "events": [
                            {"tick": i*960, "duration_ticks": 120, "note": 36, "velocity": 100}
                            for i in range(8)], "automation": []}],
            "asset_requests": [], "mix": {"target_lufs": None, "ceiling_dbtp": -1}}


class MockBackend:
    name = "test-only-mock"
    revision = "1"

    def __init__(self):
        self.calls = 0

    def render(self, request, output):
        self.calls += 1
        data = bytearray(request["frames"] * 6)
        for event in request["track"]["events"]:
            start = tick_to_sample(event["tick"], request["bpm"])
            data[start*6:start*6+6] = b"\x00\x00\x20" * 2
        write_pcm(output, 2, data)


def patch():
    return {"instrument": {"type": "vst3", "preset": "fixture"},
            "revision": "1", "license": "synthetic-test", "use": "test-only"}


class InstrumentTests(unittest.TestCase):
    def test_alignment_cache_section_and_sidechain(self):
        plan = fixture()
        empty = {"schema_version": 1, "assets": []}
        backend = MockBackend()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = [root / name for name in ("r1", "r2", "r3")]
            for run in runs:
                run.mkdir()
            kwargs = dict(patches={"tight_kick": patch()}, backend=backend, cache_dir=root/"cache")
            a = render_stems(plan, empty, runs[0], **kwargs)
            b = render_stems(plan, empty, runs[1], **kwargs)
            self.assertEqual(backend.calls, 1)
            self.assertEqual(a["stems"][0]["sha256"], b["stems"][0]["sha256"])
            self.assertTrue(b["stems"][0]["source"]["cache_hit"])
            self.assertEqual(a["frames"], expected_frames(plan))
            channels, audio = read_pcm(runs[0]/"stems/kick.wav")
            self.assertEqual(channels, 2)
            onsets = [i//6 for i in range(0, len(audio), 6) if audio[i:i+6] != b"\0"*6]
            self.assertEqual(onsets, [round(i*48000*60/126) for i in range(8)])
            measured = 7*60*48000/(onsets[-1]-onsets[0])
            self.assertAlmostEqual(measured, 126, places=3)
            _, trigger = read_pcm(runs[0]/a["sidechain_file"])
            self.assertEqual(trigger[onsets[1]*3:onsets[1]*3+3], b"\0\0\x40")
            s = render_section(runs[0]/"stems/kick.wav", plan, "b", root/"section.wav")
            self.assertEqual(s["start_sample"], onsets[4])
            self.assertEqual(s["frames"], a["frames"]-onsets[4])
            changed = copy.deepcopy(plan)
            changed["seed"] += 1
            render_stems(changed, empty, runs[2], **kwargs)
            self.assertEqual(backend.calls, 2)

    def test_asset_exact_placement_and_mono_sub(self):
        plan = fixture()
        plan["tracks"][0]["patch"] = "mono_sub"
        plan["tracks"].append({"id": "voice", "role": "spoken", "backend": "asset",
                               "patch": "spoken_calm", "events": [
                                   {"tick": 960, "duration_ticks": 240, "asset_id": "cue"}],
                               "automation": []})
        plan["asset_requests"] = [{"id": "cue", "kind": "speech", "text": "test",
                                   "seed": 1, "duration_seconds": 0.01}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = b"\x01\x02\x03" * 480
            write_pcm(root/"cue.wav", 1, sample)
            assets = {"schema_version": 1, "assets": [
                {"id": "cue", "file": "cue.wav", "kind": "speech", "sample_rate": 48000,
                 "channels": 1, "frames": 480, "sha256": digest(root/"cue.wav"),
                 "source": {"backend": "mock", "revision": "1", "seed": 1,
                            "license": "synthetic-test", "use": "test-only"},
                 "measured": {"bpm": None, "key": None}}]}
            manifest = render_stems(plan, assets, root, patches={"mono_sub": patch()}, backend=MockBackend())
            self.assertEqual(manifest["stems"][0]["channels"], 1)
            _, audio = read_pcm(root/"stems/voice.wav")
            at = tick_to_sample(960, 126)*3
            self.assertEqual(audio[:at], b"\0"*at)
            self.assertEqual(audio[at:at+len(sample)], sample)
            self.assertFalse(any(audio[at+len(sample):]))

    def test_no_implicit_mock_or_patch_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = {"schema_version": 1, "assets": []}
            with self.assertRaisesRegex(ValueError, "No verified"):
                render_stems(fixture(), empty, tmp, patches={})
            with self.assertRaisesRegex(ValueError, "Missing local patch"):
                render_stems(fixture(), empty, tmp, patches={}, backend=MockBackend())
            self.assertFalse((Path(tmp)/"stems.json").exists())


if __name__ == "__main__":
    unittest.main()
