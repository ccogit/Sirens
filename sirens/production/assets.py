"""Offline production asset validation. No audio/model imports in Sirens."""
from __future__ import annotations

import math
import re
import wave
from pathlib import Path


class AssetError(ValueError):
    """An asset cannot be used without correction or explicit approval."""


def inspect_wav(path, *, duration_seconds=None, loop=False, speech=False):
    """Inspect PCM24, report technical measurements, never infer musical quality."""
    from .contracts import validate_wav, sha256_file
    validate_wav(path)
    with wave.open(str(path), "rb") as wav:
        channels, frames = wav.getnchannels(), wav.getnframes()
        rate = wav.getframerate()
        peak = energy = clips = 0
        first = last = None
        while chunk := wav.readframes(8192):
            for i in range(0, len(chunk), channels * 3):
                frame = tuple(int.from_bytes(chunk[j:j+3], "little", signed=True)
                              for j in range(i, i + channels * 3, 3))
                if first is None:
                    first = frame
                last = frame
                for sample in frame:
                    peak = max(peak, abs(sample))
                    energy += sample * sample
                    clips += sample in (-8388608, 8388607)
    if not peak or clips:
        raise AssetError("silent or clipped asset")
    duration = frames / rate
    if duration_seconds is not None:
        if not math.isfinite(duration_seconds) or duration_seconds <= 0:
            raise AssetError("invalid requested duration")
        if speech and duration > duration_seconds + 1 / rate:
            raise AssetError("spoken cue exceeds slot; replan, never truncate text")
        if loop and abs(duration - duration_seconds) > 1 / rate:
            raise AssetError("loop length differs from requested length")
    seam = max(abs(a-b) for a,b in zip(first,last)) / 8388608
    if loop and seam > 0.02:
        raise AssetError("loop boundary discontinuity")
    return dict(sample_rate=rate, channels=channels, frames=frames,
                sha256=sha256_file(path), measured=dict(
                    bpm=None, key=None, duration_seconds=duration,
                    peak_dbfs=20 * math.log10(peak / 8388608),
                    rms_dbfs=10 * math.log10(energy / (frames * channels) / 8388608**2),
                    clipped_samples=clips, seam_delta=seam, listening=None))


def approved_source(source, *, commercial=False):
    """Require explicit usage metadata; unknown rights never pass commercial gate."""
    for field in ("backend", "revision", "license", "use"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise AssetError("missing source " + field)
    if source["use"] not in {"production", "commercial", "test-only"}:
        raise AssetError("source is not cleared for production")
    if source["license"].lower() == "unknown":
        raise AssetError("unknown license")
    if commercial and source["use"] != "commercial":
        raise AssetError("commercial use is not approved")
    return source


def asset_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise AssetError("unsafe asset ID")
    return value
