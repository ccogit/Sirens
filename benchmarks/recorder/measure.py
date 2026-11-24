"""30 Minuten PCM24-Diskpfad; synthetische Quelle, kein Browser-Nachweis."""
import argparse
import datetime
import struct
import tempfile
import time
import wave
from pathlib import Path
from benchmarks.baseline import collect
from benchmarks.result import METRICS, write
from sirens.realtime.recordings import Recording


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--scratch", required=True, type=Path)
    p.add_argument("--seconds", type=int, default=1800)
    args = p.parse_args()
    if not 1 <= args.seconds <= 1800:
        p.error("seconds: 1..1800")
    rate = 48000
    frames = args.seconds * rate
    block = struct.pack("<ff", .25, -.25) * 2048
    with tempfile.TemporaryDirectory(dir=args.scratch) as tmp:
        root = Path(tmp)
        rec = Recording(root/"recordings", root/"music", "benchmark", rate)
        start = time.monotonic()
        for offset in range(0, frames, 2048):
            n = min(2048, frames-offset)
            rec.append(block[:n*8], offset)
            delay = start+(offset+n)/rate-time.monotonic()
            if delay > 0:
                time.sleep(delay)
        paths = rec.stop()
        elapsed = time.monotonic()-start
        count = 0
        for path in paths:
            with wave.open(str(path)) as f:
                assert (f.getframerate(), f.getnchannels(), f.getsampwidth()) == (rate,2,3)
                count += f.getnframes()
                assert f.readframes(1) == bytes.fromhex("0000200000e0")
                f.setpos(f.getnframes()-1)
                assert f.readframes(1) == bytes.fromhex("0000200000e0")
        assert count == frames
        size = sum(path.stat().st_size for path in paths)
    metrics = dict.fromkeys(METRICS)
    metrics["rtf"] = elapsed/args.seconds
    write(args.out, {"wp":"WP16","kandidat":"PCM24-Diskpfad",
        "zeitpunkt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "befehl":f"python -m benchmarks.recorder.measure --scratch <scratch> --out <out> --seconds {args.seconds}",
        "gate":"nicht_gemessen","modus":"offline","rechner":collect(),
        "messwerte":{"kalt":metrics,"warm":dict.fromkeys(METRICS)},
        "notizen":[f"Frames={count}; WAV-Bytes={size}; Laufzeit={elapsed:.3f}s",
                   "Synthetischer Diskpfad; Browser/Audio-Gerät/HTTP nicht gemessen."]})


if __name__ == "__main__":
    main()
