"""Offline acceptance tests for AUFGABE-18."""
import copy
import math
import unittest

from sirens.production import arrangement as a
from sirens.production.contracts import validate_plan


CUES = ("A complete chorus.", "The complete second passage.",
        "A complete bridge.", "A complete final chorus.")
DURATIONS = (4.8, 6.3, 4.9, 4.8)
VARIANTS = ("ratchet", "counterweight", "undertow")


def brief(target=45, **overrides):
    value = dict(schema_version=1, title="Synthetic preview", style="motorik",
                 negative_tags=["sung melody"], lyrics="\n\n".join(CUES),
                 bpm=126, key="D minor", target_seconds=target, seed=101,
                 reference_ids=[], vocal_mode="spoken")
    value.update(overrides)
    return value


def track(plan, tid):
    return next(t for t in plan["tracks"] if t["id"] == tid)


class PreviewTests(unittest.TestCase):
    def test_measured_cues_fit_whole_bars_in_all_variants(self):
        for target in (30, 45, 60):
            for variant in VARIANTS:
                with self.subTest(target=target, variant=variant):
                    b = brief(target)
                    p = a.clear_head_plan(b, variant, cue_durations_seconds=DURATIONS)
                    validate_plan(p)
                    a.validate_arrangement(b, p)
                    self.assertTrue(30 <= p["total_bars"] * 240 / 126 + p["tail_seconds"] <= 60)
                    self.assertLessEqual(abs(p["total_bars"] * 240 / 126
                                             + p["tail_seconds"] - target), 240 / 126)
                    requests = [r for r in p["asset_requests"] if r["kind"] == "speech"]
                    self.assertGreaterEqual(len(requests), 2)
                    self.assertEqual([r["text"] for r in requests], list(CUES[:len(requests)]))
                    if target == 30:
                        self.assertLess(len(requests), 4)
                    else:
                        self.assertEqual(len(requests), 4)
                    cursor = 0
                    for section in p["sections"]:
                        self.assertEqual(section["start_bar"], cursor)
                        cursor += section["bars"]
                    self.assertEqual(cursor, p["total_bars"])
                    for i, (request, event) in enumerate(zip(requests, track(p, "voice")["events"])):
                        self.assertEqual(event["asset_id"], request["id"])
                        self.assertGreaterEqual(request["duration_seconds"] + 1e-9, DURATIONS[i])
                        section = next(s for s in p["sections"] if "cue_" + s["id"] == request["id"])
                        length = math.ceil(DURATIONS[i] * 126 / 60 * a.PPQ)
                        pause = math.ceil(0.5 * 126 / 60 * a.PPQ)
                        self.assertEqual(event["duration_ticks"], length)
                        self.assertEqual(event["tick"], section["start_bar"] * a.BAR + 240)
                        self.assertEqual(section["bars"], math.ceil((240 + length + pause) / a.BAR))
                        self.assertLessEqual(event["tick"] + length + pause,
                                             (section["start_bar"] + section["bars"]) * a.BAR)
                    self.assertEqual([e["tick"] for e in track(p, "kick")["events"]],
                                     [e["tick"] for e in track(p, "sub")["events"]])
                    self.assertEqual(p, a.clear_head_plan(b, variant, cue_durations_seconds=DURATIONS))

    def test_distinct_grooves_swing_and_semantic_patches(self):
        plans = [a.clear_head_plan(brief(), v, cue_durations_seconds=DURATIONS)
                 for v in VARIANTS]
        for tid in ("gears", "buoy"):
            self.assertEqual(len({track(p, tid)["patch"] for p in plans}), 3)
            self.assertEqual(len({tuple(e["tick"] for e in track(p, tid)["events"])
                                  for p in plans}), 3)
        self.assertEqual(len({track(p, "hats")["events"][0]["tick"] for p in plans}), 3)

    def test_preview_rejects_cut_text_and_invalid_durations(self):
        b = brief(30)
        p = a.clear_head_plan(b, cue_durations_seconds=DURATIONS)
        bad = copy.deepcopy(p)
        next(r for r in bad["asset_requests"] if r["kind"] == "speech")["text"] = "A complete"
        with self.assertRaises(ValueError):
            a.validate_arrangement(b, bad)
        for invalid in ([], (1, 2, 3), (True, 2, 3, 4), (0, 2, 3, 4),
                        (math.nan, 2, 3, 4), (math.inf, 2, 3, 4)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                a.clear_head_plan(b, cue_durations_seconds=invalid)
        with self.assertRaises(ValueError):
            a.clear_head_plan(b, cue_durations_seconds=(100, 100, 100, 100))

    def test_explicit_preview_and_estimated_duration_fallback(self):
        b = brief(None)
        p = a.clear_head_plan(b, preview=True, cue_durations_seconds=DURATIONS)
        a.validate_arrangement(b, p)
        self.assertTrue(30 <= p["total_bars"] * 240 / 126 + p["tail_seconds"] <= 60)
        estimated = a.clear_head_plan(brief(30))
        a.validate_arrangement(brief(30), estimated)

    def test_full_song_retains_original_structure_and_patches(self):
        b = brief(181)
        for v in VARIANTS:
            p = a.clear_head_plan(b, v)
            a.validate_arrangement(b, p)
            self.assertEqual([s["id"] for s in p["sections"]],
                             ["intro", "chorus", "interlude1", "verse", "interlude2",
                              "bridge", "interlude3", "chorus_final", "outro"])
            self.assertEqual([r["text"] for r in p["asset_requests"] if r["kind"] == "speech"],
                             list(CUES))
            self.assertEqual(track(p, "gears")["patch"], "gear_bass")
            self.assertEqual(track(p, "buoy")["patch"], "bell_buoy")
            self.assertEqual(track(p, "hats")["events"][0]["tick"], 492)
            self.assertLessEqual(abs(p["total_bars"] * 240 / 126 + 2 - 181), 240 / 126)


if __name__ == "__main__":
    unittest.main()
