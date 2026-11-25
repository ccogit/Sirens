# Aufgabe 10 – Kette KETTE-P10. Instrument-Host unter Windows ohne Handgriffe

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/instruments.py`, `workers/production_instruments/`, Tests `tests/production/test_instruments*`. Hintergrund: `ergebnisse/K03.md`, `ergebnisse/K08.md`.

## Befund
1. Der WB-Pfad (`WBWorker`, AMM `plugin_control.load`) braucht `pedalboard`; die dokumentierte Instrument-venv hat nur DawDreamer. Es lief nur mit dem globalen Python.
2. pedalboard lädt unter Windows den VST3-Bundle-Ordner `…\Surge XT.vst3` nicht („Unable to scan plugin“), nur die innere Datei `…\Surge XT.vst3\Contents\x86_64-win\Surge XT.vst3`.
3. AMM sucht Plugins und Presets nur unter `WORKBENCH_DATA_DIR/plugins` (Vorgabe `/data`); man musste die Variable setzen und Plugin und Presets kopieren.

## Umfang
1. Genau einen Host verbindlich festlegen und dokumentieren (pedalboard über AMM, wenn er reicht; sonst DawDreamer), mit Begründung. Installationsliste der Instrument-venv entsprechend (`workers/production_instruments/requirements*.txt` oder Install-Skript).
2. Bundle-Pfad unter Windows automatisch auflösen (Ordner `.vst3` → innere Datei), unter Linux/macOS unverändert.
3. Neuer Konfigurationsschlüssel `wb_data_dir` (SIRENS_PRODUCTION_CONFIG); WBWorker setzt `WORKBENCH_DATA_DIR` nur für den Worker-Prozess. Plugins/Presets dürfen außerhalb liegen: Preset-Suche über die Patch-Einträge (Pfad + sha256) statt Kopie.
4. Klare Fehlermeldung mit genau einer nächsten Handlung, wenn Host/Plugin/Preset fehlt.

## Abnahme
Tests mit gefälschtem Bundle-Ordner (Windows-Pfadlogik als reine Funktion), Umgebungsübergabe an den Worker (Mock), Fehlermeldungen. Lokaler Befehl für einen 1-Takt-Render in `ergebnisse/AUFGABE-10.md` (Koordinator misst).
