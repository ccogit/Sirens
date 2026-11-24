# AUFGABE-18 – Infinite Mutation (WP18)

## Umsetzung

- Reiner MutationScheduler mit 4/8/16-Takt-Blöcken auf dem WP10-BeatGrid, Seed, Intensität, Energie, manueller Übersteuerung und jederzeitiger Rückkehr zu Dry. Keine Timer im Scheduler.
- Reduzierter DSP-Modus: Adapter für DSP-Rack, Drum Architect, Stem Crossover und Acid Transformer (nur mit vorhandenen Quellen). Neuronale Adapter werden nur bei vorhandener Adapterfunktion und tatsächlich freigegebener, nicht als Mock gekennzeichneter Registry-Capability (DEMON/RAVE/AFTER, streaming/lookahead) angeboten; keine direkten Modellaufrufe oder Downloads.
- Begrenzte PCM-Blöcke, Peak maximal 0,8, Asset-Quota (standardmäßig 16, auch abgebrochene Anforderungen zählen), maximal eine ausstehende Vorbereitung standardmäßig, Modellwechselabstand acht Takte standardmäßig, Abbruchsignal und Verwerfen verspäteter/alter Ergebnisse.
- Session-Projektion über numerische WP16-set_param-Timeline-Einträge; Hook WP18 für KETTE-43 mit konkreter Verdrahtung, Seed/Quellhashes/Modellversionen, Rückbau und offenen Voraussetzungen.
- Eigenständiges Browser-Hörskript für drei jeweils 30-minütige Szenarien mit synthetischem PCM und separatem Registry-Nachbau. Keine Musikdateien oder Gewichte im Repository.

## Abnahme

| Punkt | Beleg / Stand |
|---|---|
| 1: gleicher Seed, 4/8/16 Takte, Taktgrenzen | tests/realtime/mutation_scheduler.test.mjs: Seed-Wiederholung, wechselndes Tempo, exakte geplante Quellframes, verspätete Ausgabe verworfen. Test angelegt, Ergebnis nicht bestätigt. |
| 1: Quota, Lautheitsgrenze, Modellwechsel | Node-Tests: Asset-Quota, Queue nach Abbruch, Mindestabstand für Wechsel, Freigabeentzug, PCM-Peak und NaN, tatsächliche DSP-/Performance-Adapter mit synthetischem PCM. Test angelegt, Ergebnis nicht bestätigt. |
| 1: Stop, Original, Override | Node-Tests: Abbruch, veraltete Ergebnisse, Rückkehr zu Original und Intensitätsänderung. Test angelegt, Ergebnis nicht bestätigt. |
| 2: 30 Minuten, mindestens drei Szenarien | **Nicht gemessen.** Im Repo-Wurzelverzeichnis `python -m http.server 8765 --bind 127.0.0.1`, im Browser `http://127.0.0.1:8765/benchmarks/mutation/soak.html` öffnen. Alle drei Szenarien nacheinander jeweils 30 Minuten laufen lassen; Stop/Original separat mitten im Block prüfen. JSON jeweils außerhalb des Repos speichern, mit `python benchmarks/result.py <datei.json>` validieren. Hörurteil, Deadline und Underruns separat am Produkt-Core prüfen; das eigenständige Skript erhebt nur Vorbereitungslatenzen, geplante/abgelehnte Blöcke und PCM-Peak. |
| 3: Gesamtprüfung | `python -m unittest discover -s tests -v` ist maßgeblich. Kein vollständiger lokaler Checkout möglich (DNS); Node-Tests ebenfalls nicht lokal ausgeführt. GitHub-Workflow-Abfrage bislang ohne Runs, Statusabfrage ohne Checks. board.md gemäß Kettenregel nicht geändert. |

Einzeltest: `node --test tests/realtime/mutation_scheduler.test.mjs`.
Abhängigkeiten: WP09, WP10, WP14, WP16, vorhandene Registry WP03; WP07/WP11 optional erst nach Freigabe. Keine neuen Fremdprojekte, Versionspins oder Gewichte/Lizenzen; bestehende Projektmodule unverändert genutzt. Zielumgebung Python 3.11, Node 22, Browser mit Web Audio. Für DSP- und Nachbaupfad keine GPU erforderlich; tatsächliche neuronale Hardwaremessung ausstehend.

## Abweichungen, Risiken und Rückbau

Der produktive AudioCore besitzt noch keine atomare, vorab zeitadressierte Blockübergabe für Mutation. Der Hook beschreibt den erforderlichen Anschluss in KETTE-43; bis dahin ist WP18 nicht als fertige Produktfunktion freizugeben. Ein Standalone-AudioContext ist nur im separaten Messskript vorhanden. Peak-Schranke ist keine LUFS-Messung, echte Lautheit und Übergänge müssen gehört werden. Das Browser-Skript ist keine G3-Messung am Produktpfad und die synthetische Registry kein echtes neuronales Backend. Session-Projektion ist getestet auf numerische Parameternamen/-werte, aber nicht end-to-end exportiert. Der Controller muss die vorhandene Timeline- und serverseitige Asset-Quota einhalten, Quell- und Masterframes korrekt abbilden, Audio- und Jobabbruch ausführen und Hintergrundrendering vom Audio-Callback fernhalten. Keine gemeinsamen Dateien oder Register geändert.

Rückbau: WP18-Hook nicht integrieren/aktivieren; übrige Pfade bleiben unverändert. Keine Migration und keine persistenten Daten durch den Scheduler.

## Übergabe

**Fertig (implementiert, nicht als CI-grün bestätigt):** Scheduler, DSP-/Registry-Adapter, Node-Tests, Hook, eigenständiges Drei-Szenarien-Hörskript, Ergebnisdokumentation.

**Offen:** maßgebliche CI-Prüfung und gegebenenfalls Korrekturen; produktive zeitadressierte Core-/Session-Integration durch KETTE-43; 30-Minuten-Hörprüfung und G3 am Zielrechner. Neuronale Backends erst nach deren Freigabe integrieren. Kein Gate als bestanden angegeben.

**Nächster Schritt:** GitHub-PR-Checks prüfen bzw. Workflow durch Koordinator auslösen; fehlgeschlagene Tests korrigieren. Danach WP18-Hook mit KETTE-43 abstimmen, drei Szenarien ausführen und am tatsächlichen Core nachmessen.

**Fehlerausgabe:** lokaler Git-Zugriff nicht möglich: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. GitHub-Connector lieferte für die abgefragten gepushten Commits `{"workflow_runs":[]}` und `{"statuses":[]}`; daraus folgt weder grüner noch roter CI-Status. Keine CI-Fehlerausgabe verfügbar.
