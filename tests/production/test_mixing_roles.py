"""Role and routing regressions; graph inspection needs no ffmpeg binary."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from sirens.production.mixing import _settings


def settings(overrides=None):
    tracks = [
        dict(id="kick", role="drums", patch="tight_kick"),
        dict(id="gears", role="bass", patch="gear_bass"),
        dict(id="sub", role="bass", patch="mono_sub"),
        dict(id="deep", role="sub", patch="plain"),
        dict(id="low", role="bass", patch="mono_sub"),
        dict(id="sub_layer", role="bass", patch="plain"),
        dict(id="subtle", role="bass", patch="subtle_bass"),
    ]
    plan = dict(tracks=tracks, mix=dict(tracks=overrides or {}))
    stems = dict(stems=[dict(track_id=t["id"], role=t["role"]) for t in tracks])
    return _settings(plan, stems)


def graph_for(config, dry=False):
    path = Path(__file__).resolve().parents[2] / "workers" / "production_mix" / "ffmpeg_mix.py"
    spec = importlib.util.spec_from_file_location("mix_graph_test", path)
    audio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audio)
    with patch.object(audio, "run") as run:
        audio.render_graph("ffmpeg", ["stem.wav"] * len(config), config,
                           48000, "output.wav", dry=dry)
    args = run.call_args.args[1]
    return args[args.index("-filter_complex") + 1].split(";")


class MixingRoleTests(unittest.TestCase):
    def test_bass_is_not_sub(self):
        cfg = settings({"gears": {"pan": .5}})
        self.assertEqual([s["sub"] for s in cfg],
                         [False, False, True, True, True, True, False])
        self.assertTrue(cfg[1]["bass"])
        self.assertFalse(cfg[1]["sidechain"])
        self.assertTrue(cfg[2]["sidechain"])
        self.assertNotEqual(cfg[1]["highpass_hz"], cfg[2]["highpass_hz"])
        self.assertNotEqual(cfg[1]["eq_db"], cfg[2]["eq_db"])
        graph = graph_for(cfg)
        self.assertIn("acompressor=", graph[1])
        self.assertIn("equalizer=", graph[1])
        self.assertIn("c0=0.70710678*c0", graph[1])
        self.assertNotIn("0.5*c0+0.5*c1", graph[1])
        self.assertNotIn("asetnsamples", graph[1])
        self.assertNotIn("[key1]", ";".join(graph))
        for i in (2, 3, 4, 5):
            self.assertIn("0.5*c0+0.5*c1", graph[i])
            self.assertIn("asetnsamples=n=1024:p=1", graph[i])
            self.assertIn(f"[track{i}][key{i}]sidechaincompress=", ";".join(graph))
        self.assertIn("asetnsamples=n=1024:p=1", graph[0])

    def test_explicit_sidechain_does_not_make_bass_mono(self):
        cfg = settings({"gears": {"sidechain": True, "pan": .5},
                        "sub": {"sidechain": False}})
        graph = graph_for(cfg)
        self.assertIn("[track1][key1]sidechaincompress=", ";".join(graph))
        self.assertNotIn("0.5*c0+0.5*c1", graph[1])
        self.assertIn("asetnsamples=n=1024:p=1", graph[1])
        self.assertIn("0.5*c0+0.5*c1", graph[2])
        self.assertNotIn("[key2]", ";".join(graph))
        dry = ";".join(graph_for(cfg, dry=True))
        self.assertNotIn("acompressor=", dry)
        self.assertNotIn("sidechaincompress=", dry)
        self.assertNotIn("asetnsamples", dry)

    def test_sidechain_must_be_boolean(self):
        for value in (1, 0, "false", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings({"gears": {"sidechain": value}})
