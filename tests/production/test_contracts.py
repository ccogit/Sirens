import copy
import tempfile
import unittest
from pathlib import Path

from sirens.production import contracts as c
from production.fixtures import load, generate


class ContractTests(unittest.TestCase):
    def test_fixtures(self):
        plan = load("plan")
        c.validate_brief(load("brief"))
        c.validate_plan(plan)
        c.validate_status(load("status"))
        c.validate_report(load("report"))
        c.validate_mix_report(load("mix_report"))
        self.assertEqual(c.expected_frames(plan), 96000)
        with tempfile.TemporaryDirectory() as tmp:
            assets, stems = generate(tmp, plan)
            c.validate_assets(assets, plan, tmp)
            c.validate_stems(stems, plan, tmp)
            with (Path(tmp) / stems["stems"][0]["file"]).open("ab") as f:
                f.write(b"x")
            with self.assertRaises(c.ContractError):
                c.validate_stems(stems, plan, tmp)

    def test_bad_plan(self):
        for change in (
            lambda p: p.update(schema_version=True),
            lambda p: p.update(bpm=float("nan")),
            lambda p: p["sections"][0].update(start_bar=1),
            lambda p: p["tracks"][0]["events"][0].update(note=128),
            lambda p: p["tracks"][0]["events"][0].update(duration_ticks=4000),
            lambda p: p["tracks"][1]["events"][0].update(asset_id="missing"),
            lambda p: p["tracks"][0]["automation"].append(dict(tick=0, parameter="arbitrary", value=0)),
            lambda p: p.update(command="unsafe"),
        ):
            plan = load("plan")
            change(plan)
            with self.assertRaises(c.ContractError):
                c.validate_plan(plan)

    def test_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in ("../x", "/tmp/x", "C:/x", "x/../y", "x//y", "x\\y"):
                with self.assertRaises(c.ContractError):
                    c.safe_path(tmp, path)
            self.assertEqual(c.safe_path(tmp, "assets/x.wav"), Path(tmp).resolve() / "assets/x.wav")
            root = Path(tmp)
            (root / "link").symlink_to(root / "missing")
            with self.assertRaises(c.ContractError):
                c.safe_path(root, "link/x")

    def test_seeds(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            plan = load("plan")
            _, first = generate(a, plan)
            changed = copy.deepcopy(plan)
            changed["seed"] += 1
            _, second = generate(b, changed)
            self.assertNotEqual(first["stems"][0]["sha256"], second["stems"][0]["sha256"])
            c.validate_stems(first, plan, a)
            c.validate_stems(second, changed, b)


    def test_ableton_schema_and_audio(self):
        value = load("ableton")
        c.validate_ableton(value)
        with tempfile.TemporaryDirectory() as tmp:
            from production.fixtures import wav
            root = Path(tmp)
            track = value["tracks"][0]
            track["sha256"] = wav(root / track["audio_file"], value["frames"], 1)
            wav(root / value["reference_mix"], value["frames"], 2, channels=2)
            c.validate_ableton(value, root)
            track["audio_file"] = "../escape.wav"
            with self.assertRaises(c.ContractError):
                c.validate_ableton(value, root)
        value = load("ableton")
        value["mode"] = "live_editable"
        with self.assertRaises(c.ContractError):
            c.validate_ableton(value)
