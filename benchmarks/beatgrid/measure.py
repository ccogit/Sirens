"""Lokale Track-Referenzen in Sekunden vergleichen, ohne Dateipfade auszugeben."""
import argparse
import datetime
import math
from pathlib import Path
import shlex
import time

from benchmarks import baseline, manifest, result
from sirens.realtime.music_analysis import analyse_file


def measure(manifest_path, output, sample_rate=48000, ffmpeg="ffmpeg"):
    data = manifest.validate(manifest_path)
    notes = ["Offline-CPU; 4/4, erste 360 Sekunden, Referenzzeiten in Sekunden.",
             "Pro Track ein Lauf; keine Warm/Kalt-Perzentile oder GPU-Messung.",
             "Fehler zur nächsten Rasterposition, keine automatische Qualitätsfreigabe."]
    rows = []
    for index, track in enumerate(data["tracks"], 1):
        refs = {}
        for key in ("beat_seconds", "downbeat_seconds"):
            values = track.get(key)
            if not isinstance(values,list) or not values or any(
                type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<360 for v in values
            ) or any(a>=b for a,b in zip(values,values[1:])):
                raise ValueError(f"Track {index}: {key} als aufsteigende Sekundenliste erforderlich")
            refs[key] = values
        start = time.perf_counter()
        found = analyse_file(manifest_path.parent / track["pfad"], sample_rate, ffmpeg)
        elapsed = time.perf_counter()-start
        grid = found["grid"]
        row = {"track": index, "confidence": found["confidence"], "elapsed_s": elapsed}
        if grid:
            period = 60/grid["bpm"]
            row["bpm"] = grid["bpm"]
            row["bpm_error"] = abs(grid["bpm"]-track["bpm"]) if track.get("bpm") else None
            for key, anchor, step in (("beat_seconds","beat0",period),
                                      ("downbeat_seconds","bar0",period*4)):
                phase = grid[anchor]/sample_rate
                errors = sorted(abs(t-phase-round((t-phase)/step)*step)*1000 for t in refs[key])
                row[key] = {"count":len(errors),"median_ms":errors[len(errors)//2],
                            "p95_ms":errors[math.ceil(.95*len(errors))-1],"max_ms":max(errors)}
        else:
            row["status"] = "unsicher"
        rows.append(row)
    command = "python -m benchmarks.beatgrid.measure " + shlex.join(
        ["<lokales Manifest>", "--out", "<lokales Ergebnis>", "--sample-rate", str(sample_rate)])
    report = {"wp":"WP10","kandidat":"CPU-BeatGrid","gate":"nicht_gemessen",
              "modus":"offline","zeitpunkt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "rechner":baseline.collect(),"befehl":command,"notizen":notes,
              "messwerte":{p:dict.fromkeys(result.METRICS) for p in ("warm","kalt")},
              "tracks":rows}
    result.write(output,report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--sample-rate",type=int,default=48000)
    parser.add_argument("--ffmpeg",default="ffmpeg")
    args = parser.parse_args()
    measure(args.manifest,args.out,args.sample_rate,args.ffmpeg)


if __name__ == "__main__":
    main()
