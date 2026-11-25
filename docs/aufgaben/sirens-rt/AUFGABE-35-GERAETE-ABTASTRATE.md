# Aufgabe 35: Mock-Pfad mit der Abtastrate des Ausgabegeräts

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 34 (in
derselben Kette davor) voraus.

## Ziel

Der Mock-Pfad im Live Lab läuft auf Geräten mit 44,1 kHz und 48 kHz, ohne erzwungenen 48-kHz-AudioContext.
Für G4 musste der Koordinator den Kontext per Init-Skript auf 48 kHz zwingen.

## Ausgangslage

- `web/js/realtime/shell.js`, Zeile ~118: `if(core.rate!==48000)throw new Error("Mock-Testmodus benötigt einen
  AudioContext mit 48 kHz")`.
- Der Server liefert 48 kHz (`sirens/realtime/sessions.py`, `sirens/realtime/mock.py`: `sample_rates:
  [48000]`). Laut Übergabe von Aufgabe 30 bleibt die Serverquelle bei 48 kHz; umgerechnet wird im Browser.

## Umfang

1. Sperre in `shell.js` entfernen. Framekoordinaten (Ausgabeframe, Loop-Frame aus `loopPlan`) zwischen
   Gerätesamplerate und 48 kHz umrechnen, ohne Drift über 2 Stunden (ganzzahlig, Rest mitführen).
2. Wet-Pakete mit 48 kHz auf die Gerätesamplerate bringen (einfache lineare Interpolation genügt für den
   Mock-Pfad), Dry/Wet bleibt sampelgenau ausgerichtet.
3. Server und Verträge unverändert.

## Abnahme

1. Node-Test aus Aufgabe 34 zusätzlich mit 44.100 Hz: 100 Loop-Wechsel, 0 unerwartete Underruns.
2. Test: Frame-Umrechnung über 2 Stunden (345.600.000 Frames bei 48 kHz) ohne aufsummierten Fehler.
3. Alle bestehenden Tests bleiben grün.
4. Ergebnisdatei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-35.md`; Hörprüfung am Gerät macht der
   Koordinator („nicht gemessen“).
