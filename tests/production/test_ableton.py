"""Offline K07 tests; no Live, network, GPU or installed AMM required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from sirens.production.ableton import export_bundle, import_return, probe, wb_source
from sirens.production.contracts import ContractError, expected_frames


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def wav(path, frames, channels=2):
    with wave.open(str(path), "wb") as w:
        w.setparams((channels, 3, 48000, frames, "NONE", "not compressed"))
        w.writeframes(bytes(frames * 3 * channels))
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AbletonExchangeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.runs = self.root / "runs"
        self.run = self.runs / "run1"
        self.run.mkdir(parents=True)
        self.exports = self.root / "exports"
        self.plan = dict(schema_version=1, seed=101, bpm=126, key=None, meter=[4, 4],
                         ppq=960, total_bars=1, tail_seconds=0,
                         sections=[dict(id="intro", start_bar=0, bars=1, intent="test")],
                         tracks=[dict(id="kick", role="drums", backend="instrument",
                                      patch="kick", events=[dict(tick=960, duration_ticks=240,
                                                               note=36, velocity=115)],
                                      automation=[dict(tick=960, parameter="volume", value=.5)])],
                         asset_requests=[], mix=dict(target_lufs=None, ceiling_dbtp=-1))
        self.frames = expected_frames(self.plan)
        self.digest = wav(self.run / "kick.wav", self.frames, 1)
        wav(self.run / "mix.wav", self.frames)
        write_json(self.run / "plan.json", self.plan)
        write_json(self.run / "stems.json", dict(schema_version=1, sample_rate=48000,
                   frames=self.frames, stems=[dict(track_id="kick", role="drums",
                   file="kick.wav", channels=1, sha256=self.digest,
                   source=dict(backend="fixture", patch="kick", revision="1"))]))

    def writer(self, document, destination):
        # Literal SMF fixture: 126 BPM, 4/4, named kick, note-on at 960, off +240.
        self.assertEqual(document["schema"], "wb-midi-source/1")
        self.assertEqual(document["tempo"], 126)
        self.assertEqual(document["time_sig"], [4, 4])
        self.assertEqual(document["markers"], [{"beat": 0, "name": "intro"}])
        self.assertEqual(document["tracks"][0]["id"], "kick")
        self.assertEqual(document["clips"][0]["notes"],
                         [{"pitch": 36, "start": 1.0, "duration": .25, "velocity": 115}])
        conductor = bytes.fromhex("00ff510307441e00ff58040402180800ff2f00")
        notes = bytes.fromhex("00ff03046b69636b8740992473817089240000ff2f00")
        destination.write_bytes(bytes.fromhex("4d546864000000060001000203c0")
                                + b"MTrk" + len(conductor).to_bytes(4, "big") + conductor
                                + b"MTrk" + len(notes).to_bytes(4, "big") + notes)
        return {"tracks": [{"track_id": "kick"}]}

    def export(self):
        return export_bundle(self.run, self.exports, "run1", "exp1", midi_writer=self.writer)

    def test_capabilities_fail_closed(self):
        self.assertFalse(probe()["render"])
        self.assertIsNone(probe()["live_version"])
        observed = probe(dict(schema_version=1, render=True, open_set=True))
        self.assertTrue(observed["observed_render"])
        self.assertFalse(observed["render"])
        with self.assertRaises(ContractError):
            export_bundle(self.run, self.exports, "run1", "exp1")
        self.assertFalse((self.exports / "exp1").exists())

    def test_export_timing_and_paths(self):
        manifest = self.export()
        bundle = self.exports / "exp1"
        self.assertEqual(manifest["frames"], self.frames)
        self.assertEqual(manifest["tracks"][0]["sha256"], self.digest)
        self.assertEqual(manifest["tracks"][0]["playback"], "audio")
        self.assertFalse(manifest["tracks"][0]["warp"])
        self.assertEqual(manifest["mode"], "import_bundle")
        self.assertIsNone(manifest["project_file"])
        self.assertEqual((bundle / "audio/kick.wav").read_bytes(),
                         (self.run / "kick.wav").read_bytes())
        self.assertEqual((bundle / "MIDI/kick.mid").read_bytes()[:14],
                         bytes.fromhex("4d546864000000060001000203c0"))
        self.assertTrue((self.exports / "return/exp1").is_dir())
        with self.assertRaises(ContractError):
            self.export()

    def test_absolute_tick_mapping(self):
        self.plan["tracks"][0]["events"][0].update(tick=1237, duration_ticks=17)
        doc = wb_source(self.plan, self.plan["tracks"][0], "run1")
        note = doc["clips"][0]["notes"][0]
        self.assertEqual(round(note["start"] * 960), 1237)
        self.assertEqual(round((note["start"] + note["duration"]) * 960), 1254)

    def test_frame_and_midi_validation(self):
        wav(self.run / "mix.wav", self.frames - 1)
        with self.assertRaises(ContractError):
            self.export()
        self.assertFalse((self.exports / "exp1").exists())
        wav(self.run / "mix.wav", self.frames)
        def broken(doc, path):
            self.writer(doc, path)
            return {"tracks": [{"track_id": "other"}]}
        with self.assertRaises(ContractError):
            export_bundle(self.run, self.exports, "run1", "exp1", midi_writer=broken)
        self.assertFalse((self.exports / "exp1").exists())

    def test_manual_return_preserves_original(self):
        self.export()
        inbox = self.exports / "return/exp1"
        master = wav(inbox / "master.wav", self.frames + 5)
        original = {p: p.read_bytes() for p in self.run.iterdir()}
        exported = (self.exports / "exp1/ableton.json").read_bytes()
        with self.assertRaises(ContractError):
            import_return(self.exports, "exp1", self.runs)
        result = import_return(self.exports, "exp1", self.runs, confirm=True,
                               revision_id="revision1", stability_seconds=0)
        self.assertEqual(result["parent_run_id"], "run1")
        self.assertEqual(result["source"], "ableton_return")
        self.assertEqual(result["master_sha256"], master)
        self.assertTrue(result["stereo_only"])
        self.assertTrue(result["duration_changed"])
        self.assertFalse(result["mastering_required"])
        self.assertFalse(result["published"])
        self.assertEqual(json.loads((inbox / "return.json").read_text())["master_sha256"], master)
        self.assertEqual(json.loads((self.runs / "revision1/status.json").read_text())["status"], "queued")
        self.assertEqual((self.runs / "revision1/master.wav").read_bytes(),
                         (inbox / "master.wav").read_bytes())
        self.assertEqual(original, {p: p.read_bytes() for p in self.run.iterdir()})
        self.assertEqual(exported, (self.exports / "exp1/ableton.json").read_bytes())
        with self.assertRaises(ContractError):
            import_return(self.exports, "exp1", self.runs, confirm=True,
                          revision_id="revision1", stability_seconds=0)

    def test_reject_mismatch_traversal_and_symlink(self):
        self.export()
        inbox = self.exports / "return/exp1"
        wav(inbox / "master.wav", self.frames)
        manifest = dict(schema_version=1, export_id="wrong", parent_run_id="run1",
                        master_file="master.wav", notes="")
        for changes in ({}, {"export_id": "exp1", "master_file": "../master.wav"},
                        {"export_id": "exp1", "master_sha256": "0" * 64}):
            write_json(inbox / "return.json", {**manifest, **changes})
            with self.assertRaises(ContractError):
                import_return(self.exports, "exp1", self.runs, confirm=True,
                              revision_id="revision1", stability_seconds=0)
            self.assertFalse((self.runs / "revision1").exists())
        (inbox / "master.wav").unlink()
        (inbox / "master.wav").symlink_to(self.run / "mix.wav")
        write_json(inbox / "return.json", {**manifest, "export_id": "exp1"})
        with self.assertRaises(ContractError):
            import_return(self.exports, "exp1", self.runs, confirm=True, stability_seconds=0)

    def test_optional_stems_midi_and_tempo_change(self):
        self.export()
        inbox = self.exports / "return/exp1"
        master = wav(inbox / "master.wav", self.frames)
        stem = wav(inbox / "edited.wav", self.frames, 1)
        midi = self.exports / "exp1/MIDI/kick.mid"
        (inbox / "edited.mid").write_bytes(midi.read_bytes())
        data = dict(schema_version=1, export_id="exp1", parent_run_id="run1",
                    master_file="master.wav", master_sha256=master, notes="edited",
                    stems=[dict(file="edited.wav", sha256=stem, track_id="kick")],
                    midi=["edited.mid"], bpm=128)
        write_json(inbox / "return.json", data)
        result = import_return(self.exports, "exp1", self.runs, confirm=True,
                               revision_id="revision2", stability_seconds=0)
        self.assertFalse(result["stereo_only"])
        self.assertEqual(result["bpm"], 128)
        self.assertEqual(result["original_bpm"], 126)
        self.assertEqual(len(result["files"]), 3)
        self.assertEqual(json.loads((inbox / "return.json").read_text()), data)

    def test_unstable_and_atomic_failure(self):
        self.export()
        inbox = self.exports / "return/exp1"
        wav(inbox / "master.wav", self.frames)
        with patch("sirens.production.ableton.time.sleep",
                   side_effect=lambda _: wav(inbox / "master.wav", self.frames + 1)):
            with self.assertRaises(ContractError):
                import_return(self.exports, "exp1", self.runs, confirm=True,
                              revision_id="revision1", stability_seconds=0)
        self.assertFalse((self.runs / "revision1").exists())
        with patch("sirens.production.ableton._copy", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                import_return(self.exports, "exp1", self.runs, confirm=True,
                              revision_id="revision1", stability_seconds=0)
        self.assertFalse((self.runs / "revision1").exists())
        self.assertFalse((self.runs / ".revision1.lock").exists())


if __name__ == "__main__":
    unittest.main()
