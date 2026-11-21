"""Unabhängiger Worker: Basic Pitch Note-Events zu einer kleinen JSON-Timeline.

Nur durch StemNoten mit validierten, lokalen Dateipfaden aufgerufen.
"""
import json
import math
import os
import sys
from pathlib import Path


def ereignisse_normalisieren(note_events):
    """(Start, Ende, MIDI-Pitch, Stärke, ...) -> [Sekunden, Sekunden, 0-127, 0-1]."""
    noten = []
    for event in note_events:
        if len(event) < 4:
            continue
        start, end, pitch, amplitude = map(float, event[:4])
        if not all(math.isfinite(x) for x in (start, end, pitch, amplitude)):
            continue
        if not 0 <= start < end <= 7200 or not 0 <= pitch <= 127:
            continue
        if end - start < .04:
            continue
        noten.append([round(start, 4), round(end, 4), int(round(pitch)),
                      round(max(.03, min(1, amplitude)), 3)])
        if len(noten) >= 12000:
            break
    return sorted(noten, key=lambda event: (event[0], event[2]))


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Eingabe und Ausgabe erforderlich.")
    eingabe, ausgabe = Path(sys.argv[1]), Path(sys.argv[2])
    if not eingabe.is_file() or eingabe.suffix.lower() != ".wav" or ausgabe.suffixes[-2:] != [".notes", ".json"]:
        raise SystemExit("Unzulässiger Stem- oder Notendateipfad.")

    from basic_pitch.inference import predict  # optionale KI-Abhängigkeit, nur im Worker
    _, _, events = predict(str(eingabe))
    noten = ereignisse_normalisieren(events)
    tmp = ausgabe.with_suffix(".tmp")
    tmp.write_text(json.dumps(noten, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, ausgabe)
    print("Erkannte Noten:", len(noten))


if __name__ == "__main__":
    main()
