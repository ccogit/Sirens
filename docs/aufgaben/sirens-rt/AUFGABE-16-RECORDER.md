# Aufgabe 16: Recorder, Session und Export (WP16)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP16“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 04 und 06 voraus.

## Ziel

Der Master-Bus lässt sich verlustfrei aufnehmen und als WAV exportieren; eine Session-Datei hält Quellen, Versionen, Zeitleiste und Seeds fest und lässt sich wieder abspielen.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Audio-Kern: `web/js/realtime/audio_core.js`. Sitzungen: `sirens/realtime/sessions.py`. Versionierung im Bestand als Vorbild: `sirens/versionen.py`.

## Umfang

1. `web/js/realtime/recorder.js`: PCM-Abgriff im Master-Bus über das Worklet, begrenzte Puffer, blockweises Senden an den Dienst; Aufnahme startet nur durch Nutzeraktion; kein MediaRecorder.
2. `sirens/realtime/recordings.py`: schreibt blockweise auf Platte (WAV 24-bit PCM oder 32-bit float, dokumentiert), prüft Speicherplatz, Größenlimit und Segmentierung, atomarer Abschluss, Reparatur abgebrochener Aufnahmen; Ziel außerhalb des Musikordners, Namen ohne Kollision.
3. Session-JSON mit Schema: Quell-Hashes, Modell- und Preset-Versionen, Zeitleiste der Befehle, Seeds, Verweise auf gerenderte Assets; Wiedergabe einer Session stellt Parameter wieder her.
4. Adressen als Hook `docs/realtime/hooks/WP16.md`, sofern Aufgabe 06 sie nicht schon vorsieht; Messskript `benchmarks/recorder/` für eine 30-Minuten-Aufnahme.

## Nicht im Umfang

- Kein verlustbehafteter Codec als „verlustfrei“.
- Kein Schreiben in den Originalordner.

## Abnahme

1. Tests: aufgenommene Fixture stimmt mit dem Signal innerhalb der Quantisierungsgrenze überein; Dauer und Abtastrate korrekt; WAV-Kopf auch über 4 GB bzw. Segmentgrenze korrekt.
2. Tests: Abbruch mitten in der Aufnahme → reparierbare Datei; Platte voll (nachgestellt) → sauberer Abschluss mit Meldung; zweite Aufnahme gleichen Namens überschreibt nichts.
3. Tests: Session speichern und laden ergibt dieselben Parameter; ungültige Session wird abgelehnt.
4. Negativ: Zielpfad außerhalb des Aufnahmeordners wird abgelehnt.
5. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: 30 Minuten Aufnahme (48 kHz, Stereo, 24 bit, rund 518 MB).
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
