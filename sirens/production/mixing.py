"""Production mixing entry points; never write to Live."""
from __future__ import annotations

import json
from urllib.request import urlopen

CHAIN_ROLES = ("vocals", "drums", "bass", "synths", "bus", "plate", "delay", "master")


def fetch_chain(role: str, *, timeout: float = 5.0, opener=urlopen) -> dict:
    """Read local SecondRoom chain data, not a Live application receipt."""
    if role not in CHAIN_ROLES:
        raise ValueError("unknown chain role")
    with opener("http://127.0.0.1:8099/api/chains/" + role, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("invalid chain response")
    return result


import math
import shutil
import subprocess
import tempfile
from pathlib import Path


def _number(value, lo, hi, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError("invalid " + name)
    return value


def _settings(plan, stems):
    tracks = {track["id"]: track for track in plan["tracks"]}
    overrides = plan["mix"].get("tracks", {})
    if not isinstance(overrides, dict) or set(overrides) - set(tracks):
        raise ValueError("unknown track override")
    result = []
    for stem in stems["stems"]:
        name, role = stem["track_id"], stem["role"].lower()
        if role != tracks[name]["role"].lower():
            raise ValueError("stem role mismatch")
        kick = name.lower().startswith("kick") or role == "kick"
        sub = role in ("bass", "sub") or name.lower().startswith("sub")
        defaults = dict(gain_db=-6 if kick or sub else -9, pan=0,
                        highpass_hz=20 if kick or sub else 80,
                        eq_hz=300, eq_db=0, reverb_send=0, delay_send=0)
        if role in ("spoken", "vocals", "voice", "synths", "synth"):
            defaults.update(reverb_send=.08, delay_send=.03)
        custom = overrides.get(name, {})
        if not isinstance(custom, dict) or set(custom) - set(defaults):
            raise ValueError("invalid track settings")
        defaults.update(custom)
        for key, bounds in dict(gain_db=(-60, 12), pan=(-1, 1),
                                highpass_hz=(10, 2000), eq_hz=(20, 20000),
                                eq_db=(-12, 12), reverb_send=(0, .5),
                                delay_send=(0, .5)).items():
            _number(defaults[key], *bounds, key)
        result.append(dict(track_id=name, kick=kick, sub=sub, **defaults))
    return result


def _gain(peak, desired, ceiling):
    return min(desired, ceiling - .10 - peak) if peak is not None else min(desired, 0)


def mix(plan, stems, root, cancelled=lambda: None, *, ffmpeg=None,
        amm_python=None, amm_root=None, reference=None):
    """Runner adapter. Trusted local configuration supplies binaries and reference.

    Writes new outputs only; revise in a new run, never modify an earlier run.
    AMM Mode C is optional and only called for an explicit target loudness.
    """
    from .contracts import (safe_path, validate_plan, validate_stems, validate_wav,
                            validate_mix_report, sha256_file)
    from workers.production_mix import ffmpeg_mix as audio

    root = Path(root).resolve(strict=True)
    validate_plan(plan)
    validate_stems(stems, plan=plan, root=root)
    if not stems["stems"]:
        raise ValueError("no stems")
    frames = stems["frames"]
    config = plan["mix"]
    ceiling = min(-1, _number(config["ceiling_dbtp"], -9, 0, "ceiling_dbtp"))
    target = config["target_lufs"]
    if target is not None:
        _number(target, -35, -5, "target_lufs")
    settings = _settings(plan, stems)
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not installed")
    if (amm_python is None) != (amm_root is None):
        raise ValueError("AMM requires both interpreter and checkout")
    files = ["dry.wav", "mix.wav", "master.wav", "mix_report.json"]
    if reference is not None:
        files += ["comparison_master.wav", "comparison_reference.wav"]
    outputs = {name: safe_path(root, name) for name in files}
    if any(path.exists() for path in outputs.values()):
        raise FileExistsError("mix outputs already exist; create a revision run")
    paths = [safe_path(root, s["file"]) for s in stems["stems"]]
    warnings = []
    report = dict(schema_version=1, warnings=warnings, settings=settings,
                  target_lufs=target, ceiling_dbtp=ceiling, headroom_dbtp=-6,
                  effects=dict(sidechain=dict(ratio=2, attack_ms=5, release_ms=110,
                                               threshold_linear=.06),
                               reverb="short filtered multitap return",
                               delay_ms=[240, 480], sub_crossover_hz=120, fade_ms=5),
                  dependencies=dict(ffmpeg=audio.run(exe, ["-version"]).splitlines()[0]
                                    if False else subprocess.check_output(
                                        [exe, "-version"], text=True, timeout=10).splitlines()[0]),
                  source_stems=[dict(track_id=s["track_id"], sha256=s["sha256"])
                                for s in stems["stems"]],
                  listening=None)
    with tempfile.TemporaryDirectory(prefix=".mix-", dir=root) as tmp:
        work = Path(tmp)
        for name, dry in (("dry", True), ("mix", False)):
            cancelled()
            raw = work / (name + "-float.wav")
            audio.render_graph(exe, paths, settings, frames, raw, dry=dry)
            peak = audio.loudness(exe, raw)["true_peak_dbtp"]
            gain = _gain(peak, 0, -6)
            audio.encode(exe, raw, work / (name + ".wav"), frames, gain)
            report[name + "_gain_db"] = gain
        cancelled()
        pre = audio.measure(exe, work / "mix.wav")
        master_source = work / "mix.wav"
        method = "ffmpeg static peak-constrained gain"
        if amm_python is not None and target is not None:
            candidate = work / "amm.wav"
            completed = subprocess.run(
                [str(Path(amm_python).resolve(strict=True)), "-m", "mastering_engine.cli",
                 str(master_source), "--profile", "custom", "--target-lufs", str(target),
                 "--true-peak", str(ceiling), "--output-format", "wav",
                 "--out", str(candidate)], cwd=Path(amm_root).resolve(strict=True),
                capture_output=True, text=True, timeout=600)
            if completed.returncode:
                raise RuntimeError("AMM mastering failed: " + completed.stderr[-1500:])
            validate_wav(candidate, channels=2, frames=frames)
            master_source = candidate
            method = "AMM mastering_engine.cli (Mode C), ffmpeg safety gain"
            report["dependencies"]["amm"] = "configured local checkout"
            warnings.append("AMM gain reduction not independently quantified; listen before release")
        source = audio.loudness(exe, master_source)
        desired = (target - source["lufs"] if target is not None and
                   source["lufs"] is not None and master_source == work / "mix.wav" else 0)
        gain = _gain(source["true_peak_dbtp"], desired, ceiling)
        if desired - gain > 3:
            warnings.append("Target would require >3 dB peak reduction; preserved dynamics instead")
        audio.encode(exe, master_source, work / "master.wav", frames, gain)
        report["mastering"] = dict(method=method, gain_db=gain,
                                  requested_gain_db=desired, compression_applied_by_sirens=False)
        report["premaster"] = pre
        report["dry"] = audio.measure(exe, work / "dry.wav")
        report["measured"] = audio.measure(exe, work / "master.wav")
        measured = report["measured"]
        if target is not None and (measured["lufs"] is None or
                                   abs(measured["lufs"] - target) > .5):
            warnings.append("Target loudness not reached; no forced compression")
        for name in ("dry", "premaster", "measured"):
            metrics = report[name]
            limit = ceiling if name == "measured" else -6
            if metrics["clipped_samples"] or (metrics["true_peak_dbtp"] is not None and
                                              metrics["true_peak_dbtp"] > limit):
                raise RuntimeError("unsafe output peak: " + name)
        if reference is not None:
            cancelled()
            ref = Path(reference).resolve(strict=True)
            # Reference is an explicitly supplied local analysis input, never mixed into song.
            ref_frames = frames
            with __import__("wave").open(str(ref), "rb") as wav:
                ref_frames = round(wav.getnframes() * 48000 / wav.getframerate())
            normalized = work / "reference-float.wav"
            audio.run(exe, ["-i", ref, "-ar", 48000, "-ac", 2,
                            "-c:a", "pcm_f32le", "-n", normalized])
            ref_metrics = audio.loudness(exe, normalized)
            if measured["lufs"] is None or ref_metrics["lufs"] is None:
                raise ValueError("cannot loudness-match silence")
            common = min(measured["lufs"], ref_metrics["lufs"])
            audio.encode(exe, work / "master.wav", work / "comparison_master.wav",
                         frames, common - measured["lufs"])
            audio.encode(exe, normalized, work / "comparison_reference.wav",
                         ref_frames, common - ref_metrics["lufs"])
            report["comparison"] = dict(master=audio.loudness(exe, work / "comparison_master.wav"),
                                        reference=audio.loudness(exe, work / "comparison_reference.wav"),
                                        reference_sha256=sha256_file(ref), listening=None)
        for name in ("mix.wav", "master.wav", "dry.wav"):
            validate_wav(work / name, frames=frames, channels=2)
        for stem, path in zip(stems["stems"], paths):
            if sha256_file(path) != stem["sha256"]:
                raise RuntimeError("stem changed during mix")
        validate_mix_report(report)
        (work / "mix_report.json").write_text(json.dumps(report, indent=2, allow_nan=False),
                                             encoding="utf-8")
        cancelled()
        for name, path in outputs.items():
            # Exclusive destination creation also protects against accidental overwrite.
            with path.open("xb") as out, (work / name).open("rb") as src:
                shutil.copyfileobj(src, out)
    return report


def analyze_return(path, *, ffmpeg=None):
    """Read a confirmed stereo return, never master it again or invent stems."""
    from .contracts import validate_wav
    from workers.production_mix import ffmpeg_mix as audio
    validate_wav(path, channels=2)
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not installed")
    return dict(schema_version=1, variant="ableton_return", stems=None,
                measured=audio.measure(exe, Path(path)), warnings=[])
