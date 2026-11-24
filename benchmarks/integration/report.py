"""Sicht-/Hörprotokoll WP17 in das gemeinsame Ergebnisformat übertragen.

Kein automatisches grünes Gate aus subjektiven Beobachtungen.
"""
import argparse
import datetime
import json
from pathlib import Path

from benchmarks.result import METRICS, write

CHECKS = ("song", "stems", "effect", "pad", "record", "export", "stop",
          "panic", "leave", "legacy", "claude", "diagnosis")


def convert(machine, observations):
    if set(observations) != set(CHECKS):
        raise ValueError("Für jeden Prüfschritt ist ein Eintrag erforderlich.")
    for key, entry in observations.items():
        if (not isinstance(entry, dict) or set(entry) != {"status", "note"}
                or entry["status"] not in ("bestanden", "fehlgeschlagen", "nicht_gemessen")
                or not isinstance(entry["note"], str) or not entry["note"].strip()):
            raise ValueError("Ungültige Beobachtung: " + key)
    # G3 erfordert zusätzliche Messungen je Funktion; hier nur Sicht-/Hörprotokoll.
    return {
        "wp": "WP17", "kandidat": "Produktintegration (Sicht-/Hörprotokoll)",
        "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rechner": machine,
        "befehl": "benchmarks/integration/README.md; python -m benchmarks.integration.report",
        "gate": "nicht_gemessen", "modus": "offline",
        "messwerte": {phase: dict.fromkeys(METRICS) for phase in ("kalt", "warm")},
        "notizen": [f"{k}: {observations[k]['status']} – {observations[k]['note']}" for k in CHECKS]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("observations", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    write(args.out, convert(json.loads(args.baseline.read_text(encoding="utf-8")),
                            json.loads(args.observations.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
