# Aufgabe 16 – Kette KETTE-P13. Laufzeiten je Stufe im Jobstatus

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/jobs.py`, `sirens/production/runner.py`, Tests `tests/production/test_jobs*`, `tests/production/test_runner*`.

## Befund
status.json überschreibt den running-Zeitstempel; es gibt keine Zeiten je Stufe (Assets, Instrumente, Mix, Report). Für die Messung mussten Datei-Zeitstempel herhalten.

## Umfang
`stages: [{stage, started, finished, seconds}]` in status.json (atomar, abwärtskompatibel), Gesamtzeit; im Report übernommen.

## Abnahme
Tests mit gefälschter Uhr; Abbruch und Fehler setzen `finished` der laufenden Stufe.
