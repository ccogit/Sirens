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
import re
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


def _number(value, lo, hi, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError("invalid " + name)
    return value


def _sub_identifier(value):
    """Recognize explicit sub markers, not arbitrary words like 'subtle'."""
    return any(re.fullmatch(r"(?:sub|subbass)[0-9]*", token)
               for token in re.split(r"[_.-]+", value.lower()))


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
        sub = (role == "sub" or _sub_identifier(name)
               or _sub_identifier(tracks[name]["patch"]))
        bass = role == "bass" and not sub and not kick
        defaults = dict(gain_db=-6 if kick or sub else -9, pan=0,
                        highpass_hz=20 if kick or sub else 80,
                        eq_hz=300, eq_db=0, reverb_send=0, delay_send=0,
                        sidechain=sub and not kick)
        if bass:
            # The musical bass has its own EQ and dynamics; leave its
            # upper stereo content intact and reserve kick ducking for
            # the sub unless the plan explicitly enables it.
            defaults.update(highpass_hz=45, eq_hz=250, eq_db=-2)
        if role in ("spoken", "vocals", "voice", "synths", "synth"):
            defaults.update(reverb_send=.08, delay_send=.03)
        custom = overrides.get(name, {})
        if not isinstance(custom, dict) or set(custom) - set(defaults):
            raise ValueError("invalid track settings")
        defaults.update(custom)
        if type(defaults["sidechain"]) is not bool:
            raise ValueError("invalid sidechain")
        for key, bounds in dict(gain_db=(-60, 12), pan=(-1, 1),
                                highpass_hz=(10, 2000), eq_hz=(20, 20000),
                                eq_db=(-12, 12), reverb_send=(0, .5),
                                delay_send=(0, .5)).items():
            _number(defaults[key], *bounds, key)
        result.append(dict(track_id=name, kick=kick, sub=sub, bass=bass, **defaults))
    return result


def _worker_python(worker_python):
    directory = Path(__file__).resolve().parents[2] / "workers" / "production_mix"
    configured = worker_python or os.environ.get("SIRENS_PRODUCTION_MIX_PYTHON")
    default = directory / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Do not resolve a POSIX venv symlink to the system interpreter.
    python = Path(configured or default).absolute()
    if not python.is_file():
        raise RuntimeError("mix worker Python unavailable; configure SIRENS_PRODUCTION_MIX_PYTHON")
    return python, directory / "worker.py"


def _run_worker(work, payload, worker_python, cancelled):
    """Use the file-job pattern: fixed script, UTF-8 JSON, separate process."""
    from .contracts import read_manifest, safe_path

    python, script = _worker_python(worker_python)
    job = work / "job.json"
    job.write_text(json.dumps(dict(schema_version=1, **payload), allow_nan=False),
                   encoding="utf-8")
    cancelled()
    deadline = time.monotonic() + 3600
    with (work / "worker.log").open("wb") as log:
        with subprocess.Popen([str(python), "-X", "utf8", str(script), str(job)],
                              stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                              shell=False) as child:
            try:
                while child.poll() is None:
                    cancelled()
                    if time.monotonic() >= deadline:
                        raise TimeoutError("mix worker timed out")
                    try:
                        child.wait(timeout=.2)
                    except subprocess.TimeoutExpired:
                        pass
            except BaseException:
                # The worker checks this between ffmpeg calls. Wait for the
                # active bounded subprocess before removing its staging files.
                (work / "cancel").touch()
                try:
                    child.wait(timeout=610)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                raise
    cancelled()
    if child.returncode:
        detail = (work / "worker.log").read_text(encoding="utf-8", errors="replace")
        raise RuntimeError("mix worker failed: " + detail[-2000:])
    return read_manifest(safe_path(work, "result.json"))


def mix(plan, stems, root, cancelled=lambda: None, *, ffmpeg=None,
        amm_python=None, amm_root=None, reference=None, worker_python=None):
    """Runner adapter. Trusted local configuration supplies binaries and reference.

    Writes new outputs only; revise in a new run, never modify an earlier run.
    AMM Mode C is optional and only called for an explicit target loudness.
    worker_python is trusted configuration, not a plan parameter; no in-process fallback.
    """
    from .contracts import (safe_path, validate_plan, validate_stems, validate_wav,
                            validate_mix_report, sha256_file)

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
    exe = shutil.which(str(ffmpeg) if ffmpeg is not None else "ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not installed")
    exe = str(Path(exe).resolve(strict=True))
    if (amm_python is None) != (amm_root is None):
        raise ValueError("AMM requires both interpreter and checkout")
    if amm_python is not None:
        amm_python = Path(amm_python).absolute()
        if not amm_python.is_file():
            raise ValueError("AMM interpreter unavailable")
        amm_root = Path(amm_root).resolve(strict=True)
    files = ["dry.wav", "mix.wav", "master.wav", "mix_report.json"]
    if reference is not None:
        files += ["comparison_master.wav", "comparison_reference.wav"]
    outputs = {name: safe_path(root, name) for name in files}
    if any(path.exists() for path in outputs.values()):
        raise FileExistsError("mix outputs already exist; create a revision run")
    paths = [safe_path(root, s["file"]) for s in stems["stems"]]
    with tempfile.TemporaryDirectory(prefix=".mix-", dir=root) as tmp:
        work = Path(tmp)
        report = _run_worker(work, dict(operation="mix", ffmpeg=exe, frames=frames,
                                        settings=settings, ceiling=ceiling, target=target,
                                        stems=stems, paths=[str(path) for path in paths],
                                        amm_python=str(amm_python) if amm_python else None,
                                        amm_root=str(amm_root) if amm_root else None,
                                        reference=str(Path(reference).resolve(strict=True))
                                        if reference is not None else None),
                             worker_python, cancelled)
        for name in ("mix.wav", "master.wav", "dry.wav"):
            validate_wav(safe_path(work, name), frames=frames, channels=2)
        if reference is not None:
            validate_wav(safe_path(work, "comparison_master.wav"), frames=frames, channels=2)
            validate_wav(safe_path(work, "comparison_reference.wav"), channels=2)
        for stem, path in zip(stems["stems"], paths):
            if sha256_file(path) != stem["sha256"]:
                raise RuntimeError("stem changed during mix")
        validate_mix_report(report)
        (work / "mix_report.json").write_text(json.dumps(report, indent=2, allow_nan=False),
                                             encoding="utf-8")
        cancelled()
        for name, path in outputs.items():
            # Exclusive destination creation also protects against accidental overwrite.
            with path.open("xb") as out, safe_path(work, name).open("rb") as src:
                shutil.copyfileobj(src, out)
    return report


def analyze_return(path, *, ffmpeg=None, worker_python=None, cancelled=lambda: None):
    """Analyze an existing stereo return in the worker, without mastering."""
    from .contracts import validate_wav, validate_mix_report
    path = Path(path).resolve(strict=True)
    validate_wav(path, channels=2)
    exe = shutil.which(str(ffmpeg) if ffmpeg is not None else "ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not installed")
    with tempfile.TemporaryDirectory(prefix="sirens-mix-measure-") as tmp:
        report = _run_worker(Path(tmp), dict(operation="measure", path=str(path),
                                             ffmpeg=str(Path(exe).resolve(strict=True))),
                             worker_python, cancelled)
    validate_mix_report(report)
    return report
