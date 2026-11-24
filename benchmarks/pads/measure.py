"""20 echte Warm-Jobs und Deadline-Auswertung mit dem JS-Scheduler.
Nur explizit im installierten Worker-Python ausführen; keine Downloads."""
import argparse
import datetime
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.result import write, METRICS
from workers.stable_audio.adapter import Adapter, PAD_TYPES


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--p95-ms", type=float, required=True)
    args = parser.parse_args()
    adapter = Adapter()
    start = time.perf_counter()
    adapter.load()
    adapter.warmup()
    cold = (time.perf_counter() - start) * 1000
    rows = []
    try:
        for i in range(20):
            bars = (1, 2, 4, 8)[i % 4]
            kind = PAD_TYPES[i % len(PAD_TYPES)]
            start = time.perf_counter()
            meta = adapter.generate(dict(type=kind, prompt="electronic dance music at 120 BPM",
                                         seed=i, strength=0.7, bars=bars, duration=bars*2))
            rows.append(dict(type=kind, bars=bars, seed=i, frames=meta["frames"],
                             elapsed_ms=(time.perf_counter()-start)*1000))
    finally:
        adapter.unload()
    result = subprocess.run(["node", str(Path(__file__).with_name("evaluate.mjs"))],
                            input=json.dumps(dict(rows=rows, p95_ms=args.p95_ms)), text=True,
                            capture_output=True, check=True)
    counts = json.loads(result.stdout)
    times = [row["elapsed_ms"] for row in rows]
    empty = dict.fromkeys(METRICS)
    warm = dict(empty, p50_ms=percentile(times,.5), p95_ms=percentile(times,.95),
                p99_ms=percentile(times,.99))
    data = dict(wp="WP12", kandidat="Stable Audio 3 small-music", modus="lookahead",
                gate="nicht_gemessen", zeitpunkt=datetime.datetime.now().astimezone().isoformat(),
                befehl=subprocess.list2cmdline(sys.argv),
                rechner=dict(os=platform.platform(), python=sys.version, node=None, ffmpeg=None,
                             gpus=None, wsl=None, disk=None, git=None, notes=[]),
                messwerte=dict(warm=warm, kalt=dict(empty)),
                notizen=["Kalt inkl. Load/Warmup: %.2f ms" % cold,
                         "Deadline-Planung (kein Browser/kein Tonausgang): " + json.dumps(counts),
                         "G3 bleibt bis Ende-zu-Ende-Hör-/Einsatzmessung offen."],
                jobs=rows, deadline=counts)
    write(args.out, data)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
