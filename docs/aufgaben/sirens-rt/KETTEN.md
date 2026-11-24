# Ketten: Vergabe und Zusammenarbeit

Die Aufgaben dieses Verzeichnisses werden als **Ketten** an externe Bearbeiter vergeben. Eine Kette ist eine
feste Folge von Aufgaben, die ein Bearbeiter in **einem** Branch und **einem** PR liefert. Der Koordinator
vergibt, prüft und merged.

Die Ketten bilden die Wellen aus `PLAN.md`, Kapitel 6, ab: Die erste Ziffer der Kettennummer ist die Welle.
Ketten derselben Welle laufen nebeneinander, sobald ihre Voraussetzungen gemergt sind.

## Register

| Kette | Titel | Aufgaben | Voraussetzung | Stand |
|---|---|---|---|---|
| KETTE-00 | Welle 0: Baseline und Testgerüst | 00 | – | gemergt |
| KETTE-11 | Welle 1: Verträge und Architektur | 01 | KETTE-00 gemergt | gemergt |
| KETTE-12 | Welle 1: Modell-Spikes (Berichte und Messskripte) | 02 | KETTE-00 gemergt | gemergt |
| KETTE-13 | Welle 1: Modell-Spikes Teil 2 – lauffähige Messpfade | 21 | KETTE-12 gemergt | gemergt |
| KETTE-14 | Welle 1: Messpfad DEMON | 22 | KETTE-13 gemergt | gemergt |
| KETTE-15 | Welle 1: Messpfad RAVE und AFTER | 23 | KETTE-13 gemergt | gemergt |
| KETTE-16 | Welle 1: Messpfad Magenta RealTime | 24 | KETTE-13 gemergt | gemergt |
| KETTE-21 | Welle 2: GPU-Manager und Worker-Supervisor | 03 | KETTE-11 gemergt | gemergt |
| KETTE-22 | Welle 2: Audio Core und Data Plane | 04 | KETTE-11 gemergt | gemergt |
| KETTE-23 | Welle 2: Live Lab Shell und GPU-Anzeige | 05 | KETTE-11 gemergt | gemergt |
| KETTE-24 | Welle 2: BeatGrid, Tonart, MIDI | 10 | KETTE-11 gemergt | gemergt |
| KETTE-25 | Welle 2: DSP Rack | 09 | KETTE-22 gemergt | gemergt |
| KETTE-26 | Welle 2: Advanced Stem Studio | 08 | KETTE-13 gemergt, KETTE-21 gemergt, Gate G1 Separation gemessen | gemergt |
| KETTE-27 | Welle 2: Semantic Stem Extractor | 13 | KETTE-21 gemergt, KETTE-13 gemergt | gemergt |
| KETTE-28 | Welle 2: Advanced Stem Studio Teil 2 – Dateijob und Verdrahtung | 25 | KETTE-26 gemergt | gemergt |
| KETTE-31 | Welle 3: Mock-Durchstich, Gate G2 | 06 | KETTE-21 gemergt, KETTE-22 gemergt, KETTE-23 gemergt | gemergt |
| KETTE-32 | Welle 3: Recorder, Session, Export | 16 | KETTE-22 gemergt | gemergt |
| KETTE-33 | Welle 3: DEMON Neural Remix Deck | 07 | KETTE-31 gemergt, KETTE-14 gemergt | gemergt |
| KETTE-34 | Welle 3: Neural Mutation (RAVE, AFTER) | 11 | KETTE-31 gemergt, KETTE-15 gemergt | gemergt |
| KETTE-35 | Welle 3: Generative Performance Pads | 12 | KETTE-31 gemergt, KETTE-24 gemergt, Gate G1 Stable Audio gemessen | gemergt |
| KETTE-38 | Welle 3: Performance Pads Teil 2 – Verdrahtung | 27 | KETTE-35 gemergt | gemergt |
| KETTE-36 | Welle 3: Generative Companion (optional) | 15 | KETTE-31 gemergt, KETTE-24 gemergt, KETTE-16 gemergt | gemergt |
| KETTE-37 | Welle 3: Performance-Tools | 14 | KETTE-22 gemergt, KETTE-25 gemergt, KETTE-24 gemergt | gemergt |
| KETTE-41 | Welle 4: Produktintegration und UX | 17 | KETTE-31 gemergt, KETTE-25 gemergt, KETTE-37 gemergt, KETTE-32 gemergt | gemergt |
| KETTE-43 | Welle 4: Produktintegration Teil 2 | 26 | KETTE-41 gemergt | gemergt |
| KETTE-42 | Welle 4: Infinite Mutation (optional) | 18 | KETTE-24 gemergt, KETTE-37 gemergt, KETTE-32 gemergt | gemergt |
| KETTE-44 | Welle 4: Alle offenen Hooks in die Oberfläche | 28 | KETTE-43 gemergt | gemergt |
| KETTE-45 | Welle 4: GPU-Regel, Profile, dauerhafter Supervisor | 29 | KETTE-43 gemergt | gemergt |
| KETTE-51 | Welle 5: Systemabnahme, Gate G4 | 19 | KETTE-41 gemergt, KETTE-43 gemergt, KETTE-28 gemergt | gemergt |
| KETTE-52 | Welle 5: Rollout und Release Candidate | 20 | KETTE-51 gemergt | vergeben (24.11.2026) |

Im Register steht als Voraussetzung nur, wessen **Code** gebraucht wird. Ketten werden **vorgezogen**: Sie
starten, sobald ihre Voraussetzung vergeben ist, und bauen auf deren Branch auf (Regel 11). Ketten zu echten
Modellen starten ohne gemessenes Gate: Sie bauen Worker und Adapter gegen den Messpfad und testen mit
nachgebautem Modell; die Fähigkeit bleibt abgeschaltet, bis der Koordinator das Gate gemessen hat; KETTE-37 und KETTE-41 arbeiten bis dahin
mit den vorhandenen Demucs-Stems und binden weitere Modelle nur über die Registry ein.

## Engpässe (pflegt der Koordinator)

Was die Externe grundsätzlich nicht kann und deshalb früh angestoßen wird. Stand 24.11.2026.

| Engpass | Wer | Schaltet frei | Stand |
|---|---|---|---|
| G1 RoFormer messen | Claude | KETTE-26 | erledigt: grün (offline) |
| Hugging-Face-Zugang SAM Audio, Stable Audio 3 | Nutzer | Messung → KETTE-27, KETTE-35 | Stable Audio: erledigt; SAM: Freigabe durch Meta ausstehend (403) |
| G1 SAM Audio, Stable Audio 3 messen | Claude | KETTE-27, KETTE-35 | Stable Audio: grün (lookahead); SAM wartet auf Zugang |
| Messpfade DEMON, RAVE/AFTER, Magenta | Externe | Messung → KETTE-33, 34, 36 | KETTE-14, 15, 16 |
| G1 DEMON, RAVE/AFTER, Magenta messen | Claude | KETTE-33, 34, 36 | nach KETTE-14/15/16; Magenta braucht vermutlich WSL2 |
| C++-Build-Tools für Pakete mit Quellbau | Nutzer (Installation) | nur falls ein Kandidat sie zwingend braucht | vermeiden (nur Wheels) |
| G2: 30 Minuten Mock-Durchlauf im Browser mit Ton | Claude | Freigabe KI-Integration | nach KETTE-31 |
| G3 je Funktion, Hörprüfung | Claude, Hörurteil Nutzer | Aufnahme ins Release | ab KETTE-41 |
| G4: 2 Stunden Soak | Claude, Beobachtung Nutzer | Merge KETTE-52 | läuft parallel zu KETTE-52 |
| Merge nach `main`, Release | Nutzer | Abschluss | am Ende |
| Parallele Codex-Arbeit an Song-/Albumliste auf `main` | Claude | Konfliktfreiheit | `main` regelmäßig in den Integrationszweig mergen |

## Dateien je Kette

Parallele Ketten legen nur die Dateien ihrer eigenen Aufgabe an und ändern keine Datei einer anderen Kette.

| Kette | Eigene Dateien |
|---|---|
| KETTE-11 | `docs/realtime/*.md`, `docs/realtime/adr/`, `docs/realtime/examples/`, `sirens/realtime/contracts.py`, `pcm.py`, `mock.py`, `routes.py`, `schemas/`, `web/js/realtime/pcm.js`, `mock_api.js`, Weiche in `sirens/server.py`, `sirens/config.py`, `.env.example` |
| KETTE-12 bis KETTE-16 | `benchmarks/spikes/` (je Kette nur der Ordner ihres Kandidaten, dazu je eine Zeile in `benchmarks/spikes/README.md`) |
| KETTE-21 | `sirens/realtime/gpu_manager.py`, `worker_supervisor.py`, `model_registry.py`, `telemetry.py`, `workers/mock/`; in `routes.py` nur die Adressen `gpu` und `capabilities` |
| KETTE-22 | `web/js/realtime/audio_core.js`, `clock.js`, `ringbuffer.js`, `transport.js`, `worklet_processor.js`, `stem_adapter.js`, `sirens/realtime/sidecar.py`, `benchmarks/audio_core/` |
| KETTE-23 | `web/js/realtime/shell.js`, `api.js`, `capabilities.js`, `gpu_panel.js`, `controls.js`, `web/realtime.css`; Registrierung in `web/js/live_lab.js`, `web/js/main.js`, `web/index.html` |
| KETTE-24 | `sirens/realtime/music_analysis.py`, `web/js/realtime/beat_grid.js`, `benchmarks/beatgrid/` |
| KETTE-25 | `web/js/realtime/effects/`, `benchmarks/dsp/` |
| KETTE-32 | `web/js/realtime/recorder.js`, `sirens/realtime/recordings.py`, `benchmarks/recorder/` |
| KETTE-37 | `web/js/realtime/drum_architect.js`, `stem_crossover.js`, `acid_transformer.js` |
| KETTE-28 | `workers/separation/`, `sirens/realtime/stem_adapter.py`, `web/js/realtime/advanced_stems.js`, Dateijob in `worker_supervisor.py` und `routes.py`, `benchmarks/separation/` |
| KETTE-43 | gemeinsame Dateien (README Abschnitt 4 Punkt 7) außer den Dateien von KETTE-28 und KETTE-35 |
| KETTE-38 | `workers/stable_audio/`, `web/js/realtime/pad_scheduler.js`, `benchmarks/pads/`, Pad-Leiste als eigenes Modul unter `web/js/realtime/` |
| KETTE-35 | `workers/stable_audio/`, `web/js/realtime/pad_scheduler.js`, `benchmarks/pads/` |
| KETTE-44 | gemeinsame Dateien und `web/js/realtime/` (außer `gpu_panel.js`), `sirens/realtime/routes.py`, `sessions.py` |
| KETTE-45 | `sirens/realtime/gpu_manager.py`, `worker_supervisor.py`, `model_registry.py`, `telemetry.py`, `web/js/realtime/gpu_panel.js`, CUDA-Sperre in `sirens/server.py` |
| KETTE-31 | `sirens/realtime/sessions.py`, alle Adressen in `routes.py`, Einbau aller Hooks, `benchmarks/g2/` |

Jede Kette schreibt außerdem ihre Tests unter `tests/realtime/` (Dateinamen mit dem eigenen Thema, z. B.
`test_gpu_manager.py`, `audio_core.test.mjs`), ihre Ergebnisdatei und bei Bedarf `docs/realtime/hooks/WPnn.md`.
`docs/realtime/board.md` pflegt **nur der Koordinator**; die Zeile „board.md ist fortgeschrieben“ in den
Aufgaben entfällt.

Den Stand ändert nur der Koordinator (`offen`, `vergeben (TT.MM.JJJJ)`, `gemergt`, `gesperrt`). Bearbeiter
reservieren nichts und ändern diese Datei nicht.

## Regeln für Bearbeiter

1. **Ein Branch, ein PR, Zielzweig `integration/sirens-rt`.** Branch `extern/KETTE-nn` vom aktuellen
   `origin/integration/sirens-rt`. Früh genau einen Draft-PR `extern/KETTE-nn` → `integration/sirens-rt`
   öffnen (Basis im PR ausdrücklich auf `integration/sirens-rt` stellen, nicht `main`). Keine Einzel-Branches
   oder Einzel-PRs je Aufgabe.
2. **Reihenfolge.** Die Aufgaben der Kette in der Reihenfolge des Registers. Commits je Aufgabe mit Präfix
   `AUFGABE-nn: …`. Umfang und Abnahme stehen verbindlich in `AUFGABE-nn-….md` und im Abschnitt „WPnn“ von
   `PLAN.md`; gemeinsame Bedingungen in `README.md` dieses Verzeichnisses.
3. **Ergebnis je Aufgabe.** Eine Datei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-nn.md`: was umgesetzt
   wurde, je Abnahmepunkt der Beleg (Test, Befehl, Ausgabe), was nicht geprüft werden konnte („nicht
   gemessen“ samt Skript und Aufruf für den Koordinator), Abweichungen von der Aufgabe mit Grund, Versionen,
   Pins und Lizenzen fremder Projekte, offene Risiken, Rückbau.
4. **Früh pushen, keine CI.** Nach dem ersten Commit sofort pushen und den Draft-PR öffnen; danach in
   kleinen Schritten weiter pushen. GitHub Actions ist abgeschaltet (seit 24.11.2026): Es gibt keine CI-Läufe,
   nicht darauf warten. Die maßgebliche Prüfung (`py -3.11 -m unittest discover -s tests -v` unter Windows)
   macht der Koordinator nach „Ready for review“; Tests müssen unter Linux und Windows laufen. Ein lokal nicht
   geprüfter Stand ist nie ein Grund, nicht zu pushen oder keinen PR zu öffnen.
   Tests zu jeder Änderung, ohne Netz, ohne GPU, ohne Modellgewichte.
5. **Nie ohne PR enden.** Jede Antwort im Chat, die die Arbeit beendet, setzt einen gepushten Stand und einen
   PR voraus. Ist alles fertig und die CI grün: Ready for review. Geht es nicht weiter (Blockade, CI bleibt
   rot, Umfang nicht zu schaffen): Stand pushen, in der Ergebnisdatei einen Abschnitt „Übergabe“ schreiben
   (fertig, offen, nächster Schritt, Fehlerausgabe) und den PR **trotzdem auf Ready for review** setzen, mit
   „ÜBERGABE“ am Anfang des PR-Titels. Der Koordinator übernimmt dann den Branch. Ein Draft, an dem niemand
   arbeitet, ist der einzige falsche Zustand.
6. **Aktuell bleiben.** Regelmäßig `origin/integration/sirens-rt` in den Branch mergen (kein Force-Push, kein
   Rebase nach dem ersten Push), Konflikte selbst lösen.
7. **Grenzen.** Kein Torch- oder Modell-Import im Paket `sirens/`. Keine Modellgewichte, Musikdateien oder
   Downloads im Repo. Gemeinsame Dateien (README, Abschnitt 4, Punkt 7) nur ändern, wenn die Aufgabe es
   ausdrücklich erlaubt; sonst den Einbau als Hook in `docs/realtime/hooks/WPnn.md` beschreiben. Keine
   Secrets. Nichts außerhalb des Umfangs der Aufgaben ändern; Auffälliges außerhalb des Umfangs steht in der
   Ergebnisdatei unter „Beobachtungen“.
8. **Keine erfundenen Messwerte.** Was die Zielhardware, einen Browser mit Tonausgabe oder ein echtes Modell
   braucht, wird als Skript geliefert und als „nicht gemessen“ ausgewiesen. Der Koordinator misst.
9. **Durcharbeiten.** Ohne Rückfrage Aufgabe für Aufgabe weiter. Bei einer echten Blockade die Annahme in der
   Ergebnisdatei festhalten und mit der sinnvollsten Auslegung weiterarbeiten.
10. **Vorgezogene Ketten.** Sagt der Auftrag, dass eine Voraussetzung noch nicht gemergt ist: Branch von
    `origin/integration/sirens-rt` anlegen und als Erstes `origin/extern/KETTE-xx` (den Branch der
    Voraussetzung) hineinmergen; vor dem Abschluss erneut mergen. Dessen Dateien nur benutzen, nicht ändern.
    Passt dort etwas nicht oder fehlt noch etwas: in der Ergebnisdatei unter „Anpassungsbedarf“ nennen und im
    eigenen Modul überbrücken (kleiner Adapter), nicht warten. Ist der Branch der Voraussetzung noch leer:
    gegen deren Aufgabendatei und `PLAN.md`, Kapitel 4, entwickeln.
11. **Abschluss.** Sind alle Aufgaben der Kette fertig und die CI grün: PR auf „Ready for review“ setzen, im
   PR-Text je Aufgabe: WP, Depends-on, Änderungen, Tests, Hardwaremessung oder ausdrücklich „nicht gemessen“,
   Risiken, Rollback. Der Koordinator prüft und merged den Ketten-PR als Ganzes. Nacharbeit kommt als
   Nachricht im Chat der Kette; der PR ist dann nicht abgeschlossen.
