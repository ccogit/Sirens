# Aufgabe 11 – Kette KETTE-P11, Aufgabe 1 von 2. WAV mit WAVE_FORMAT_EXTENSIBLE akzeptieren

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/contracts.py` (nur `validate_wav` und Hilfsfunktionen), `sirens/production/assets.py`, Tests `tests/production/test_contracts*`, `tests/production/test_assets*`.

## Befund
ffmpeg schreibt PCM24 als WAVE_FORMAT_EXTENSIBLE (Format-Tag 65534). Pythons `wave` in 3.11 lehnt das ab („unknown format: 65534“); `assets.render_assets`/`inspect_wav` (um Zeile 318) meldet dann „source needs local WAV conversion“, der Run scheitert.

## Umfang
1. Eigener kleiner RIFF-Leser (Standardbibliothek): PCM (1) und EXTENSIBLE mit Subformat PCM akzeptieren; Kanäle, Rate, Bittiefe, Frames korrekt lesen. Float-WAV weiterhin klar ablehnen.
2. Alle Stellen in `contracts.py` und `assets.py`, die `wave` zum Prüfen nutzen, darauf umstellen.

## Abnahme
Tests mit selbst erzeugten Bytes beider Header-Varianten (PCM24 Mono/Stereo), Fehlerfall Float und kaputter Header.
