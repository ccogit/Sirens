"""Local, read-only catalogue/AMM reference adapter. No audio reuse or DB writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from ..catalog import ACHSEN, Katalog, bekannte_bewertungen
from ..store import Store, write_json_atomic
from .contracts import safe_path, sha256_file, validate_brief

METHOD = "sirens.realtime.music_analysis.analyse_file/1"


def _id(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


def _norm(value):
    return "".join(c for c in str(value or "").casefold() if c.isalnum())


def _rating(value):
    return value if type(value) is int and -2 <= value <= 2 else None


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_invalid_constant)


def _invalid_constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def _axes(values):
    return {k: v for k, v in (values if isinstance(values, dict) else {}).items() if k in ACHSEN
            and type(v) in (int, float) and 0 <= v <= 10}


def _identity(artist, release, title, version):
    return (_norm(artist), _norm(release), _norm(title), version)


def _sidecar(root, release, title):
    """Existing catalog convention; ambiguous variants are not guessed."""
    folder = safe_path(root, release)
    candidates = []
    for directory in (folder, folder / "Lyrics-Fassungen"):
        if directory.is_symlink() or not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.txt")):
            match = re.fullmatch(r"(.+) - lyrics(?: \[song \d+\])?", path.stem, re.I)
            if match and _norm(match[1]) == _norm(title) and not path.is_symlink():
                try:
                    value = _text(path.read_text(encoding="utf-8-sig"))
                except (OSError, UnicodeError):
                    continue
                if value:
                    candidates.append(value)
    return candidates[0] if candidates and len(set(candidates)) == 1 else None


def _raw(row, source):
    score = _rating(row.get("score", row.get("outcome_score")))
    if score is None:
        return None
    favorite = row.get("favorit", row.get("favorite"))
    return {"score": score, "favorite": favorite if type(favorite) is bool else None,
            "comment": _text(row.get("kommentar", row.get("comment"))),
            "source": source, "axes": _axes(row.get("achsen", row.get("axes")))}


def _export_index(export):
    """Explicit local projection of the existing AMM read-only resolver, not SQL."""
    index = defaultdict(list)
    if export is None:
        return index
    if export.get("schema_version") != 1 or not isinstance(export.get("songs"), list):
        raise ValueError("AMM export: expected schema_version=1 and songs list")
    for row in export["songs"]:
        key = _identity(row.get("artist_slug"), row.get("release_slug"),
                        row.get("title"), row.get("version"))
        index[key].append(row)
    return index


def collect(cfg, *, amm_export=None):
    """Read catalog tree, raw Store judgments and optional local AMM projection."""
    store = Store(cfg)
    orders = store.list()
    catalog = Katalog(cfg)
    catalog.scan()
    tree = catalog.baum(bekannte_bewertungen(cfg, store))
    raw = defaultdict(list)
    order_metadata = defaultdict(list)
    for order in orders:
        plan = {t["nr"]: t for t in (order.get("plan") or {}).get("tracks", [])}
        for stand in order.get("tracks_stand", []):
            metadata = plan.get(stand["nr"], {})
            for relative in stand.get("dateien", []):
                order_metadata[relative].append(metadata)
        for row in order.get("bewertungen", []):
            item = _raw(row, "store")
            if item is not None:
                item["order_id"] = order["id"]
                raw[row["pfad"]].append(item)
    index = _export_index(amm_export)
    tracks = []
    skipped = 0
    ambiguous = 0
    hashes = {}
    parents = {}

    def find(key):
        while parents.get(key, key) != key:
            key = parents[key]
        return key

    for release in tree["releases"]:
        for song in release["songs"]:
            title = song["titel"]
            family = _id(release["pfad"], _norm(title))
            for file in song["dateien"]:
                relative = file["pfad"]
                try:
                    path = safe_path(cfg.music_root, relative)
                    digest = sha256_file(path)
                except (OSError, ValueError):
                    skipped += 1
                    continue
                if digest in hashes:
                    a, b = sorted((find(family), find(hashes[digest])))
                    if a != b:
                        parents[b] = a
                hashes[digest] = family
                key = _identity(release.get("stilreferenz"), release["slug"],
                                title, file.get("version"))
                matches = index.get(key, [])
                # Only one unambiguous identity; never attach an arbitrary package.
                amm = matches[0] if len(matches) == 1 else {}
                ambiguous += len(matches) > 1
                ratings = list(raw[relative])
                ratings.extend(item for row in amm.get("song_evaluations", [])
                               if (item := _raw(row, "amm")) is not None)
                aggregate = file.get("bewertung") or {}
                axes = _axes(aggregate.get("achsen"))
                axes.update(_axes(amm.get("axes")))
                favorites = [r["favorite"] for r in ratings if r["favorite"] is not None]
                score = _rating(aggregate.get("score"))
                if score is None:
                    score = max((r["score"] for r in ratings), default=None)
                metadata = order_metadata[relative]
                def unique_text(field):
                    values = {_text(m.get(field)) for m in metadata} - {None}
                    return next(iter(values)) if len(values) == 1 else None
                lyrics = (_text(amm.get("lyrics")) or unique_text("text") or
                          _sidecar(cfg.music_root, release["pfad"], title))
                short = song.get("kurzprofil") or {}
                tracks.append({
                    "id": _id(relative), "song_family": family, "relative_path": relative,
                    "rating": score, "catalog_rating": _rating(aggregate.get("score")),
                    "raw_ratings": ratings, "raw_comments": [r["comment"] for r in ratings if r["comment"]],
                    "favorite": True if True in favorites else False if favorites else None,
                    "axes": axes, "style_text": _text(amm.get("style_prompt")),
                    "lyrics": lyrics, "description": _text(song.get("beschreibung")),
                    "negative_tags": amm.get("negative_tags"), "parameters": amm.get("parameters"),
                    "style_hint": unique_text("stil_kurz") or release.get("stilreferenz") or None,
                    "bpm_text": short.get("tempo_bpm"), "bpm_measured": None,
                    "bpm_confidence": None, "key": None, "key_confidence": None,
                    "features": {}, "source": {"sha256": digest, "version": file.get("version"),
                        "release": release["pfad"], "title": title,
                        "fassung": file.get("fassung"), "amm_resolved": bool(amm)},
                    "usage": "analysis_only",
                })
    for track in tracks:
        track["song_family"] = find(track["song_family"])
    coverage = {"catalog_status": tree["zustand"], "orders": len(orders),
                "amm_available": amm_export is not None, "amm_ambiguous": ambiguous,
                "skipped_files": skipped, "tracks": len(tracks),
                "families": len({t["song_family"] for t in tracks}),
                "unrated": sum(t["rating"] is None for t in tracks),
                "raw_ratings": sum(len(t["raw_ratings"]) for t in tracks),
                "comments": sum(len(t["raw_comments"]) for t in tracks),
                "favorites": sum(t["favorite"] is True for t in tracks),
                "positive": sum(t["rating"] in (1, 2) for t in tracks),
                "with_axes": sum(bool(t["axes"]) for t in tracks),
                "with_prompts": sum(t["style_text"] is not None for t in tracks),
                "amm_resolved": sum(t["source"]["amm_resolved"] for t in tracks),
                "with_measured_bpm": 0,
                "with_lyrics": sum(t["lyrics"] is not None for t in tracks)}
    coverage["favorite_status"] = ("found" if coverage["favorites"] else
                                    "none_found_in_available_sources")
    coverage["missing_sources"] = (["amm_export"] if amm_export is None else []) + (
        ["catalog"] if tree["zustand"] != "bereit" else []) + (
        ["store"] if not cfg.orders_dir.is_dir() else [])
    return sorted(tracks, key=lambda t: t["id"]), coverage


def _tokens(value):
    return set(re.findall(r"\w+", (value or "").casefold()))


def _distance(track, brief):
    target = _tokens(brief.get("style"))
    style = _tokens(" ".join(t for t in (track["style_text"], track["style_hint"],
                                       track["description"]) if t))
    similarity = len(target & style) / max(1, len(target | style))
    tempo = track["bpm_measured"] or track["bpm_text"]
    bpm = brief.get("bpm")
    distance = min(abs(tempo - bpm) / 30, 2) if tempo and bpm else 1
    return (1 - similarity + distance, -int(track["favorite"] is True),
            -abs(track["rating"] or 0), track["id"])


def _groups(tracks):
    groups = defaultdict(list)
    for track in tracks:
        groups[track["song_family"]].append(track)
    return groups


def _measure(cfg, track, cache):
    from ..realtime.music_analysis import analyse_file
    from ..contracts import Ablehnung
    digest = track["source"]["sha256"]
    key = _id(digest, METHOD)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (key + ".json")
    try:
        result = _json(path)
        if result.get("method") != METHOD or result.get("sha256") != digest:
            raise ValueError("cache mismatch")
    except (OSError, ValueError):
        try:
            data = analyse_file(safe_path(cfg.music_root, track["relative_path"]),
                                ffmpeg=os.environ.get("SIRENS_FFMPEG") or "ffmpeg")
        except (OSError, ValueError, Ablehnung):
            track["features"]["measurement_status"] = "unavailable"
            return
        grid = data.get("grid") or {}
        result = {"method": METHOD, "sha256": digest, "bpm": grid.get("bpm"),
                  "bpm_confidence": grid.get("confidence"), "key": data.get("key"),
                  "key_confidence": data.get("key_confidence"),
                  "sections": data.get("sections"), "onsets": data.get("onsets"),
                  "grid": grid or None}
        write_json_atomic(path, result)
    track.update(bpm_measured=result["bpm"], bpm_confidence=result["bpm_confidence"],
                 key=result["key"], key_confidence=result["key_confidence"])
    track["features"] = result


def build_references(tracks, coverage, brief, *, measure=None):
    """Deterministic family holdout, then one representative per training family/sign."""
    validate_brief(brief)
    groups = _groups(tracks)
    rated = sorted(family for family, members in groups.items()
                   if any(t["rating"] in (-2, -1, 1, 2) for t in members))
    # Fixed split independent of brief; preserve at least one training family.
    held = set()
    remaining = {sign: {f for f in rated if any(t["rating"] * sign > 0
                 for t in groups[f] if t["rating"] is not None)} for sign in (-1, 1)}
    limit = max(1, len(rated)//5) if len(rated) >= 3 else 0
    for family in sorted(rated, key=lambda f: _id("holdout-v1", f)):
        if len(held) >= limit:
            break
        if any(family in members and len(members - held) <= 1 for members in remaining.values()):
            continue
        held.add(family)
    training = {f: members for f, members in groups.items() if f not in held}
    if measure:
        for members in training.values():
            for track in members:
                if track["rating"] in (-2, -1, 1, 2):
                    measure(track)
    selected = []
    contrasts = []
    conflicts = 0
    for members in training.values():
        signs = {1 if t["rating"] > 0 else -1 for t in members
                 if t["rating"] in (-2, -1, 1, 2)}
        signs.update(1 if r["score"] > 0 else -1 for t in members for r in t["raw_ratings"]
                     if r["score"] != 0)
        if len(signs) > 1:
            conflicts += 1
            continue
        positive = [t for t in members if t["rating"] in (1, 2)]
        negative = [t for t in members if t["rating"] in (-1, -2)]
        if positive:
            selected.append(min(positive, key=lambda t: _distance(t, brief)))
        elif negative:
            contrasts.append(min(negative, key=lambda t: _distance(t, brief)))
    selected = sorted(selected, key=lambda t: _distance(t, brief))[:5]
    contrasts = sorted(contrasts, key=lambda t: _distance(t, brief))[:3]
    # Production pairs are provenance only, not additional musical votes.
    pairs = []
    for members in training.values():
        originals = [t for t in members if not t["source"]["fassung"]]
        for master in members:
            if "emastered" not in (master["source"]["fassung"] or "").casefold():
                continue
            matching = [t for t in originals if all(t["source"][k] == master["source"][k]
                            for k in ("release", "title", "version"))]
            if len(matching) == 1:
                pairs.append({"original": matching[0]["id"], "master": master["id"]})
    coverage = dict(coverage, holdout_families=len(held), conflicting_families=conflicts,
                    selected=len(selected), contrasts=len(contrasts),
                    with_measured_bpm=sum(t["bpm_measured"] is not None for t in tracks))
    def summary(t):
        return {"id": t["id"], "title": t["source"]["title"], "rating": t["rating"],
                "style": t["style_text"] or t["style_hint"],
                "bpm_measured": t["bpm_measured"], "bpm_text": t["bpm_text"],
                "axes": t["axes"], "description": t["description"]}

    result = {"schema_version": 1, "tracks": tracks, "selected": [t["id"] for t in selected],
            "holdout": [t["id"] for t in tracks if t["song_family"] in held],
            "profile": {"music": {"positive_examples": [t["id"] for t in selected],
                                  "negative_examples": [t["id"] for t in contrasts],
                                  "producer_examples": [summary(t) for t in selected],
                                  "producer_contrasts": [summary(t) for t in contrasts]},
                        "production": {"original_master_pairs": pairs},
                        "coverage": coverage}}
    validate_references(result)
    return result


def validate_references(value):
    """Local V1 guard until K00 provides a shared references validator."""
    from .contracts import validate_relative_path
    if value.get("schema_version") != 1:
        raise ValueError("references schema_version")
    tracks = {t["id"]: t for t in value["tracks"]}
    if len(tracks) != len(value["tracks"]):
        raise ValueError("duplicate reference id")
    for track in tracks.values():
        validate_relative_path(track["relative_path"])
        if track["usage"] != "analysis_only":
            raise ValueError("reference usage")
        if track["rating"] is not None and _rating(track["rating"]) is None:
            raise ValueError("reference rating")
    held = set(value["holdout"])
    selected = set(value["selected"]) | set(value["profile"]["music"]["negative_examples"])
    for pair in value["profile"]["production"]["original_master_pairs"]:
        selected.update((pair["original"], pair["master"]))
    if not (selected | held) <= tracks.keys():
        raise ValueError("unknown reference id")
    families = {tracks[i]["song_family"] for i in held}
    if any(tracks[i]["song_family"] in families for i in selected):
        raise ValueError("holdout family leak")
    if any(t["song_family"] in families and t["id"] not in held for t in tracks.values()):
        raise ValueError("incomplete holdout family")
    json.dumps(value, allow_nan=False)
    return value


def main(argv=None):
    from ..config import load, umgebung
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "references"))
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--amm-export", type=Path)
    parser.add_argument("--analyse", action="store_true", help="local mix analysis of rated training tracks")
    args = parser.parse_args(argv)
    cfg = load(umgebung())
    if args.action == "references" and args.brief is None:
        parser.error("references requires --brief")
    # Never write private reference data into the checkout.
    out = (cfg.data_dir / "production" / "references").resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo):
        parser.error("configure SIRENS_DATA_DIR outside the repository")
    if args.amm_export and args.amm_export.resolve().is_relative_to(repo):
        parser.error("AMM export must be outside the repository")
    tracks, coverage = collect(cfg, amm_export=_json(args.amm_export) if args.amm_export else None)
    out.mkdir(parents=True, exist_ok=True)
    if args.action == "inventory":
        write_json_atomic(out / "inventory.json", coverage)
    else:
        measure = (lambda t: _measure(cfg, t, out / "cache")) if args.analyse else None
        result = build_references(tracks, coverage, _json(args.brief), measure=measure)
        write_json_atomic(out / "references.json", result)
        coverage = result["profile"]["coverage"]
    print(json.dumps(coverage, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
