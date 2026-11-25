# Aufgabe 17 – Kette KETTE-P14. Mix: Bass ist nicht automatisch Sub

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/mixing.py`, `workers/production_mix/`, Tests `tests/production/test_mixing*`.

## Befund
`mixing._settings` behandelt jede Spur mit Rolle „bass“ als Sub (`sub = role in ("bass", "sub") or …`); damit landet auch die Gear-Bass-Spur aus dem Arrangement im Mono-Sub-Pfad samt Sidechain.

## Umfang
Sub nur bei Rolle `sub` oder Patch/Track-ID mit Sub-Kennung; Bass-Spuren bleiben Bass (eigener EQ/Kompression, Sidechain nur, wenn der Plan es verlangt). Reproduzierbarkeit aus Aufgabe 09 bleibt (Test 10x).

## Abnahme
Tests: Bass ≠ Sub, Sub weiterhin mono, bestehende Mix-Tests grün.
