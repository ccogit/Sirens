"""K03: aligned offline stems. No audio/plugin imports in the main process."""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from .contracts import (SAMPLE_RATE, PPQ, expected_frames, tick_to_sample,
                        safe_path, validate_plan, validate_assets, validate_stems)


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        channels, frames = wav.getnchannels(), wav.getnframes()
        if wav.getframerate() != SAMPLE_RATE or wav.getsampwidth() != 3 or channels not in (1, 2):
            raise ValueError("Expected 48 kHz mono/stereo PCM24")
        data = wav.readframes(frames)
    if len(data) != frames * channels * 3:
        raise ValueError("Truncated WAV")
    return channels, data


def write_pcm(path, channels, data):
    if channels not in (1, 2) or len(data) % (channels * 3):
        raise ValueError("Invalid PCM24 data")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(3)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data)


def _sample(data, index):
    return int.from_bytes(data[index:index + 3], "little", signed=True)


def _pcm(value):
    if not -8388608 <= value <= 8388607:
        raise ValueError("PCM24 overflow: reduce gain before render")
    return int(value).to_bytes(3, "little", signed=True)


def peak_dbfs(data):
    peak = max((abs(_sample(data, i)) for i in range(0, len(data), 3)), default=0)
    return 20 * math.log10(peak / 8388608) if peak else None


def mono(data):
    return b"".join(_pcm(round((_sample(data, i) + _sample(data, i+3)) / 2))
                    for i in range(0, len(data), 6))


def _atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        tmp = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def place_assets(track, plan, assets, root):
    """Place complete assets at absolute ticks. Reject truncation and clipping."""
    frames = expected_frames(plan)
    events = track["events"]
    sources = []
    for event in events:
        asset = assets[event["asset_id"]]
        if asset.get("error") is not None:
            raise ValueError("Asset failed: " + event["asset_id"])
        path = safe_path(root, asset["file"])
        if digest(path) != asset["sha256"]:
            raise ValueError("Asset hash mismatch")
        channels, data = read_pcm(path)
        start = tick_to_sample(event["tick"], plan["bpm"])
        end = tick_to_sample(event["tick"] + event["duration_ticks"], plan["bpm"])
        count = len(data) // (channels * 3)
        if count > end - start or start + count > frames:
            raise ValueError("Asset exceeds planned duration: " + event["asset_id"])
        sources.append((start, channels, data))
    channels = max((x[1] for x in sources), default=1)
    output = bytearray(frames * channels * 3)
    for start, source_channels, data in sources:
        if source_channels == 1 and channels == 2:
            data = b"".join(data[i:i+3]*2 for i in range(0, len(data), 3))
        offset = start * channels * 3
        for i in range(0, len(data), 3):
            j = offset + i
            output[j:j+3] = _pcm(_sample(output, j) + _sample(data, i))
    return channels, output


def sidechain(plan, path):
    """Sample-aligned, 10 ms rectangular kick trigger, not a rendered instrument."""
    frames = expected_frames(plan)
    data = bytearray(frames * 3)
    on = _pcm(4194304)
    for track in plan["tracks"]:
        if track["patch"] == "tight_kick":
            for event in track["events"]:
                start = tick_to_sample(event["tick"], plan["bpm"])
                count = min(480, frames - start)
                data[start*3:(start+count)*3] = on * count
    write_pcm(path, 1, data)


class WBWorker:
    """Run the existing AMM VST3 renderer in an operator-configured worker venv.

    config is local trusted configuration, never read from a song plan.
    """
    name = "amm_wb_vst3"

    def __init__(self, python, amm_backend, revision):
        self.python = str(Path(python).resolve(strict=True))
        self.amm_backend = str(Path(amm_backend).resolve(strict=True))
        if not revision:
            raise ValueError("Explicit AMM/host revision required")
        self.revision = revision

    def render(self, request, output):
        script = Path(__file__).resolve().parents[2] / "workers/production_instruments/render.py"
        payload = dict(request, amm_backend=self.amm_backend, output=str(output.resolve()))
        result = subprocess.run([self.python, str(script)], input=json.dumps(payload),
                                text=True, capture_output=True, timeout=600, check=False)
        if result.returncode:
            raise RuntimeError("WB worker failed: " + result.stderr[-2000:])


def _patch(patches, track):
    patch = patches.get(track["patch"])
    if not patch:
        raise ValueError("Missing local patch: " + track["patch"])
    for field in ("instrument", "revision", "license", "use"):
        if not patch.get(field):
            raise ValueError("Missing patch metadata: " + field)
    if patch["instrument"].get("type") != "vst3":
        raise ValueError("Only verified WB VST3 instrument bindings are supported")
    if not patch["instrument"].get("preset") and not patch["instrument"].get("state"):
        raise ValueError("Explicit preset or state required")
    return patch


def render_stems(plan, asset_manifest, run_dir, *, patches, backend=None, cache_dir=None):
    """New run only. A backend is mandatory for instruments; no production mock fallback.

    Cache identity includes the complete track, absolute timeline, seed, patch
    metadata and host revision. A hit is accepted only after WAV/hash validation.
    """
    validate_plan(plan)
    root = Path(run_dir).resolve(strict=True)
    validate_assets(asset_manifest, plan=plan, root=root)
    if (root / "stems.json").exists() or (root / "stems").exists():
        raise FileExistsError("Render into a fresh run")
    frames = expected_frames(plan)
    assets = {a["id"]: a for a in asset_manifest["assets"]}
    cache = Path(cache_dir).resolve() if cache_dir is not None else None
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    stems = []
    with tempfile.TemporaryDirectory(dir=root) as stage_name:
        stage = Path(stage_name)
        audio = stage / "stems"
        audio.mkdir()
        for track in plan["tracks"]:
            path = audio / (track["id"] + ".wav")
            if track["backend"] == "asset":
                if track["automation"]:
                    raise ValueError("Asset track automation not supported; delegate to K05")
                channels, data = place_assets(track, plan, assets, root)
                write_pcm(path, channels, data)
                source = {"backend": "asset_placement", "revision": "1", "patch": track["patch"],
                          "seed": plan["seed"], "assets": [assets[e["asset_id"]]["source"] for e in track["events"]]}
            else:
                if backend is None:
                    raise ValueError("No verified instrument backend configured")
                patch = _patch(patches, track)
                request = {"track": track, "patch": patch, "bpm": plan["bpm"],
                           "frames": frames, "seed": plan["seed"], "sample_rate": SAMPLE_RATE}
                key = cache_key({"request": request, "backend": backend.name, "revision": backend.revision})
                cached = cache / (key + ".wav") if cache else None
                meta = cache / (key + ".json") if cache else None
                hit = False
                if cached and cached.is_file() and meta.is_file():
                    try:
                        entry = json.loads(meta.read_text(encoding="utf-8"))
                        c, d = read_pcm(cached)
                        hit = entry["sha256"] == digest(cached) and len(d) == frames * c * 3
                    except (ValueError, OSError, KeyError, wave.Error):
                        hit = False
                if hit:
                    shutil.copyfile(cached, path)
                else:
                    backend.render(request, path)
                channels, data = read_pcm(path)
                if len(data) != frames * channels * 3:
                    raise ValueError("Instrument stem length mismatch")
                if track["patch"] == "mono_sub" and channels == 2:
                    data, channels = mono(data), 1
                    write_pcm(path, channels, data)
                if track["events"] and peak_dbfs(data) is None:
                    raise ValueError("Instrument rendered silence: " + track["id"])
                if cached and not hit:
                    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as f:
                        temp = Path(f.name)
                    try:
                        shutil.copyfile(path, temp)
                        os.replace(temp, cached)
                    finally:
                        temp.unlink(missing_ok=True)
                    _atomic_json(meta, {"sha256": digest(cached)})
                source = {"backend": backend.name, "revision": backend.revision,
                          "patch": track["patch"], "preset_revision": patch["revision"],
                          "seed": plan["seed"], "license": patch["license"], "use": patch["use"],
                          "cache_key": key, "cache_hit": hit}
            peak = peak_dbfs(data)
            if peak is not None and peak >= -0.01:
                raise ValueError("Insufficient headroom: " + track["id"])
            stems.append({"track_id": track["id"], "role": track["role"],
                          "file": "stems/" + path.name, "channels": channels,
                          "sha256": digest(path), "source": source, "peak_dbfs": peak})
        sidechain(plan, stage / "sidechain.wav")
        manifest = {"schema_version": 1, "sample_rate": SAMPLE_RATE, "frames": frames,
                    "stems": stems, "sidechain_file": "stems/sidechain-control.wav"}
        # Use a reserved sidechain filename outside the track namespace.
        manifest["sidechain_file"] = "sidechain-control.wav"
        validate_stems(manifest, plan=plan, root=stage)
        if (root / "sidechain-control.wav").exists():
            raise FileExistsError("Sidechain output already exists")
        os.rename(audio, root / "stems")
        os.rename(stage / "sidechain.wav", root / "sidechain-control.wav")
        _atomic_json(root / "stems.json", manifest)
    return manifest


def render_section(stem_path, plan, section_id, output):
    """Extract an exact section from a full-context rendered/cached stem.

    Preserve incoming notes, automation and effect state; never restart a synth
    in the middle of a held note.
    """
    section = next(s for s in plan["sections"] if s["id"] == section_id)
    start = tick_to_sample(section["start_bar"] * 4 * PPQ, plan["bpm"])
    end = tick_to_sample((section["start_bar"] + section["bars"]) * 4 * PPQ, plan["bpm"])
    channels, data = read_pcm(stem_path)
    if len(data) != expected_frames(plan) * channels * 3:
        raise ValueError("Section source is not a full aligned stem")
    if Path(output).exists():
        raise FileExistsError(output)
    write_pcm(output, channels, data[start*channels*3:end*channels*3])
    return {"start_sample": start, "frames": end-start, "sha256": digest(output)}
