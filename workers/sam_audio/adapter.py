"""Offline-Adapter: PCM16-Stereo, Textprompt, segmentierte Inferenz."""
import array
import math
import sys
import wave
from pathlib import Path

FILES = ("target.wav", "residual.wav")
RATES = (44100, 48000)
SEGMENT_SECONDS = 15


class Cancelled(Exception):
    pass


def prompt_value(params):
    if not isinstance(params, dict) or set(params) != {"prompt"}:
        raise ValueError("Nur Textprompt erlaubt")
    prompt = params["prompt"]
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 512:
        raise ValueError("Textprompt fehlt oder zu lang")
    if any(ord(c) < 32 or ord(c) == 127 for c in prompt):
        raise ValueError("Steuerzeichen im Prompt")
    return prompt.strip()


def decode(raw):
    data = array.array("h")
    data.frombytes(raw)
    if sys.byteorder != "little":
        data.byteswap()
    return data


def encode(samples):
    data = array.array("h", samples)
    if sys.byteorder != "little":
        data.byteswap()
    return data.tobytes()


def split_sample(original, estimate):
    # Beide Ausgaben bleiben im PCM16-Bereich; keine unabhängige Normalisierung.
    if not math.isfinite(estimate):
        raise ValueError("Nicht endliche Modell-Ausgabe")
    target = round(max(-1.0, min(1.0, estimate)) * 32768)
    target = max(-32768, original - 32767, min(32767, original + 32768, target))
    return target, original - target


def shape(path):
    with wave.open(str(path), "rb") as w:
        if w.getnchannels() != 2 or w.getsampwidth() != 2 or w.getframerate() not in RATES:
            raise ValueError("PCM16-Stereo mit 44,1/48 kHz erforderlich")
        if w.getnframes() <= 0:
            raise ValueError("Leere WAV-Datei")
        return w.getframerate(), w.getnframes()


def separate(model, source, out_dir, params, cancelled, progress=lambda value: None):
    """Nur in serverseitig angelegtem, leerem Ausgabeordner schreiben."""
    prompt = prompt_value(params)
    source, out_dir = Path(source), Path(out_dir)
    if not source.is_absolute() or not out_dir.is_absolute() or not out_dir.is_dir():
        raise ValueError("Serverseitige absolute Pfade erforderlich")
    if out_dir.is_symlink() or any(out_dir.iterdir()) or out_dir.resolve() in source.resolve().parents:
        raise ValueError("Ausgabeordner muss leer und von der Quelle getrennt sein")
    rate, total = shape(source)
    paths = [out_dir / name for name in FILES]
    try:
        with wave.open(str(source), "rb") as inp, wave.open(str(paths[0]), "wb") as a, wave.open(str(paths[1]), "wb") as b:
            for w in (a, b):
                w.setparams((2, 2, rate, 0, "NONE", "not compressed"))
            offset = 0
            while offset < total:
                if cancelled.is_set():
                    raise Cancelled()
                count = min(total - offset, rate * SEGMENT_SECONDS)
                original = decode(inp.readframes(count))
                if len(original) != 2 * count:
                    raise ValueError("Unvollständige Quelle")
                mono = [(original[i] + original[i+1]) / 65536 for i in range(0, len(original), 2)]
                estimate = model.separate(mono, rate, prompt)
                if cancelled.is_set():
                    raise Cancelled()
                if len(estimate) != count:
                    raise ValueError("Abweichende Modell-Länge")
                left, right = [], []
                for i, value in enumerate(estimate):
                    for sample in original[2*i:2*i+2]:
                        t, r = split_sample(sample, value)
                        left.append(t)
                        right.append(r)
                a.writeframesraw(encode(left))
                b.writeframesraw(encode(right))
                offset += count
                progress(offset / total)
        if cancelled.is_set():
            raise Cancelled()
        return list(FILES)
    except BaseException:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
