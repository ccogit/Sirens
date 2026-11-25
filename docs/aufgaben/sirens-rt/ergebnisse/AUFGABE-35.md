# AUFGABE-35 – offen / Übergabe

Nicht begonnen: setzt Aufgabe 34 und deren vollständigen Produzenten-/Worklet-Test voraus. Keine Änderung an shell.js, audio_core.js, Server oder Verträgen für diese Aufgabe.

## Abnahme
1. 44.100 Hz, 100 Loop-Wechsel, null unerwartete Underruns: nicht umgesetzt/nicht geprüft.
2. Frame-Umrechnung über 345.600.000 Serverframes: nicht umgesetzt/nicht geprüft.
3. Bestehende Tests: nicht geprüft.
4. Diese Ergebnisdatei. Hörprüfung am Gerät nicht gemessen.

## Übergabe
Fertig: keine Codeänderungen für diese Aufgabe. Offen: nach 34 48-kHz-Server-Sitzung beibehalten, 48-kHz-Sperre entfernen, Dry/Wet auf Geräterate ausrichten, absolute ganzzahlige Framegrenzen bzw. Restführung nutzen; Paketgrenzen und Loop-Rest gesondert prüfen, Drift- und 44,1-kHz-Tests ergänzen. Die bestehende Transport-Resamplingfunktion in transport.js ist zu berücksichtigen; keine unfreigegebene Datei ändern.
Nächster Schritt: nach Abschluss von 34 umsetzen und Tests unter Node 22 sowie py -3.11 -m unittest discover -s tests -v ausführen; Koordinator führt Hörprüfung auf 44,1- und 48-kHz-Geräten und G4-Soak durch.
Fehlerausgabe: siehe AUFGABE-33.md (DNS; keine CI-Läufe).
Keine neuen Abhängigkeiten, Pins oder Lizenzen; kein Rückbau nötig.
