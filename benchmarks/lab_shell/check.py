"""Manuelle Sichtprüfung WP05; keine Audio- oder GPU-Leistungsmessung."""
import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from baseline import collect
from result import METRICS, write

CHECKS = (
    "Schalter aus: RT gesperrt; Bestandsspielzeuge erreichbar",
    "RT an, Mock aus: kein Modell bzw. nicht freigegeben sichtbar",
    "RT an, Mock an: Testmodus, keine KI und kein Ton sichtbar",
    "Katalog und vorhandene Stems wählbar; leere Bibliothek verständlich",
    "GPU/Queue/VRAM: fehlende Werte unbekannt, keine erfundene Latenz",
    "Mock: Play/Pause/Seek/Stop, Bypass, Dry/Wet, A/B und Panic",
    "Presets nach erneutem Öffnen lokal verfügbar; Tastatur/Fokus",
    "Wechsel zu jedem Bestandsspielzeug; keine RT-Requests nach Verlassen",
    "API 503 bzw. ungültiges JSON: Fehler sichtbar, kein JS-Absturz",
    "Öffnen startet keine GPU-Aufgabe und erzeugt keinen AudioContext",
)


def build_result(answers, machine):
    if len(answers) != len(CHECKS) or any(a not in ("ja", "nein", "offen") for a in answers):
        raise ValueError("Je Prüfschritt ja, nein oder offen erwartet")
    return {
        "wp": "WP05", "kandidat": "RTX Neural Lab Sichtprüfung",
        "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gate": "nicht_gemessen", "modus": "unbekannt", "rechner": machine,
        "befehl": "python benchmarks/lab_shell/check.py --out benchmarks/results/wp05-lab-shell.json",
        "messwerte": {phase: dict.fromkeys(METRICS) for phase in ("warm", "kalt")},
        "notizen": [f"{a}: {check}" for a, check in zip(answers, CHECKS)] +
                    ["Nur Sichtprüfung; keine Audio-, VRAM-Peak- oder Latenzmessung und kein Gate."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print("Anleitung: docs/realtime/hooks/WP05.md. Keine Kundendaten eingeben.")
    answers = []
    for check in CHECKS:
        while True:
            answer = input(check + " [ja/nein/offen]: ").strip().lower()
            if answer in ("ja", "nein", "offen"):
                answers.append(answer)
                break
    write(args.out, build_result(answers, collect()))
    print("Sichtprüfung protokolliert; kein Leistungs-Gate.")


if __name__ == "__main__":
    main()
