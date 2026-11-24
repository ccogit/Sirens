import copy
import unittest
from types import SimpleNamespace

from sirens.production import arrangement as a
from sirens.production.contracts import validate_plan


def brief(**overrides):
    value = dict(schema_version=1, title="Synthetic lighthouse fixture",
                 style="motorik at 126 BPM", negative_tags=["sung melody", "EDM drop"],
                 lyrics="Line one.\nLine two.\n\nAnother line.\nStill here.\n\nA bridge.",
                 bpm=126, key=None, target_seconds=181, seed=101,
                 reference_ids=[], vocal_mode="spoken")
    value.update(overrides)
    return value


def track(plan, tid):
    return next(t for t in plan["tracks"] if t["id"] == tid)


class ArrangementTests(unittest.TestCase):
    def test_full_song_and_three_distinct_variants(self):
        b = brief()
        plans = [a.clear_head_plan(b, v) for v in ("ratchet", "counterweight", "undertow")]
        self.assertEqual(len({str(track(p, "gears")["events"]) for p in plans}), 3)
        self.assertEqual(len({str(track(p, "buoy")["events"]) for p in plans}), 3)
        for variant, p in zip(("ratchet", "counterweight", "undertow"), plans):
            validate_plan(p)
            self.assertEqual(p, a.clear_head_plan(b, variant))
            self.assertEqual(p["key"], "D minor")
            self.assertEqual(p["bpm"], 126)
            self.assertLessEqual(abs(p["total_bars"] * 240 / 126 + 2 - 181), 1)
            self.assertEqual([s["id"] for s in p["sections"]],
                             ["intro", "chorus", "interlude1", "verse", "interlude2",
                              "bridge", "interlude3", "chorus_final", "outro"])
            self.assertEqual([e["tick"] for e in track(p, "kick")["events"]],
                             [e["tick"] for e in track(p, "sub")["events"]])
            self.assertFalse(track(p, "sub")["automation"])
            beam = track(p, "beam")["automation"]
            self.assertEqual(len(beam), p["total_bars"] * 3)
            for bar in range(p["total_bars"]):
                self.assertEqual([e["tick"] for e in beam[3*bar:3*bar+3]],
                                 [bar*a.BAR, bar*a.BAR+a.BAR//2, (bar+1)*a.BAR-1])
            speech = [r["text"] for r in p["asset_requests"] if r["kind"] == "speech"]
            self.assertEqual(speech, b["lyrics"].split("\n\n") + [b["lyrics"].split("\n\n")[0]])

    def test_requested_key_tempo_and_long_text(self):
        b = brief(key="F# major", bpm=110, target_seconds=None,
                  lyrics=" ".join(["word"] * 80) + "\n\nVerse.\n\nBridge.\n\nEnd.")
        p = a.clear_head_plan(b)
        self.assertEqual((p["key"], p["bpm"]), ("F# major", 110))
        self.assertGreater(p["sections"][1]["bars"], 4)
        self.assertEqual(track(p, "sub")["events"][0]["note"] % 12, 6)
        a.validate_arrangement(b, p)
        with self.assertRaises(ValueError):
            a.clear_head_plan(dict(b, target_seconds=5))

    def test_reject_truncated_or_overlapping_speech(self):
        b = brief(lyrics="Chorus.\n\nVerse.\n\nBridge.\n\nFinal.")
        p = a.clear_head_plan(b)
        short = copy.deepcopy(p)
        track(short, "voice")["events"][0]["duration_ticks"] = 1
        with self.assertRaises(ValueError):
            a.validate_arrangement(b, short)
        cut = copy.deepcopy(p)
        next(r for r in cut["asset_requests"] if r["kind"] == "speech")["text"] = "Chor"
        with self.assertRaises(ValueError):
            a.validate_arrangement(b, cut)

    def test_scoped_revision(self):
        p = a.clear_head_plan(brief())
        original = copy.deepcopy(p)
        s = next(s for s in p["sections"] if s["id"] == "intro")
        hi = s["bars"] * a.BAR
        old = track(p, "buoy")
        events = [dict(e, velocity=80) for e in old["events"] if e["tick"] < hi]
        revised, evidence = a.revise_window(p, "buoy", events, section_id="intro")
        self.assertEqual(p, original)
        self.assertNotEqual(evidence["before_sha256"], evidence["after_sha256"])
        self.assertEqual(revised["seed"], p["seed"])
        self.assertEqual([t for t in revised["tracks"] if t["id"] != "buoy"],
                         [t for t in p["tracks"] if t["id"] != "buoy"])
        self.assertEqual([e for e in track(revised, "buoy")["events"] if e["tick"] >= hi],
                         [e for e in old["events"] if e["tick"] >= hi])
        with self.assertRaises(ValueError):
            a.revise_window(p, "buoy", [dict(tick=hi-1, duration_ticks=2, note=60, velocity=80)],
                            section_id="intro")

    def test_amm_adapter_and_reference_context(self):
        reference = dict(schema_version=1, selected=["a", "b"], holdout=["b"],
                         tracks=[dict(id="a", features={"swing": 0.1}), dict(id="b")],
                         profile=dict(music={}, production={}, coverage={}))
        planner = SimpleNamespace(request_constraints=lambda style: {"tempo": 126})
        knowledge = SimpleNamespace(search=lambda style: {"available": False, "results": []})
        context = a.agent_context(brief(), reference, amm_planner=planner, amm_knowledge=knowledge)
        self.assertEqual([t["id"] for t in context["selected"]], ["a"])
        self.assertEqual(context["amm_constraints"], {"tempo": 126})
        self.assertFalse(context["amm_knowledge"]["available"])
        self.assertEqual(a.amm_notes_to_events([dict(start=1.125, duration=.25, pitch=60, velocity=100)]),
                         [dict(tick=1080, duration_ticks=240, note=60, velocity=100)])
        with self.assertRaises(ValueError):
            a.amm_notes_to_events([dict(start=1, duration=.00001, pitch=60, velocity=100)])


if __name__ == "__main__":
    unittest.main()
