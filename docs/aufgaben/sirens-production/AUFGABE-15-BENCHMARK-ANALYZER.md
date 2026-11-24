# Aufgabe 15 – Kette KETTE-P12, Aufgabe 3 von 3. Benchmark misst LUFS und True Peak

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/__main__.py`, `sirens/production/quality.py`, Tests `tests/production/test_quality*`.

## Befund
Der CLI-Benchmark liefert True Peak und LUFS als null, weil kein Analyzer übergeben wird. `mastering_analyzer(worker_python, engine_root)` funktioniert lokal (AMM `mastering_engine`).

## Umfang
`analysis_python` und `analysis_root` aus der Konfiguration lesen und an `benchmark` übergeben; fehlen sie, ffmpeg-`ebur128` als Rückfall, sonst null mit Grund.

## Abnahme
Tests mit Mock-Analyzer und ohne Analyzer (null + Grund).
