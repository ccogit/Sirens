"""WP06-Browser-Rohmessung in das gemeinsame Benchmark-Format übertragen."""
import argparse
import json
import math
from pathlib import Path

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write


def convert(raw, machine, ci_green=False):
    duration = raw["elapsed_seconds"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        raise ValueError("Ungültige Dauer")
    for k in ("underruns", "skipped_blocks", "interruptions", "matched_blocks", "invalid_blocks",
              "alignment_max_samples"):
        if raw[k] is not None and (type(raw[k]) is not int or raw[k] < 0):
            raise ValueError("Ungültiger Messwert: " + k)
    for k in ("completed", "dry_fallback", "worker_error"):
        if type(raw[k]) is not bool:
            raise ValueError("Ungültiger Status: " + k)
    measured = raw["completed"] and duration >= 1800 and raw["underruns"] is not None
    passed = (measured and not raw.get("error") and raw["underruns"] == 0
              and raw["interruptions"] == raw["skipped_blocks"] == raw["invalid_blocks"] == 0
              and raw["matched_blocks"] > 0 and raw["alignment_max_samples"] is not None
              and raw["alignment_max_samples"] <= 1 and raw["dry_fallback"] and raw["worker_error"])
    values = dict.fromkeys(METRICS)
    values["underruns"] = raw["underruns"]
    return {
        "wp": "WP06", "kandidat": "Mock-Worker / Sidecar / AudioCore (G2)",
        "zeitpunkt": raw["zeitpunkt"], "rechner": machine,
        "befehl": "benchmarks/g2/soak.js auf lokaler Sirens-Seite; python -m benchmarks.g2.report",
        "gate": "green" if passed and ci_green else "red" if measured and not passed else "nicht_gemessen",
        "modus": "offline",
        "messwerte": {"warm": values, "kalt": dict.fromkeys(METRICS)},
        "notizen": [
            f"Soak: {duration} s; vollständiger Lauf: {raw['completed']}; CI grün bestätigt: {ci_green}",
            f"PCM-Blöcke korrekt: {raw['matched_blocks']}; ungültig: {raw['invalid_blocks']}; "
            f"übersprungen: {raw['skipped_blocks']}; Unterbrechungen: {raw['interruptions']}",
            f"Digitale PCM-Fixture-Deckung (Samples): {raw['alignment_max_samples']}",
            f"Dry am Master-Abgriff: {raw['dry_fallback']}; Worker-Fehlerzustand: {raw['worker_error']}",
            "Keine Messung analoger Geräte-Latenz; keine KI- oder Echtzeitfreigabe.",
            f"Fehler: {raw.get('error') or 'keiner gemeldet'}",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ci-green", action="store_true", help="Nur nach belegter grüner PR-CI")
    args = parser.parse_args()
    write(args.out, convert(json.loads(args.raw.read_text(encoding="utf-8")), collect(), args.ci_green))


if __name__ == "__main__":
    main()
