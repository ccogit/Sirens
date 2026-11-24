"""Rekonstruktion, Leakage und Alignment aus PCM-Referenzen; keine Downloads."""
import argparse
import array
import datetime
import json
import math
from pathlib import Path
import sys
import wave

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write


def pcm(path):
    with wave.open(str(path), "rb") as f:
        rate, channels, width, frames = f.getframerate(), f.getnchannels(), f.getsampwidth(), f.getnframes()
        raw = f.readframes(frames)
    if width not in (2, 3) or len(raw) != frames * channels * width:
        raise ValueError("PCM16/24 erwartet")
    if width == 2:
        values = array.array("h", raw)
        if sys.byteorder != "little":
            values.byteswap()
        samples = [x / 32768 for x in values]
    else:
        samples = [int.from_bytes(raw[i:i+3], "little", signed=True) / 8388608
                   for i in range(0, len(raw), 3)]
    return (rate, channels, frames), samples


def quality(original, vocals, instrumental, reference_vocals, reference_instrumental):
    tracks = [pcm(p) for p in (original, vocals, instrumental, reference_vocals, reference_instrumental)]
    if any(t[0] != tracks[0][0] for t in tracks):
        raise ValueError("Samplezahl, Rate oder Kanäle stimmen nicht überein")
    _, channels, frames = tracks[0][0]
    x, v, i, rv, ri = [t[1] for t in tracks]
    def rms(values):
        return math.sqrt(sum(z*z for z in values) / max(1, len(x)))
    def projection(track, ref):
        denom = sum(z*z for z in ref)
        return sum(a*b for a,b in zip(track, ref)) / denom if denom else None
    # Begrenzte Lag-Suche auf den ersten 4096 Frames; Referenz muss dort Signal tragen.
    def lag(track, ref):
        n = min(frames, 4096)
        def score(offset):
            lo, hi = max(0, -offset), min(n, n-offset)
            a = track[(lo+offset)*channels:(hi+offset)*channels]
            b = ref[lo*channels:hi*channels]
            energy = math.sqrt(sum(z*z for z in a)*sum(z*z for z in b))
            return sum(p*q for p,q in zip(a,b))/energy if energy else -2
        scores = [(score(k), k) for k in range(-64, 65)]
        best = max(scores, key=lambda item: (item[0], -abs(item[1])))
        return best[1] if best[0] > 0 else None
    return {"reconstruction_rms": rms(a-b-c for a,b,c in zip(x,v,i)),
            "vocals_error_rms": rms(a-b for a,b in zip(v,rv)),
            "instrumental_error_rms": rms(a-b for a,b in zip(i,ri)),
            "instrumental_into_vocals_projection": projection(v,ri),
            "vocals_into_instrumental_projection": projection(i,rv),
            "vocals_lag_frames": lag(v,rv), "instrumental_lag_frames": lag(i,ri)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "vocals", "instrumental", "reference_vocals", "reference_instrumental", "report"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    metrics = quality(a.original, a.vocals, a.instrumental, a.reference_vocals, a.reference_instrumental)
    write(a.report, {"wp":"WP08","kandidat":"roformer","gate":"nicht_gemessen","modus":"offline",
          "zeitpunkt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "befehl":"python -m benchmarks.separation.quality ORIGINAL VOCALS INSTRUMENTAL REF_V REF_I REPORT",
          "rechner":collect(),"messwerte":{phase:dict.fromkeys(METRICS) for phase in ("kalt","warm")},
          "notizen":["Qualitätswerte: " + json.dumps(metrics, allow_nan=False),
                     "Leakage-Projektion nur für orthogonale Referenzsignale sinnvoll; Lag-Suche ±64 Frames."]})


if __name__ == "__main__":
    main()
