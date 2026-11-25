# K09 – Mix byte-reproduzierbar machen

Folgeaufgabe aus der Abnahme von K05/K08 (24.11.2026). Lies PLAN.md, CONTRACT.md, KETTEN.md und
`ergebnisse/K05.md`. Owner-Dateien wie K05: `workers/production_mix/`, `sirens/production/mixing.py`,
`tests/production/test_mixing*`.

## Befund

`tests/production/test_mixing.py::MixingTests.test_reproducible_revision_and_reference` schlägt am Zielrechner
(Windows 11, ffmpeg im PATH) in etwa jedem dritten Lauf fehl: Zwei Mixe mit identischen Stems und identischem Plan
liefern unterschiedliche `master.wav`-Bytes. In der früheren Linux-CI war der Test mangels ffmpeg übersprungen.
Die Eingaben sind deterministisch (Test-Fixture ohne Zufall), `-threads 1` und `-filter_complex_threads 1` sind
gesetzt. Verdacht: Reihenfolge/Größe der Audio-Frames im Filtergraph (`asplit`, `amix`, `sidechaincompress`,
Hall-Taps mit `adelay`) oder Dither beim Wandeln nach PCM24.

## Umfang

1. Ursache eingrenzen (ffmpeg-Version im Worker-Report protokollieren; Graph schrittweise vereinfachen) und
   beheben, ohne den Klang zu ändern: z. B. feste Frame-Größe (`asetnsamples`), `amix` durch deterministische
   Summe ersetzen, `-ar`/`-sample_fmt`/Dither explizit setzen.
2. Test so erweitern, dass er die Reproduzierbarkeit mehrfach prüft (mindestens 5 Wiederholungen) und die
   ffmpeg-Version im Fehlertext nennt.
3. Kein Import aus `workers` im Paket `sirens/`; keine neuen Abhängigkeiten.

## Abnahme

- `py -3.11 -m unittest tests.production.test_mixing` 10-mal hintereinander grün am Zielrechner (der Koordinator
  prüft lokal; GitHub Actions ist abgeschaltet).
- Bestehende Messwerte (LUFS, True Peak ≤ −1 dBTP) unverändert innerhalb 0,1 dB.
