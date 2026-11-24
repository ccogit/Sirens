"""Dateijob nach ADR 0006. Nur der Supervisor übergibt lokale Pfade."""
import math
import struct
import wave
from pathlib import Path

if __package__:
    from .adapter import PAD_TYPES, RATE, validate_job
else:
    from adapter import PAD_TYPES, RATE, validate_job

KEYS = ("unbekannt",) + tuple(
    f"{note} {mode}" for mode in ("major", "minor")
    for note in ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
)


def decode_params(params):
    if not isinstance(params, dict) or set(params) != {
        "pad_type", "bars", "bpm", "key", "seed", "strength", "duration"
    }:
        raise ValueError("Dateijob-Parameter")
    for name, limit in (("pad_type", len(PAD_TYPES)), ("key", len(KEYS))):
        if type(params[name]) is not int or not 0 <= params[name] < limit:
            raise ValueError(name)
    bpm = params["bpm"]
    if type(bpm) not in (float, int) or not math.isfinite(bpm) or not 1 <= bpm <= 1000:
        raise ValueError("BPM")
    prompt = f"electronic music, {bpm:g} BPM"
    if params["key"]:
        prompt += ", " + KEYS[params["key"]]
    return validate_job(dict(type=PAD_TYPES[params["pad_type"]], prompt=prompt,
                             bars=params["bars"], seed=params["seed"],
                             strength=params["strength"], duration=params["duration"]))


def render_file(adapter, payload):
    if set(payload) != {"job_id", "source", "out_dir", "params"}:
        raise ValueError("Dateijob")
    job_id = payload["job_id"]
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Job-ID")
    # Quelle dient nur der Zuordnung; kein Inpainting und kein Lesen der Musik.
    source, out = Path(payload["source"]), Path(payload["out_dir"])
    if (not source.is_absolute() or not source.is_file() or not out.is_absolute()
            or out.name != job_id or not out.is_dir() or out.is_symlink()
            or out.resolve() != out or any(out.iterdir())):
        raise ValueError("Dateijob-Pfad")
    job = decode_params(payload["params"])
    meta = adapter.generate(job)
    path = out / "pad.wav"
    # PCM16-WAV ist mit der vorhandenen Asset-Dekodierung kompatibel.
    try:
        with path.open("xb") as stream, wave.open(stream, "wb") as wav:
            wav.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
            for offset in range(0, meta["frames"], 16384):
                raw = adapter.chunk(offset, min(16384, meta["frames"] - offset))
                pcm = bytearray()
                for (sample,) in struct.iter_unpack("<f", raw):
                    if not math.isfinite(sample):
                        raise ValueError("Audio ungültig")
                    pcm.extend(struct.pack("<h", round(max(-1, min(1, sample)) * 32767)))
                wav.writeframesraw(pcm)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    finally:
        adapter.clip = None
    return {"files": ["pad.wav"]}
