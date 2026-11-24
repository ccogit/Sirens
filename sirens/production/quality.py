"""Offline production quality audit. No audio/model dependencies in the main process."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import subprocess
import wave
from pathlib import Path

from . import contracts as c


def measure_wav(path, frames=None):
    """Sample peak is not true peak. PCM24 cannot contain NaN."""
    c.validate_wav(path, frames=frames)
    peak = clipped = 0
    with wave.open(str(path), "rb") as stream:
        count = stream.getnframes()
        rate = stream.getframerate()
        channels = stream.getnchannels()
        while block := stream.readframes(8192):
            for offset in range(0, len(block), 3):
                value = int.from_bytes(block[offset:offset + 3], "little", signed=True)
                peak = max(peak, abs(value))
                clipped += value in (-8388608, 8388607)
    return dict(frames=count, duration_seconds=count / rate, sample_rate=rate,
                channels=channels, sample_peak_dbfs=20 * math.log10(peak / 8388608) if peak else None,
                clipped_samples=clipped, nan_samples=0, true_peak_dbtp=None,
                lufs=None, method="PCM24 sample scan")


def _json(path):
    return c.read_manifest(path)


def _write_new(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def _gate(state, reasons):
    return {"status": state, "reasons": reasons}


def mastering_analyzer(worker_python, engine_root):
    """Reuse the existing mastering_engine analyzer in an explicitly configured worker."""
    worker_python = Path(worker_python).resolve(strict=True)
    engine_root = Path(engine_root).resolve(strict=True)
    if not worker_python.is_file() or not (engine_root / "mastering_engine" / "analysis.py").is_file():
        raise ValueError("mastering analysis worker/checkout unavailable")
    script = ("import dataclasses,json,sys; from mastering_engine import analysis; "
              "print(json.dumps(dataclasses.asdict(analysis.analyze(sys.argv[1])), allow_nan=False))")
    def analyze(path):
        process = subprocess.run([str(worker_python), "-c", script, str(Path(path).resolve(strict=True))],
                                 cwd=engine_root, capture_output=True, text=True,
                                 encoding="utf-8", timeout=600, check=True)
        raw = json.loads(process.stdout.strip().splitlines()[-1])
        result = {}
        for source, target in (("integrated_lufs", "lufs"), ("true_peak_dbtp", "true_peak_dbtp"),
                               ("loudness_range_lu", "lra"), ("stereo_correlation", "stereo_correlation")):
            value = raw.get(source)
            result[target] = value if type(value) in (int, float) and math.isfinite(value) else None
        result["measurement_method"] = "mastering_engine.analysis.analyze (worker)"
        return result
    return analyze


def inspect_run(root, analyzer=None):
    """Audit immutable run inputs, not perceived musical quality."""
    root = Path(root)
    errors, missing, technical = [], [], {}
    manifests = {}
    for name in ("brief", "plan", "assets", "stems", "mix_report"):
        try:
            data = _json(c.safe_path(root, name + ".json"))
            kwargs = {}
            if name in ("assets", "stems"):
                kwargs = {"plan": manifests.get("plan"), "root": root}
            c.validate_manifest(name, data, **kwargs)
            manifests[name] = data
        except (ValueError, OSError) as exc:
            errors.append(f"{name}: {exc}")
    plan = manifests.get("plan")
    frames = c.expected_frames(plan) if plan else None
    technical["expected_frames"] = frames
    technical["planned_bpm"] = plan["bpm"] if plan else None
    technical["measured_bpm"] = None
    technical["beat_drift_samples"] = None
    technical["planned_bar_samples"] = [
        c.tick_to_sample(i * 3840, plan["bpm"]) for i in range(plan["total_bars"] + 1)
    ] if plan else None
    for name in ("mix", "master"):
        try:
            technical[name] = measure_wav(c.safe_path(root, name + ".wav"), frames)
            if analyzer is not None:
                try:
                    measured = analyzer(c.safe_path(root, name + ".wav"))
                    for metric in ("lufs", "true_peak_dbtp", "lra", "stereo_correlation"):
                        value = measured.get(metric)
                        technical[name][metric] = value if type(value) in (int, float) and math.isfinite(value) else None
                    technical[name]["measurement_method"] = measured.get("measurement_method")
                except (ValueError, OSError, subprocess.SubprocessError, KeyError, IndexError) as exc:
                    missing.append(name + ": external measurement unavailable (" + type(exc).__name__ + ")")
            if technical[name]["clipped_samples"]:
                errors.append(name + ": clipping")
        except (ValueError, OSError) as exc:
            errors.append(f"{name}: {exc}")
            technical[name] = None
    master = technical.get("master") or {}
    if master.get("true_peak_dbtp") is not None and master.get("measurement_method") and master["true_peak_dbtp"] > -1:
        errors.append("master exceeds -1 dBTP")
    if any((technical.get(name) or {}).get(metric) is None or
           not (technical.get(name) or {}).get("measurement_method")
           for name in ("mix", "master") for metric in ("true_peak_dbtp", "lufs")):
        missing.append("true peak and LUFS with measurement method")
    for asset in manifests.get("assets", {}).get("assets", []):
        if asset.get("error") is not None:
            errors.append("asset error: " + asset["id"])
        if asset.get("source", {}).get("license") in (None, "", "unknown"):
            missing.append("asset license: " + asset["id"])
    brief = manifests.get("brief", {})
    lyrics = brief.get("lyrics")
    speech = []
    if plan:
        requests = {r["id"]: r for r in plan["asset_requests"] if r["kind"] == "speech"}
        events = sorted((e for t in plan["tracks"] for e in t["events"]
                         if e.get("asset_id") in requests), key=lambda e: e["tick"])
        speech = [requests[e["asset_id"]]["text"] for e in events]
    normalize = lambda s: " ".join(s.split())
    technical["planned_text_complete"] = (normalize(" ".join(speech)) == normalize(lyrics)
                                          if lyrics and brief.get("vocal_mode") == "spoken" and plan else None)
    if technical["planned_text_complete"] is False:
        errors.append("planned spoken text differs from brief")
    missing += ["measured BPM/beat drift",
                "spoken audio transcription and absence of unintended singing/cuts",
                "local inventory/reference manifest", "real B1/B2 listening",
                "regeneration/cancel and Ableton roundtrip evidence"]
    report = dict(schema_version=1, technical={**technical, "errors": errors},
                  music={"score": None}, production={"score": None},
                  gates={"G0": _gate("open", ["local inventory and reference evidence required"]),
                         "G1": _gate("failed" if errors else "open", ["real groove, three seeds and user verdict required"]),
                         "G2": _gate("failed" if errors else "open", ["real full-song and roundtrip evidence required"]),
                         "G3": _gate("open", ["real blind B2 results and G2 required"])},
                  missing=missing, provenance={"method": "contracts + PCM24 sample scan",
                  "audio_quality_measured": False, "seed": plan["seed"] if plan else None},
                  listening={"blind_pairs": [], "results": []})
    report["next_improvements"] = (errors + ["Measure true peak/LUFS with existing mastering analysis",
                                  "Collect real blind listening feedback on groove and production"])[:2]
    c.validate_report(report)
    return report


def allocate_pair(path, pair_id, candidate, reference, seed, *, brief_id, repetition,
                  candidate_lufs, reference_lufs):
    """Persist operator-only mapping. Never send mapping or original filenames to listener."""
    if not all(isinstance(x, str) and x for x in (pair_id, candidate, reference, seed, brief_id)):
        raise ValueError("missing pair identity")
    if candidate == reference or type(repetition) is not int or repetition < 1:
        raise ValueError("invalid comparison")
    for value in (candidate_lufs, reference_lufs):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("measured loudness required")
    target = min(candidate_lufs, reference_lufs)
    order = [{"kind": "candidate", "id": candidate, "gain_db": target - candidate_lufs},
             {"kind": "reference", "id": reference, "gain_db": target - reference_lufs}]
    random.Random(int.from_bytes(hashlib.sha256((seed + "|" + pair_id).encode()).digest(), "big")).shuffle(order)
    mapping = dict(schema_version=1, pair_id=pair_id, brief_id=brief_id, repetition=repetition,
                   assignment=dict(zip(("A", "B"), order)), target_lufs=target)
    _write_new(path, mapping)
    return {"pair_id": pair_id, "labels": ["A", "B"]}


def reveal_pair(mapping, vote, matched_lufs):
    """Reveal only a complete locked vote with measured matched playback levels."""
    if vote.get("pair_id") != mapping["pair_id"] or vote.get("locked") is not True:
        raise ValueError("vote not locked or wrong pair")
    if set(matched_lufs) != {"A", "B"} or any(type(v) not in (int, float) or not math.isfinite(v)
                                               for v in matched_lufs.values()):
        raise ValueError("missing measured playback loudness")
    if abs(matched_lufs["A"] - matched_lufs["B"]) > 0.5:
        raise ValueError("playback not loudness matched")
    assignment = mapping["assignment"]
    if set(assignment) != {"A", "B"} or {v["kind"] for v in assignment.values()} != {"candidate", "reference"}:
        raise ValueError("invalid assignment")
    label = next(k for k, v in assignment.items() if v["kind"] == "candidate")
    preference = vote.get("preference")
    if preference not in ("A", "B", "tie"):
        raise ValueError("invalid preference")
    for axis in ("music", "production"):
        if type(vote.get(axis)) is not int or not 1 <= vote[axis] <= 5:
            raise ValueError("candidate rating must be 1..5")
    comment = vote.get("comment")
    if comment is not None and not isinstance(comment, str):
        raise ValueError("invalid comment")
    return {"pair_id": mapping["pair_id"], "brief_id": mapping["brief_id"],
            "repetition": mapping["repetition"], "candidate_id": assignment[label]["id"],
            "reference_id": assignment["B" if label == "A" else "A"]["id"],
            "preference": "tie" if preference == "tie" else "candidate" if preference == label else "reference",
            "music": vote["music"], "production": vote["production"], "comment": comment}


def summarize_b2(results):
    """Threshold audit only; not a G3 release. Real provenance and G2 are external."""
    ids = [r["pair_id"] for r in results]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate pair")
    groups = {}
    for r in results:
        groups.setdefault(r["brief_id"], []).append(r)
    valid_design = len(groups) >= 3
    for group in groups.values():
        candidates = {r["candidate_id"] for r in group}
        valid_design &= len(candidates) >= 2 and all(
            len({r["repetition"] for r in group if r["candidate_id"] == candidate}) >= 2
            for candidate in candidates)
    wins = sum(r["preference"] in ("candidate", "tie") for r in results)
    music = statistics.median(r["music"] for r in results) if results else None
    production = statistics.median(r["production"] for r in results) if results else None
    no_clear_loss = all(any(r["preference"] != "reference" for r in group) for group in groups.values())
    return dict(n=len(results), candidate_or_tie=wins, median_music=music, median_production=production,
                threshold_met=bool(valid_design and len(results) >= 12 and wins * 12 >= len(results) * 8
                                   and music >= 4 and production >= 4 and no_clear_loss),
                release=False)


def benchmark(manifest, analyzer=None):
    """Manifest lists relative run directories. Results remain local."""
    manifest = Path(manifest)
    data = _json(manifest)
    if data.get("schema_version") != 1 or not isinstance(data.get("runs"), list):
        raise ValueError("invalid benchmark manifest")
    return {"schema_version": 1, "runs": [inspect_run(c.safe_path(manifest.parent, run), analyzer)
                                        for run in data["runs"]]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--analysis-python", type=Path, help="Existing isolated audio worker Python")
    parser.add_argument("--analysis-root", type=Path, help="Existing mastering_engine checkout")
    args = parser.parse_args(argv)
    if bool(args.analysis_python) != bool(args.analysis_root):
        parser.error("both analysis options are required together")
    analyzer = mastering_analyzer(args.analysis_python, args.analysis_root) if args.analysis_python else None
    result = benchmark(args.manifest, analyzer)
    if args.output:
        _write_new(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return int(any(r["technical"]["errors"] for r in result["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
