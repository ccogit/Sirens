# AUFGABE-28 – Hooks in die Oberfläche (WP28) – ÜBERGABE

Depends-on: WP07, 08/25, 09, 11, 12/27, 13, 14, 15, 17/26, 18.
Branch extern/KETTE-44, PR #35 gegen integration/sirens-rt. Ausgangspunkt
03b18f6492377aeaf8b25dda706c7b74b07747a9; aktueller Integrationsstand
1637a21acf4dd79dffecc0f255b9125726c0d7c0 per Zweieltern-Merge ea26f9e1835cdf1ec1e4bbae2d9ed757d4670d35
übernommen (keine eigenen Registeränderungen, kein Force-Push).

## Umgesetzt

- Shell zeigt 13 Hook-Karten unabhängig von Registry-Reihenfolge und fehlenden
  Deskriptoren: DEMON, RoFormer, DrumSep, RAVE, AFTER, Performance Pads,
  Semantic Stem Extractor, Companion, DSP Rack, Drum Architect, Stem
  Crossover, Acid Transformer und Infinite Mutation. Deskriptor-Regler
  aus min/max/default; ganzzahlige Seeds/Steps, gesperrte Textfelder
  für noch nicht verifizierte Prompt-/Stilpfade. Keine Modellfreigabe
  durch eine vorhandene Karte oder Modusbezeichnung.
- GET /api/rt/v1/hook-status als separate lesende Diagnose, ohne Änderung
  des eingefrorenen Capability-Schemas. Host-/Origin-/Flag-Prüfungen
  wie die vorhandenen RT-Routen; keine Workerinitialisierung durch GET.
  Feste Modell-ID/G1-Datei-Zuordnung, boolescher Interpreter-/Berichtsstatus
  und Registry-Availability; keine Pfade im Ergebnis. G1-Datei vorhanden
  bedeutet nicht, dass ihr Inhalt, Gewichtshash oder Modellinstallation
  geprüft oder G3 bestanden ist. Fehlende Datei: nicht gemessen; fehlender
  Interpreter: nicht installiert; Registry false: gesperrt. API-Fehler
  werden angezeigt, bei fehlender Diagnose bleibt RoFormer gesperrt.
- WP08/25: vorhandenes mountSeparationJobs in Shell eingebaut, explizite
  Offline-Trennung, Ergebnis-Mix/A/B/Solo/Mute/Pegel und bestehender
  serverseitiger WAV-Export. RoFormer über Registry-ID separation und
  vorhandenen G1-Bericht; Demucs-CPU-Option nutzt bestehenden Backend-
  Prüfpfad, keine Behauptung einer vorab geprüften Demucs-Installation.
  Synthetische Mock-Fixture ist keine Trennquelle.
- Vorhören des Offline-Mixes per explizitem Klick auf denselben AudioCore-
  Ausgabemechanismus wie Mock; kein zusätzliches HTML-Audioelement in
  der Shell. Vor neuem Core wird Mock geschlossen, vor Mock-Aktion
  der Vorhör-Core zerstört. Exklusive AudioCore-Ownership, serialisierte
  Übergänge und Generation gegen spätes Play. Mixänderung stoppt die
  Vorschau; kein automatisches Abspielen. PCM bleibt lokal.
- Panic, Stop, Song-/Stem-/Capabilitywechsel und Verlassen räumen das
  Stem-Panel und den Vorhörpfad auf; ausstehende Startantwort mit Job-ID
  wird beim Verlassen abgewartet und abgebrochen. Kein erneuter Mount
  während laufender Panel-Schließung. Kein Profil-, Supervisor-, Registry-,
  GPU-Manager-, Telemetrie-, CUDA-Sperren- oder gpu_panel.js-Umbau.

## Abnahme und Belege

| Abnahmepunkt | Beleg | Stand |
|---|---|---|
| 28.1 Node je Modul, Sichtbarkeit, Zustände, Panic | tests/realtime/hook_tools.test.mjs (alle IDs, fehlende/gesperrte/verfügbare Deskriptoren, Fehler, Regler und Diagnose); tests/realtime/offline_preview.test.mjs (exklusives Vorhören, Panic während Öffnung); tests/realtime/separation_mount_28.test.mjs (kein Start bei Mount, Gate, Abbruch einer späten Job-ID). | Teilweise implementiert. Keine vollständige Bedien- oder Panic-Abnahme der noch gesperrten Module. |
| 28.2 HTTP komplett mit Mock ohne Leck | tests/realtime/test_hooks_28.py (Flag, Origin, Diagnose ohne Service-Start, Mock load/play/bypass/close und Worker-/Sidecar-Poll); bestehender tests/realtime/test_integration_26.py für Aufnahme und Export. | Test hinzugefügt; vollständiger neuer HTTP-/Browser-Ablauf nicht nachgewiesen. |
| 28.3 CI grün | GitHub Actions am PR #35; ältere Läufe 45465941686, 45466073437, 45466500045 cancelled; Merge-Lauf 45466617624 in_progress beim Abruf; 45466683263 pending beim letzten Abruf. | Kein bestätigtes Grün des Abschlussstands. |

Nachstellen: `python -m unittest discover -s tests -v` (Python 3.11, Node 22).
Einzeln: `node --test tests/realtime/hook_tools.test.mjs tests/realtime/offline_preview.test.mjs tests/realtime/separation_mount_28.test.mjs`.
Hardware-/Hörprüfung: nicht gemessen. Vorhandene Messpfade der jeweiligen
Hooks und `python -m benchmarks.integration.report <baseline.json> <beobachtungen.json> <ergebnis.json>`,
`python -m benchmarks.result <ergebnis.json>`; WP14:
`node benchmarks/performance/render.mjs <neues externes Verzeichnis>`.
Für WP18 und Pads sind die tatsächlichen taktscharfen Einsätze im Browser
und die Rückkehr zu Dry gesondert zu messen. Keine Audiodateien einchecken.

## Abweichungen, Grenzen, Risiken

- WP07 DEMON, WP11 RAVE/AFTER: keine echten Session-/PCM-/Lookahead-Adapter
  eingebaut. Dynamische Regler sichtbar, aber absichtlich nicht bedienbar.
  Für RAVE dynamische IPC-Controls und für AFTER Zwei-Quellen-Job klären.
- WP12/27 Pads: PadController/PadAudio nicht mit Backend, Grid und
  AudioCore-Epoch verbunden; persistenter Dateijob/Lifecycle (parallel
  KETTE-45) und G3-Insert-Quote offen. Kein fiktiver p95.
- WP13 SAM: Textprompt sichtbar/gesperrt; sicherer Text-Dateijob,
  Cache und Ziel-/Rest-Vorhören offen.
- WP15 Companion: keine Style-Referenz-Übertragung, getrennte Spur,
  MIDI- oder Job-Lifecycle-Integration. Kein Textkonditionierungsversprechen.
- WP09 DSP, WP14 Drum/Crossover/Acid, WP18 Mutation: sichtbare gesperrte
  Karten, noch keine vollständige Bedien-/Render-/Taktplanung, Quellen-
  und Preset-Integration, Automationstimeline oder G3-Hörfreigabe.
- Die Gate-Diagnose prüft nur die erwarteten G1-Berichtsdateinamen und
  Interpreterexistenz, nicht Inhalte, Revisionen oder Gewichte; bei
  zukünftigen anders benannten Berichten ist die Zuordnung anzupassen.
  Registry bleibt maßgeblich. Offline-Separation muss am Zielrechner
  einschließlich Demucs-Abhängigkeiten, RoFormer-GPU-Budget und
  tatsächlich installierten Gewichten geprüft werden.
- Ein vor Job-ID-Antwort gescheiterter HTTP-Startrequest ohne ID kann
  vom Browser nicht sicher storniert werden. Serverjob-Timeout und
  tatsächliche Prozessbeendigung bleiben Backend-Verantwortung.
  Keine neue Garantie für Netzwerkfehler oder echte Hardware.
- Keine neuen fremden Projekte, Versionen, Pins, Lizenzen oder Gewichte.
  Python 3.11 Standardbibliothek, ES-Module ohne Build, Node 22.
  Zielrechner Windows 11/RTX 5080 16 GiB, Browser mit AudioWorklet;
  Latenz, VRAM und Klang nicht gemessen. Keine Änderungen an eingefrorenen
  Schemata, Katalog, Song-/Albumliste oder Board.

## Übergabe

**Fertig:** Hook-Sichtbarkeit, lesende Installations-/G1-Diagnose,
Deskriptor-Regler in gesperrten Karten, WP25-Panel mit gemeinsamem
exklusivem AudioCore-Mechanismus, Panic/Schließen des Vorhörpfads,
Regressionstests für diese Teilpfade; gepusht.

**Offen:** vollständige funktionale Einbindung der oben aufgeführten
Hooks, echte Modell- und CPU-Werkzeug-Adapter, vollständige gemeinsame
Panic/Player-Abnahme und G3 je Funktion. AUFGABE-28 ist nicht abgeschlossen.

**Nächster Schritt:** CI des letzten Commits prüfen und Fehler beheben;
danach zuerst den DSP-/Performance-Pfad unter G3 und die Mock-HTTP-
Abnahme vervollständigen, dann die Backend-Verträge für die echten
Modellpfade und den Pad-Lifecycle mit KETTE-45 abgleichen. Keine
Freigabe ohne Gate, Installation und nachgewiesenen Bedienpfad.

**Fehlerausgabe/Blockade:** Vollständiger lokaler Checkout scheiterte mit
`fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
GitHub-API-Schreibzugriff funktioniert. Tests lokal nicht ausgeführt,
CI-Abschlussstand nicht bestätigt; ältere Läufe abgebrochen bzw. noch
in_progress/pending beim Abruf. Der Restumfang konnte in der verfügbaren
Bearbeitung nicht abgeschlossen werden. Nicht auf eine lokale Prüfung
gewartet: Branch und PR früh angelegt und Teilstände gepusht.

**Rollback:** PR nicht mergen oder ausschließlich AUFGABE-28-Änderungen
revertieren. SIRENS_RT_ENABLED=0 erhält Bestand. Keine Originale oder
vorhandene Exporte automatisch löschen; kein Force-Push.
