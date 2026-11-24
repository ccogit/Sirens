"""E2E-Protokoll aus dem Browser auswerten, keine Modell-/Planungszeiten als Hörnachweis."""
import argparse
import datetime
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.result import METRICS, write


def evaluate(rows):
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError("Genau 20 Job-Beobachtungen erforderlich")
    counts = dict(timely=0, shifted=0, dry=0, other=0)
    times = []
    for i, row in enumerate(rows):
        if row.get("job") != i + 1:
            raise ValueError("Fortlaufende Jobnummern 1 bis 20")
        for field in ("target_frame", "scheduled_frame", "observed_frame"):
            value = row.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(field)
        target, planned, actual = (row.get(k) for k in ("target_frame", "scheduled_frame", "observed_frame"))
        if target is None:
            raise ValueError("Ursprüngliche Taktgrenze fehlt")
        elapsed = row.get("asset_ready_ms")
        if elapsed is not None:
            if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("asset_ready_ms")
            times.append(elapsed)
        if planned is None and actual is None:
            counts["dry"] += 1
        elif planned is not None and actual is not None and abs(actual-planned) <= 1:
            if planned == target:
                counts["timely"] += 1
            elif planned > target:
                counts["shifted"] += 1
            else:
                counts["other"] += 1
        else:
            counts["other"] += 1
    counts["ratio"] = counts["timely"] / 20
    times.sort()
    metrics = dict.fromkeys(METRICS)
    if len(times) == 20:
        for key, p in (("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99)):
            metrics[key] = times[math.ceil(len(times)*p)-1]
    return counts, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    machine = json.loads(args.baseline.read_text(encoding="utf-8"))
    observations = json.loads(args.observations.read_text(encoding="utf-8"))
    rows = observations["jobs"]
    counts, warm = evaluate(rows)
    # Nur explizite Zielrechner-/Hörfreigabe kann einen Gate-Bericht begründen.
    # Dieses Skript allein prüft nicht, ob die Beobachtungen echt sind.
    data = dict(wp="WP12", kandidat="Stable Audio 3 small-music", modus="lookahead",
                gate="nicht_gemessen", zeitpunkt=datetime.datetime.now().astimezone().isoformat(),
                befehl=" ".join(sys.argv), rechner=machine,
                messwerte=dict(warm=warm, kalt=dict.fromkeys(METRICS)),
                notizen=["Manuell erfasste Ende-zu-Ende-Beobachtungen; Audio-Ausgabe und "
                          "Taktgrenze separat prüfen. Gate-Freigabe durch Koordinator.",
                          "Rechtzeitig: %d/20; Ziel 19/20." % counts["timely"]],
                jobs=rows, deadline=counts)
    write(args.out, data)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
