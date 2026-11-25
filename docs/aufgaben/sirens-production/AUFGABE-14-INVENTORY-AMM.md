# Aufgabe 14 – Kette KETTE-P12, Aufgabe 2 von 3 (nach 13). `inventory` nutzt den AMM-Export aus der Konfiguration

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/__main__.py`, Tests `tests/production/test_cli*`.

## Befund
`python -m sirens.production inventory` ruft `collect(cfg)` ohne `amm_export`; Ergebnis with_prompts 0 und missing_sources ["amm_export"], obwohl die Konfiguration einen Export nennt.

## Umfang
`inventory` und `references` lesen `amm_export` aus SIRENS_PRODUCTION_CONFIG und reichen ihn an `collect` weiter.

## Abnahme
CLI-Test mit temporärer Konfiguration und Fixture-Export.
