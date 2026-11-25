# Aufgabe 32: Mess-Harness für G4 lauffähig machen

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt die gemergten
Aufgaben 04, 16 und 19 voraus. Folgeaufgabe aus der Systemabnahme G4 (Aufgabe 19).

## Ziel

Die Systemsuite (`benchmarks/system_suite.py`) läuft auf dem Windows-Rechner ohne Handgriffe von Anfang bis
Ende durch. Heute scheitern dort drei Messpfade am Harness, nicht am Produkt.

## Ausgangslage (G4-Lauf 24./25.11.2026)

1. **Audio Core (WP04):** `benchmarks/audio_core/serve.py` liefert nur die Dateien in `PATHS`. Der Worklet
   lädt aber auch `web/js/realtime/effects/*.js` und bekommt 404. Für G4 musste ersatzweise
   `python -m http.server` laufen.
2. **Recorder (WP16):** `benchmarks/recorder/browser.py` lehnt Modulpfade mit `/` ab. Dadurch wird
   `web/js/realtime/effects/rack.js` nicht ausgeliefert (404), und die Messung ist unmöglich.
3. **Prozessinventar:** `process_snapshot()` in `benchmarks/system_suite.py` (PowerShell
   `Get-CimInstance … | ConvertTo-Json`) lieferte nach 16 Minuten einmal ungültiges JSON. Die Suite hat
   daraufhin den laufenden und alle folgenden Messpfade abgebrochen.
4. **Separation:** Der RoFormer-Pfad verlangt 44,1 kHz Stereo. Ein Song mit 48 kHz wird mit dem
   nichtssagenden Fehler „audio“ abgelehnt. Die Suite sollte das vor dem Start prüfen und klar melden.
5. **Stable Audio:** Ohne `SIRENS_RT_STABLE_AUDIO_CACHE` schlägt der Pfad mit „Lokaler Cache fehlt“ fehl,
   obwohl die Gewichte im bekannten venv-Ordner liegen (`.venv-spike-stable-audio-3\weights`). Den Ordner
   wie bei den Modellumgebungen automatisch finden (siehe `python_dirs` im Manifest).

## Umfang

1. Beide Server liefern alle ES-Module, die der jeweilige Benchmark transitiv importiert, per Allowlist unter
   `web/js/realtime/` einschließlich Unterordnern. Kein Pfad außerhalb des Repos, kein `..`, nur
   `127.0.0.1`.
2. `process_snapshot()` robust: wiederholen bei ungültigem JSON oder Zeitüberschreitung (bis zu 5 Versuche mit
   kurzer Pause). Ein einzelner Ausfall bricht keinen Messpfad ab; erst ein Dauerausfall wird als Fehler
   dieses Pfads gemeldet. Die folgenden Pfade laufen weiter.
3. Vorprüfung der Testdaten je Pfad (Abtastrate, Kanäle) mit klarer Meldung.
4. Stable-Audio-Cache automatisch finden; die Umgebungsvariable bleibt als Vorrang.

## Nicht im Umfang

- Produktcode unter `web/js/realtime/` und `sirens/realtime/` (Aufgaben 30 und 31). Hier nur `benchmarks/`
  außer `benchmarks/g4/` und `benchmarks/dsp/`, und `workers/stable_audio/` nur für die Cache-Suche.

## Abnahme

1. Tests: Der Server liefert `effects/rack.js` und Unterordnermodule aus. `..`, absolute Pfade und fremder
   Host ergeben 404.
2. Test mit nachgebautem Snapshot, der einmal kaputtes JSON liefert: Die Suite läuft weiter. Bei
   Dauerausfall ist genau der betroffene Pfad als Fehler markiert.
3. Test: 48-kHz-Song für Separation ergibt eine klare Vorprüfungsmeldung statt eines Jobfehlers.
4. Test: Cache wird aus dem venv-Ordner gefunden; die Umgebungsvariable hat Vorrang.
5. Alle bestehenden Tests bleiben grün. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-32.md`.
