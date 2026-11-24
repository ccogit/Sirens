# AUFGABE-14 – Performance-Tools (WP14)

## Umsetzung
- Drum Architect: synthetische Kick/Snare/Becken, Double/Replace bei vorhandenen Einzelstems, Demucs-Gesamtspur nur Double mit expliziter Klassifikation, Velocity, Raster und manuelle Korrektur.
- Stem Crossover: bis vier Mono-PCM-Quellen, absolute BeatGrid-Abbildung, begrenzte Grain-Streckung, Tonartwarnung und manuelle Transposition, Pegelgrenze.
- Acid Transformer: Basic-Pitch-Noten bzw. WP10-Frames, Onset-Fallback mit vorgegebener Tonhöhe, Resonanz, Drive, Slide, Akzent, Oktave und Bass-Ausblendung.
- Gemeinsamer Scheduler über vorhandenen AudioCore; Offline-Rack-Preset, JSON-Presets v1 und Einbauhook WP14. Neun synthetische Demos, kein Download.

## Abnahme und Belege
1. `tests/realtime/{drum_architect,stem_crossover,acid_transformer,performance_tools}.test.mjs`: Raster/Frames, Velocity, Korrektur, Pegel, Preset-Roundtrip, gemeinsame Play/Stop/Seek-Schnittstelle am Mock; absolute Rasterprüfung über zehn Minuten sowie je drei reproduzierbare Fixture-Demos. Erwartete Belege im CI-Lauf, nicht als bestanden gewertet, solange kein erfolgreicher Lauf vorliegt.
2. Fehlende Drum-Einzelstems, Tonartkonflikt, Stretch-Limit: Warnungen in den jeweiligen Node-Tests geprüft; bei zu großem Stretch wird Quelle übersprungen.
3. Hörprüfung **nicht gemessen**. `node benchmarks/performance/render.mjs <neues externes Verzeichnis>` rendert neun WAV-Dateien. Diese lokal im Browser hören; `python benchmarks/performance/report.py <baseline.json> <render.json> <neue Ergebnisdatei.json> --note "Name: Beobachtung"` je Demo mit Notizen, anschließend `python benchmarks/result.py <Ergebnisdatei.json>`. Keine Audiodateien ins Repo. Zielrechner Windows 11 / RTX 5080, GPU nicht erforderlich für Offline-PCM.
4. Sollprüfung `python -m unittest discover -s tests -v`. Lokaler Git-Zugriff blockiert (DNS: Could not resolve host: github.com). CI über GitHub maßgeblich. Register und Board nicht eigenständig verändert.

## Anpassungsbedarf / Abweichungen / Risiken
- WP06 und WP08 nicht verfügbar; nur bestehende Demucs-Stems, kein Modellimport. Anbindung über Hook, keine UI-Freigabe. Klassifikation der Drum-Onsets derzeit Eingabe durch Controller/Nutzer; keine automatische Einzelstem-Erkennung. Mono-Offline-Render, kein Echtzeitversprechen. Grain-OLA ist eine einfache Annäherung; Tonartkorrektur nicht automatisch, Warnung bei unklaren Konflikten. Hörbare Stretch-Artefakte, Übergänge und Rack-Latenz müssen am Zielrechner geprüft werden. Presets referenzieren Quellen-ID, nicht Audiomaterial. Keine externen Bibliotheken oder Modellgewichte; keine fremden Pins/Lizenzen erforderlich. Python 3.11 und Node 22 vorgesehen, Browser Web Audio API.
- Abhängigkeiten erneut gemergt: KETTE-22 51fdeb3, KETTE-24 2e8dd86, KETTE-25 295bde3, Integration dc2c872. Register aus Integration beibehalten; überlappende Audio-Core-Dateien in 22/25 waren blob-identisch.
- Rückbau: Hook nicht aktivieren, eigene drei JS-Module, eigene Tests, Benchmark und Hook entfernen; keine Bestandsdaten oder gemeinsamen Dateien betroffen.

## Übergabe
Fertig: Offline-Kern der drei Werkzeuge, Fixture-Tests, Hook und Hörskript. Offen: CI-Bestätigung, echte Browser-/Hörprüfung, automatische Drum-Klassifizierung und produktiver Controller (Hook, WP17). Nächster Schritt: PR-CI prüfen, Fehler korrigieren, Hörprüfung durchführen und G3 erst nach Freigabe setzen. Fehlerausgabe lokal: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. CI-Lauf 45453963346: 120 Python-Tests (1 Fehler, 4 übersprungen); Node: 67/68 bestanden. Fehler: Acid, assert.ok(x.track.some(v=>v!==0)), zwei auf denselben Rasterframe quantisierte Noten. Ursache: Slide von nicht gerenderter Vorgängernote (Frequenz 0); behoben durch Prüfung tatsächlich gerenderter Vorgängerstimme. Wiederholungs-CI erforderlich; Lauf 45454174421 durch neuere Pushes abgebrochen.
