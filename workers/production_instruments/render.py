"""Isolated adapter to AMM/WB's existing VST3 render_vst3_instrument.

Run only with the configured worker interpreter and locally installed AMM.
No dependency installs, network, Live calls or fallback synthesis.
"""
import hashlib
import json
import math
import sys
import wave
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path


def position(tick, bpm):
    return round(Fraction(tick * 48000 * 60, 960) / Fraction(str(bpm)))


def resolve_bundle(path, *, windows):
    """Translate a Windows x64 VST3 bundle to the file pedalboard scans."""
    path = Path(path)
    if windows and path.suffix.lower() == ".vst3" and path.is_dir():
        path = path / "Contents" / "x86_64-win" / path.name
        if not path.is_file():
            raise ValueError("Plugin bundle incomplete; set instrument.plugin to an installed x64 VST3.")
    if not path.exists():
        raise ValueError("Plugin missing; set instrument.plugin to an existing VST3.")
    return path


def verified_preset(binding):
    if (not isinstance(binding, dict) or not isinstance(binding.get("path"), str)
            or not Path(binding["path"]).is_absolute()):
        raise ValueError("Preset missing; configure instrument.preset_file with an absolute path and sha256.")
    path = Path(binding["path"])
    try:
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise ValueError("Preset missing; configure instrument.preset_file with an existing file and sha256.") from exc
    if actual != binding.get("sha256"):
        raise ValueError("Preset hash mismatch; update instrument.preset_file with its verified path and sha256.")
    return path


@contextmanager
def local_bindings(instrument, plugins, factory_presets, *, windows):
    """Adapt only the two AMM lookup functions in this disposable process.

    Keep plugin_control.load, preset decoding, state/parameter application,
    warm-up and rendering in AMM. Never modify WB files or its data directory.
    """
    original_plugin = plugins.plugin_path
    original_preset = factory_presets.preset_file
    entry = dict(instrument)
    ref = entry.get("plugin")
    if not isinstance(ref, str) or not ref:
        raise ValueError("Plugin missing; set instrument.plugin in the local patch.")
    plugin_ref = ref.partition("#")[0]
    try:
        path = Path(plugin_ref)
        if not path.is_absolute():
            path = original_plugin(plugin_ref)
        resolved = resolve_bundle(path, windows=windows)
    except (OSError, ValueError) as exc:
        raise ValueError("Plugin missing or invalid; set instrument.plugin to an installed VST3.") from exc
    binding = entry.get("preset_file")
    if binding is not None:
        preset = verified_preset(binding)
        # AMM applies a preset only when the identifier is truthy.
        entry["preset"] = entry.get("preset") or "sirens-explicit-file"
    elif entry.get("preset"):
        try:
            preset = original_preset(ref, entry["preset"])
            if not Path(preset).is_file():
                raise FileNotFoundError(preset)
        except Exception as exc:
            raise ValueError("Preset missing; configure instrument.preset_file with its verified path and sha256.") from exc
    elif not entry.get("state"):
        raise ValueError("Preset missing; configure a verified preset_file or state in the local patch.")
    else:
        preset = None

    def plugin_path(rel):
        return resolved if rel == plugin_ref else original_plugin(rel)

    def preset_file(plugin, ident):
        if preset is not None and plugin == ref and ident == entry.get("preset"):
            return preset
        return original_preset(plugin, ident)

    plugins.plugin_path = plugin_path
    factory_presets.preset_file = preset_file
    try:
        yield entry
    finally:
        plugins.plugin_path = original_plugin
        factory_presets.preset_file = original_preset


def render(request):
    # All non-stdlib dependencies are imported only in this worker.
    sys.path.insert(0, str(Path(request["amm_backend"]).resolve(strict=True)))
    try:
        import pedalboard  # verify the one supported host before loading WB
        import numpy as np
        from app.audio_engine import plugins, factory_presets
        from app.audio_engine.render_instruments import render_vst3_instrument
    except (ImportError, OSError) as exc:
        raise RuntimeError("Instrument host missing or invalid; install the documented AMM/Pedalboard worker requirements.") from exc

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
    with local_bindings(instrument, plugins, factory_presets, windows=sys.platform == "win32") as entry:
        audio = np.asarray(render_vst3_instrument(events, frames, sr, entry), dtype=np.float64)
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
    try:
        render(json.load(sys.stdin))
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
