# Aufgabe 18 – Kette KETTE-P15. Preview-Plan aus gemessenen Sprachdauern

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/arrangement.py`, `sirens/production/templates/`, Tests `tests/production/test_arrangement*`.

## Befund
Das Clear-Head-Rezept scheitert für einen 30–60-s-Preview mit allen vier Sprachpassagen („Target duration cannot hold complete spoken cues“, um Zeile 182). Der Koordinator musste einen eigenen Preview-Plan schreiben (Abschnittslängen nach gemessenen TTS-Dauern, K02-Muster, `validate_arrangement`).

## Umfang
1. Preview-Modus: wählt eine Teilmenge der Cues (z. B. Chorus + Verse) oder kürzt Interludes, nie den Text; Taktgrenzen; Ziel 30–60 s.
2. Abschnittslängen aus gemessenen Sprachdauern (Eingabe: Dauer je Cue in Sekunden), auf ganze Takte aufgerundet plus kurze Pause.
3. Drei Varianten weiterhin bewusst verschieden (Groove-Muster, Swing, Bass/Hook-Patches).

## Abnahme
Tests: vier Cues mit realistischen Dauern (4,8 / 6,3 / 4,9 / 4,8 s) ergeben gültige Previews 30–60 s; Vollsong unverändert.
