"""Explizite lokale WP13-Hörproben und Messwerte; kein Gate-Entscheid."""
import argparse
import datetime
import math
import sys
import threading
import time
from pathlib import Path

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write, markdown
from workers.sam_audio.adapter import separate, shape
from workers.sam_audio.cache import validate_assets
from workers.sam_audio.backend import SamBackend

PROMPTS = ("lead vocals", "kick drum", "bass guitar", "hi-hat cymbals", "piano")


def metrics(times, durations, peaks):
    ordered = sorted(times)
    def percentile(p):
        return ordered[max(0, math.ceil(p * len(ordered)) - 1)]
    return dict(p50_ms=percentile(.50), p95_ms=percentile(.95),
                p99_ms=percentile(.99), peak_vram_mib=max(peaks),
                rtf=sum(times) / 1000 / sum(durations), underruns=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--tracks", required=True, nargs=5, type=Path,
                        help="Fünf passende lokale PCM16-Stereo-WAVs (in Prompt-Reihenfolge)")
    parser.add_argument("--out", required=True, type=Path,
                        help="Neuer Ausgabeordner außerhalb des Repos")
    args = parser.parse_args()
    out = args.out.resolve()
    root = Path(__file__).resolve().parents[2]
    if out == root or root in out.parents:
        parser.error("Hörproben außerhalb des Repos speichern")
    tracks = [p.resolve() for p in args.tracks]
    durations = []
    for track in tracks:
        rate, frames = shape(track)
        durations.append(frames / rate)
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    model = SamBackend(args.receipt.resolve())
    load_ms = (time.perf_counter() - start) * 1000
    torch = model.torch
    times, peaks, notes = [], [], []
    for i, (prompt, track) in enumerate(zip(PROMPTS, tracks), 1):
        dest = out / str(i)
        dest.mkdir()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        start = time.perf_counter()
        separate(model, track, dest, {"prompt": prompt}, threading.Event())
        torch.cuda.synchronize()
        ms = (time.perf_counter() - start) * 1000
        peak = torch.cuda.max_memory_allocated() / 1024**2
        if not validate_assets(track, dest):
            raise RuntimeError("Rekonstruktion fehlgeschlagen")
        times.append(ms)
        peaks.append(peak)
        notes.append(f"{i}: {prompt}; {durations[i-1]:.3f} s; {ms:.1f} ms; "
                     f"{peak:.1f} MiB; PCM16-Summe exakt. Hörurteil: offen.")
    cold = metrics([times[0]+load_ms], durations[:1], peaks[:1])
    cold["peak_vram_mib"] = None  # Ladepeak nicht erfasst
    data = dict(wp="WP13", kandidat="sam-audio-small", gate="nicht_gemessen",
                modus="offline", zeitpunkt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                befehl="python -m benchmarks.semantic.messen --receipt <Receipt> --tracks <5 WAVs> --out <extern>",
                rechner=collect(), messwerte={"kalt": cold, "warm": metrics(times[1:], durations[1:], peaks[1:])},
                notizen=notes + ["Kalt inklusive Laden; Warm: vier unterschiedliche Tracks.",
                                 "Peak: Torch allocated, nicht gesamte GPU; keine Streaming-Messung.",
                                 "Hörprüfung und G1/G3-Entscheid ausschließlich Koordinator."])
    write(out / "result.json", data)
    (out / "result.md").write_text(markdown(data), encoding="utf-8")
    (out / "hoerbericht.md").write_text(
        "# WP13 Hörprüfung\n\n"
        + "\n".join(f"- {i}: {p}: Isolation / Leakage / Artefakte / Segmentgrenzen / Alignment: offen"
                    for i, p in enumerate(PROMPTS, 1))
        + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
