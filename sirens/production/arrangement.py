"""Contract-level arrangement helpers, not a generic song generator.

AMM remains the musical proposal engine for general briefs. The Clear Head
recipe is an explicitly authored, reproducible test arrangement.
"""
from copy import deepcopy
import hashlib
import json
import math
import random
import re

BAR = 3840
PPQ = 960


def _contracts():
    from . import contracts
    return contracts


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8")).hexdigest()


def agent_context(brief, references, *, amm_planner=None, amm_knowledge=None):
    """Read-only agent inputs. Inject trusted local AMM modules, never paths
    or callables from a brief. No model, network or Live calls here."""
    _contracts().validate_brief(brief)
    if references.get("schema_version") != 1:
        raise ValueError("references schema_version must be 1")
    selected = set(references["selected"]) - set(references["holdout"])
    tracks = []
    for track in references["tracks"]:
        if track["id"] in selected:
            tracks.append({key: deepcopy(track.get(key)) for key in
                           ("id", "style_text", "bpm_measured", "bpm_confidence",
                            "key", "key_confidence", "axes", "features")})
    style = brief["style"] or ""
    constraints = (amm_planner.request_constraints(style)
                   if amm_planner is not None else {})
    if (brief["bpm"] is not None and "tempo" in constraints
            and brief["bpm"] != constraints["tempo"]):
        raise ValueError("Brief BPM conflicts with AMM text constraint")
    return {"brief": deepcopy(brief), "selected": tracks,
            "profile": deepcopy(references["profile"]),
            "amm_constraints": constraints,
            "amm_knowledge": (amm_knowledge.search(style)
                              if amm_knowledge is not None else None)}


def amm_notes_to_events(notes):
    """Adapt AMM absolute-beat notes to Sirens absolute integer ticks."""
    events = []
    for note in notes:
        start, duration = note["start"], note["duration"]
        pitch, velocity = note["pitch"], note["velocity"]
        if (type(start) not in (int, float) or type(duration) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(duration)
                or start < 0 or duration <= 0 or type(pitch) is not int
                or not 0 <= pitch <= 127 or type(velocity) is not int
                or not 1 <= velocity <= 127):
            raise ValueError("Invalid AMM note")
        tick = round(start * PPQ)
        length = round((start + duration) * PPQ) - tick
        if length <= 0:
            raise ValueError("AMM note shorter than tick resolution")
        events.append(dict(tick=tick, duration_ticks=length,
                           note=pitch, velocity=velocity))
    return sorted(events, key=lambda e: (e["tick"], e["note"]))


def validate_arrangement(brief, plan, *, lyrics=None):
    """Check explicit brief constraints on an agent-authored plan."""
    _contracts().validate_brief(brief)
    _contracts().validate_plan(plan)
    for key in ("bpm", "key", "seed"):
        if brief[key] is not None and brief[key] != plan[key]:
            raise ValueError("Plan contradicts brief: " + key)
    if brief["vocal_mode"] == "spoken":
        if any(t["role"] in ("vocal", "vocals", "singing") for t in plan["tracks"]):
            raise ValueError("Spoken brief cannot contain sung track")
        requests = {r["id"]: r for r in plan["asset_requests"]}
        cues = []
        for track in plan["tracks"]:
            for event in track["events"]:
                request = requests.get(event.get("asset_id"))
                if request is None or request["kind"] != "speech":
                    continue
                if track["role"] != "spoken":
                    raise ValueError("Speech requires spoken role")
                seconds = event["duration_ticks"] / PPQ * 60 / plan["bpm"]
                if seconds + 1e-9 < request["duration_seconds"]:
                    raise ValueError("Speech reservation shorter than requested audio")
                cues.append((event["tick"], event["duration_ticks"], request["text"]))
        cues.sort()
        if any(a[0] + a[1] > b[0] for a, b in zip(cues, cues[1:])):
            raise ValueError("Overlapping spoken cues")
        expected = brief["lyrics"] if lyrics is None else lyrics
        if " ".join(" ".join(c[2] for c in cues).split()) != " ".join((expected or "").split()):
            raise ValueError("Spoken lyrics differ from brief")
    return plan


# Patterns are original, relative scale degrees, not extracted reference notes.
# Each tuple is (sixteenth offset, degree, length in sixteenths).
_VARIANTS = {
    "ratchet": ((0, 0, 2), (3, 0, 1), (6, 4, 2), (8, 0, 2),
                (11, 2, 1), (14, 4, 2)),
    "counterweight": ((0, 0, 3), (5, 7, 2), (8, 0, 3), (13, 5, 2)),
    "undertow": ((0, 0, 2), (2, 1, 2), (7, 4, 1), (8, 0, 2),
                 (10, -1, 2), (15, 1, 1)),
}
_HOOKS = {
    "ratchet": ((3, 4), (7, 2), (13, 0)),
    "counterweight": ((2, 7), (9, 4), (14, 5)),
    "undertow": ((1, 1), (6, 4), (11, 6), (15, 2)),
}


def _scale(key):
    match = re.fullmatch(r"([A-G])([#b]?) (minor|major)", key)
    if not match:
        raise ValueError("Clear Head key must be a named major/minor key")
    root = dict(C=0, D=2, E=4, F=5, G=7, A=9, B=11)[match[1]]
    root += {"": 0, "#": 1, "b": -1}[match[2]]
    intervals = (0, 2, 3, 5, 7, 8, 10) if match[3] == "minor" else (0, 2, 4, 5, 7, 9, 11)
    return lambda degree, octave: 12 * octave + root + 12 * (degree // 7) + intervals[degree % 7]


def clear_head_plan(brief, variant="ratchet"):
    """Authored lighthouse arrangement. Lyrics: three blank-line separated
    passages (chorus repeated at end) or four explicitly supplied passages."""
    _contracts().validate_brief(brief)
    if variant not in _VARIANTS or brief["vocal_mode"] != "spoken":
        raise ValueError("Unknown variant or non-spoken Clear Head brief")
    lyrics = brief["lyrics"] or ""
    cues = re.split(r"\n[ \t]*\n", lyrics.strip().replace("\r\n", "\n"))
    if len(cues) == 3:
        cues.append(cues[0])
    if len(cues) != 4 or not all(c.strip() for c in cues):
        raise ValueError("Supply chorus, verse, bridge and optional final chorus")
    bpm = brief["bpm"] if brief["bpm"] is not None else 126
    key = brief["key"] or "D minor"
    pitch = _scale(key)
    seed = brief["seed"]
    rng = random.Random(seed)
    bar_seconds = 240 / bpm
    # Budget generous speech time, not a claim about the measured TTS duration.
    speech_seconds = [max(2.0, len(c.split()) / 1.8 + 1.5) for c in cues]
    speech_bars = [max(4, math.ceil((s + 0.5) / bar_seconds)) for s in speech_seconds]
    intro, outro = max(1, round(15 / bar_seconds)), max(1, round(5 / bar_seconds))
    interludes = [max(1, round(s / bar_seconds)) for s in (35, 45, 45)]
    if brief["target_seconds"] is not None:
        wanted = round((brief["target_seconds"] - 2) / bar_seconds)
        budget = wanted - intro - outro - sum(speech_bars)
        if budget < 3:
            raise ValueError("Target duration cannot hold complete spoken cues")
        interludes = [max(1, round(budget * 35 / 125)),
                      max(1, round(budget * 45 / 125)), 1]
        interludes[2] = budget - sum(interludes[:2])
        if interludes[2] < 1:
            raise ValueError("Target too short for three interludes")
    specs = [
        ("intro", intro, "gears start, kick/sub and buoy"),
        ("chorus", speech_bars[0], "sparse calm spoken chorus"),
        ("interlude1", interludes[0], "mandolin and gulls, turning gears"),
        ("verse", speech_bars[1], "clear-eyed spoken verse"),
        ("interlude2", interludes[1], "foghorn rise, cello and brass bell"),
        ("bridge", speech_bars[2], "stripped spoken bridge"),
        ("interlude3", interludes[2], "brightest full instrumental ensemble"),
        ("chorus_final", speech_bars[3], "return of spoken chorus"),
        ("outro", outro, "dawn, lamp clicks off"),
    ]
    sections = []
    total = 0
    for sid, bars, intent in specs:
        sections.append(dict(id=sid, start_bar=total, bars=bars, intent=intent))
        total += bars
    roles = [
        ("kick", "drums", "tight_kick"), ("sub", "bass", "mono_sub"),
        ("gears", "bass", "gear_bass"), ("hats", "drums", "closed_hat"),
        ("buoy", "lead", "bell_buoy"), ("beam", "texture", "stereo_beam"),
        ("mandolin", "instrument", "mandolin"), ("cello", "instrument", "cello"),
        ("brass", "instrument", "ship_bell"), ("voice", "spoken", "spoken_calm"),
        ("atmosphere", "texture", "maritime_foley"),
    ]
    tracks = {tid: dict(id=tid, role=role, patch=patch,
                        backend="asset" if tid in ("voice", "atmosphere") else "instrument",
                        events=[], automation=[]) for tid, role, patch in roles}
    requests = []

    def note(tid, tick, length, p, velocity):
        tracks[tid]["events"].append(dict(tick=tick, duration_ticks=length,
                                          note=p, velocity=velocity))

    def asset(tid, aid, kind, tick, length, prompt, text=None):
        request = dict(id=aid, kind=kind, seed=seed + len(requests),
                       duration_seconds=length / PPQ * 60 / bpm, prompt=prompt)
        if text is not None:
            request["text"] = text
        requests.append(request)
        tracks[tid]["events"].append(dict(tick=tick, duration_ticks=length, asset_id=aid))

    spoken_ids = ("chorus", "verse", "bridge", "chorus_final")
    for section in sections:
        sid = section["id"]
        start = section["start_bar"] * BAR
        end = start + section["bars"] * BAR
        spoken = sid in spoken_ids
        if spoken:
            idx = spoken_ids.index(sid)
            length = math.ceil(speech_seconds[idx] * bpm / 60 * PPQ)
            asset("voice", "cue_" + sid, "speech", start + 240, length,
                  "calm close male spoken, no singing", cues[idx])
        if sid in ("interlude1", "interlude3"):
            asset("atmosphere", "gulls_" + sid, "foley", start,
                  min(BAR * 2, end - start), "distant gulls, existing licensed asset first")
        if sid == "interlude2":
            length = min(2 * BAR, end - start)
            asset("atmosphere", "foghorn", "texture", end - length, length,
                  "low foghorn swelling riser, existing licensed asset first")
        if sid == "outro":
            asset("atmosphere", "lamp_off", "foley", end - PPQ, PPQ,
                  "isolated mechanical lamp switch click")
        for bar in range(section["bars"]):
            t = start + bar * BAR
            # Locked kick/sub, upper gear/hat offsets never affect sub.
            if sid != "outro" or bar < section["bars"] - 1:
                for beat in range(4):
                    k = t + beat * PPQ
                    note("kick", k, 180, 36, 115 if beat == 0 else 108)
                    note("sub", k, 300, pitch(0, 3), 98)
                for step, degree, length in _VARIANTS[variant]:
                    shift = 0 if step % 2 == 0 else 12
                    note("gears", t + step * 240 + shift,
                         length * 240 - 40, pitch(degree, 4 if variant != "counterweight" else 5),
                         (75 if spoken else 96) + rng.randrange(-4, 5))
                for step in (2, 6, 10, 14):
                    note("hats", t + step * 240 + (12 if step % 4 == 2 else 0),
                         100, 42, (48 if spoken else 70) + rng.randrange(-5, 6))
            if not spoken and sid != "outro":
                for step, degree in _HOOKS[variant]:
                    note("buoy", t + step * 240, 180, pitch(degree, 6), 92)
            note("beam", t, BAR - 1, pitch(4, 6), 48 if spoken else 65)
            # One complete left-to-right sweep per bar, upper beam only.
            for offset, pan in ((0, -0.85), (BAR // 2, 0.0), (BAR - 1, 0.85)):
                tracks["beam"]["automation"].append(dict(tick=t + offset, parameter="pan", value=pan))
            if sid in ("interlude1", "interlude2", "interlude3"):
                for step, degree in ((1, 0), (5, 2), (10, 4), (13, 2)):
                    note("mandolin", t + step * 240, 200, pitch(degree, 5), 76)
            if sid in ("interlude2", "interlude3"):
                degree = (0, 5, 4, 0)[bar % 4]
                note("cello", t, BAR - 120, pitch(degree, 4), 70)
                if bar % 4 == 3 or bar == section["bars"] - 1:
                    note("brass", t + 2 * PPQ, PPQ, pitch(0, 5), 90)
    for track in tracks.values():
        track["events"].sort(key=lambda e: (e["tick"], e.get("note", 0)))
    plan = dict(schema_version=1, seed=seed, bpm=bpm, key=key, meter=[4, 4],
                ppq=PPQ, total_bars=total, tail_seconds=2, sections=sections,
                tracks=list(tracks.values()), asset_requests=requests,
                mix=dict(target_lufs=None, ceiling_dbtp=-1))
    return validate_arrangement(brief, plan, lyrics="\n".join(cues))


def revise_window(plan, track_id, events, *, section_id=None, automation=None):
    """Replace one track or section window; absolute ticks, no crossing tails.
    Return new plan and deterministic change evidence; never mutate original.
    Asset requests and timeline remain unchanged in this narrow operation."""
    _contracts().validate_plan(plan)
    result = deepcopy(plan)
    track = next((t for t in result["tracks"] if t["id"] == track_id), None)
    if track is None:
        raise ValueError("Unknown track")
    lo, hi = 0, plan["total_bars"] * BAR
    if section_id is not None:
        section = next((s for s in plan["sections"] if s["id"] == section_id), None)
        if section is None:
            raise ValueError("Unknown section")
        lo = section["start_bar"] * BAR
        hi = lo + section["bars"] * BAR
    before = _digest(track)
    retained = []
    for event in track["events"]:
        start, end = event["tick"], event["tick"] + event["duration_ticks"]
        if end <= lo or start >= hi:
            retained.append(event)
        elif start < lo or end > hi:
            raise ValueError("Existing event crosses revision boundary")
    if any(e["tick"] < lo or e["tick"] + e["duration_ticks"] > hi for e in events):
        raise ValueError("Replacement crosses revision boundary")
    track["events"] = sorted(retained + deepcopy(events), key=lambda e: (e["tick"], e.get("note", 0)))
    if automation is not None:
        # Section edits cannot change inherited automation state outside the
        # window implicitly: require whole-track automation replacement instead.
        if section_id is not None:
            raise ValueError("Automation revision requires explicit whole-track scope")
        track["automation"] = deepcopy(automation)
    _contracts().validate_plan(result)
    return result, dict(track_id=track_id, section_id=section_id, seed=plan["seed"],
                        before_sha256=before, after_sha256=_digest(track))
