"""WP19: Browser-Soak in das gemeinsame Ergebnisformat übertragen."""
import argparse
import json
import math
from pathlib import Path

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write


def convert(raw, candidate, machine):
    seconds = raw["requested_seconds"]
    if seconds not in (1800, 7200):
        raise ValueError("Ungültige Soll-Dauer")
    for key in ("elapsed_seconds", "audio_seconds"):
        if type(raw[key]) not in (int, float) or not math.isfinite(raw[key]) or raw[key] < 0:
            raise ValueError("Ungültige Dauer: " + key)
    for key in ("underruns", "interruptions", "visibility_changes", "epoch_changes"):
        if type(raw[key]) is not int or raw[key] < 0:
            raise ValueError("Ungültiger Zähler: " + key)
    if type(raw["completed"]) is not bool:
        raise ValueError("Ungültiger Abschlussstatus")
    measured = (raw["completed"] and raw["elapsed_seconds"] >= seconds
                and raw["audio_seconds"] >= seconds - 1 and not raw.get("error"))
    values = dict.fromkeys(METRICS)
    values["underruns"] = raw["underruns"]
    return dict(wp="WP19", kandidat=candidate, zeitpunkt=raw["zeitpunkt"],
                befehl="benchmarks/g4/soak.js; python -m benchmarks.g4.report",
                gate="nicht_gemessen", modus="streaming", rechner=machine,
                messwerte=dict(warm=values, kalt=dict.fromkeys(METRICS)),
                elapsed_seconds=raw["elapsed_seconds"] if measured else 0,
                notizen=["Audio-Sekunden: " + str(raw["audio_seconds"]),
                         "Unterbrechungen: " + str(raw["interruptions"]),
                         "Tabwechsel: " + str(raw["visibility_changes"]),
                         "Epoch-Wechsel: " + str(raw["epoch_changes"]),
                         "Fehler: " + str(raw.get("error")),
                         "Keine analoge Geräte-/Modelllatenz gemessen; keine Gate-Entscheidung."])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw", type=Path)
    p.add_argument("--candidate", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    write(a.out, convert(json.loads(a.raw.read_text(encoding="utf-8")), a.candidate, collect()))


if __name__ == "__main__":
    main()
