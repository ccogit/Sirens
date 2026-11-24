# WP17 – Sicht- und Hörprüfung (nicht gemessen)

Auf dem Zielrechner lokal mit SIRENS_RT_ENABLED=1 und SIRENS_RT_MOCK=1 starten.
Browser in 48 kHz, geringe Abhörlautstärke. Keine Originaldateien verändern.
Für jeden Schritt eine Beobachtung mit Status und konkreter Fehler-/Erfolgsmeldung
in einer externen JSON-Datei notieren:

- song: Katalog filtern, Testsignal und lokal vorhandene PCM16-WAV auswählen.
- stems: vorhandene Stems wählen; wenn kein produktiver Pfad verfügbar ist,
  nicht_gemessen bzw. fehlgeschlagen notieren, nicht als Erfolg werten.
- effect: Mock-Wet/Gain und Bypass vergleichen; echte DSP-Effekte separat messen.
- pad: Mock-Pad auslösen, Gain-Änderung prüfen (kein generatives Pad).
- record: Aufnahme starten/stoppen, PCM24-WAV im externen RT-Ordner prüfen.
- export: Sitzungsexport vor Stop auslösen, ID und JSON samt Quelle/Assets prüfen.
- stop: Stop; kein Ton, kein Worker der Sitzung.
- panic: während Wiedergabe und ausstehender Aktion; kein Ton/Worker.
- leave: mehrmals wechseln und erneut öffnen; Browser-Timer, AudioContext und
  Prozessmanager auf verwaiste Ressourcen prüfen.
- legacy: Flag aus, Bestandsnavigation, Katalog, Stem Studio, Claude-Start prüfen.
- claude: laufende Sitzung und fehlende GPU-Telemetrie; Verhalten dokumentieren.
- diagnosis: Modellstatus, Mess-/Freigabehinweis und Installationshilfe prüfen.

Beispielstruktur (alle oben genannten Schlüssel erforderlich):
`{"song":{"status":"bestanden","note":"konkrete Beobachtung"},"stems":{"status":"nicht_gemessen","note":"Grund"}}`.
Zulässige Status: bestanden, fehlgeschlagen, nicht_gemessen. Keine erfundenen Werte.

```sh
python -m benchmarks.integration.report <baseline.json> <beobachtungen.json> <ergebnis.json>
python -m benchmarks.result <ergebnis.json>
```

Das Skript erzeugt nur ein Sicht-/Hörprotokoll mit Gate nicht_gemessen.
G3 zusätzlich je Funktion: vorhandene Messpfade in benchmarks/g2, dsp, performance,
recorder und separation sowie tatsächliche Zielhardwaremessungen verwenden.
Keine Freigabe allein aus dem Protokoll. Keine Audiodateien einchecken.
