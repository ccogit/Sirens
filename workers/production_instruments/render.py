"""Isolated adapter to AMM/WB's existing VST3 render_vst3_instrument.

Run only with the configured worker interpreter and locally installed AMM.
No dependency installs, network, Live calls or fallback synthesis.
"""
import json
import math
import sys
import wave
from fractions import Fraction
from pathlib import Path


def position(tick, bpm):
    return round(Fraction(tick * 48000 * 60, 960) / Fraction(str(bpm)))


def render(request):
    # All non-stdlib dependencies are imported only in this worker.
    sys.path.insert(0, str(Path(request["amm_backend"]).resolve(strict=True)))
    import numpy as np
    from app.audio_engine.render_instruments import render_vst3_instrument

    track = request["track"]
    bpm = request["bpm"]
    frames = request["frames"]
    sr = request["sample_rate"]
    if sr != 48000:
        raise ValueError("Expected 48000 Hz")
    events = [(position(e["tick"], bpm)/sr,
               position(e["tick"] + e["duration_ticks"], bpm)/sr,
               e["note"], e["velocity"]) for e in track["events"]]
    # Use the direct VST3 function, not render_instrument_track: that function
    # can silently fall back to a basic synth on some plugin failures.
    instrument = request["patch"]["instrument"]
    if instrument.get("type") != "vst3":
        raise ValueError("Invalid instrument binding")
    lanes = {}
    for point in track["automation"]:
        parameter = point["parameter"]
        if parameter not in {"volume", "gain", "gain_db", "pan", "mute"}:
            raise ValueError("Unsupported WB render automation: " + parameter)
        lanes.setdefault(parameter, []).append((position(point["tick"], bpm), point["value"]))
    audio = np.asarray(render_vst3_instrument(events, frames, sr, instrument), dtype=np.float64)
    if audio.shape != (frames, 2) or not np.isfinite(audio).all():
        raise ValueError("Invalid or nonfinite WB audio")
    indices = np.arange(frames)
    for parameter, points in lanes.items():
        points.sort()
        if len({p[0] for p in points}) != len(points):
            raise ValueError("Duplicate automation sample")
        xs, ys = zip(*points)
        if parameter == "mute":
            curve = np.asarray(ys)[np.maximum(0, np.searchsorted(xs, indices, side="right")-1)]
            audio *= (1-curve)[:, None]
            continue
        curve = np.interp(indices, xs, ys)
        if parameter == "pan":
            audio[:, 0] *= np.minimum(1, 1-curve)
            audio[:, 1] *= np.minimum(1, 1+curve)
        elif parameter == "gain_db":
            audio *= (10 ** (curve/20))[:, None]
        else:
            audio *= curve[:, None]
    if np.max(np.abs(audio), initial=0) >= 1:
        raise ValueError("Render clips; lower local patch gain_db")
    pcm = np.rint(audio * 8388608).astype("<i4")
    if np.max(pcm, initial=0) > 8388607:
        raise ValueError("PCM24 overflow")
    data = pcm.view(np.uint8).reshape(-1, 4)[:, :3].copy().tobytes()
    with wave.open(request["output"], "wb") as wav:
        wav.setparams((2, 3, sr, frames, "NONE", "not compressed"))
        wav.writeframes(data)


if __name__ == "__main__":
    render(json.load(sys.stdin))
