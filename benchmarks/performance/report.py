"""Hörprüfung dokumentieren; kein automatisches Gate und keine erfundenen Messwerte."""
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from result import write, METRICS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline", type=Path)
    p.add_argument("render", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--note", action="append", required=True,
                   help="Je Demo: Name, gehört/nicht gehört, Beobachtung")
    a = p.parse_args()
    machine = json.loads(a.baseline.read_text(encoding="utf-8"))
    rendered = json.loads(a.render.read_text(encoding="utf-8"))
    data = {"wp": "WP14", "kandidat": "Performance-Tools",
            "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "befehl": "node benchmarks/performance/render.mjs <externes Verzeichnis>",
            "rechner": machine, "gate": "nicht_gemessen", "modus": "offline",
            "messwerte": {phase: dict.fromkeys(METRICS) for phase in ("warm", "kalt")},
            "notizen": a.note + [f"{r['name']}: {r['frames']} Frames; PCM-Peak {r['peak']}; {r['warnings']}"
                                for r in rendered["results"]]}
    if a.output.exists():
        p.error("Ergebnis existiert bereits")
    write(a.output, data)


if __name__ == "__main__":
    main()
