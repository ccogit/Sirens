# Vergabe und Parallelisierung

## Register für das Werkzeug `ketten` (maßgeblich für Branch und Stand)

Vergeben wird mit dem Werkzeug `ketten` (`.ketten.json` auf diesem Zweig). Kette KETTE-P0x = Auftrag K0x;
Branch `extern/KETTE-P0x` (ersetzt `feat/production-k0x-…` unten), ein PR auf `integration/sirens-production`.
Owner-Dateien je Kette: Tabelle weiter unten. Den Stand pflegt nur der Koordinator.

| Kette | Titel | Aufgaben | Voraussetzung | Stand |
|---|---|---|---|---|
| KETTE-P00 | Runner, Verträge, Mock-Durchstich (Umfang 1–2) | K00 | – | gemergt |
| KETTE-P01 | Persönliches Referenzwissen | K01 | – | gemergt |
| KETTE-P02 | Komposition, Groove, Dramaturgie | K02 | – | gemergt |
| KETTE-P03 | Instrumente und Offline-Rendering | K03 | – | gemergt |
| KETTE-P04 | Generative Klangbausteine, Spoken Word | K04 | – | gemergt |
| KETTE-P05 | Mixing und Mastering | K05 | – | gemergt |
| KETTE-P06 | Qualitätsbenchmark und schlanke Oberfläche | K06 | – | gemergt |
| KETTE-P07 | Ableton-Adapter, Export/Return | K07 | – | gemergt |
| KETTE-P08 | Integration: echter CLI-Durchstich, Signal-Room, Export (K00 Umfang 3) | K08 | KETTE-P00 gemergt, KETTE-P01 gemergt, KETTE-P02 gemergt, KETTE-P03 gemergt, KETTE-P04 gemergt, KETTE-P05 gemergt, KETTE-P06 gemergt, KETTE-P07 gemergt | gemergt |
| KETTE-P09 | Mix byte-reproduzierbar (Folge aus K05/K08) | K09 | – | gemergt |
| KETTE-P10 | Instrument-Host unter Windows | 10 | – | vergeben (24.11.2026) |
| KETTE-P11 | PCM24-Extensible und Sprache im Worker | 11 → 12 | – | vergeben (24.11.2026) |
| KETTE-P12 | AMM-Export, Inventur, Benchmark-Messung | 13 → 14 → 15 | – | vergeben (24.11.2026) |
| KETTE-P13 | Laufzeiten je Stufe | 16 | – | vergeben (24.11.2026) |
| KETTE-P14 | Mix: Bass ist nicht Sub | 17 | – | vergeben (24.11.2026) |
| KETTE-P15 | Preview-Plan aus Sprachdauern | 18 | – | vergeben (24.11.2026) |

**Begriffe:** *Aufgabe* = Datei `AUFGABE-nn-….md` mit eigener Abnahme. *Kette* = eine oder mehrere Aufgaben in
fester Reihenfolge, ein Branch, ein PR. Abhängigkeiten zwischen Aufgaben derselben Kette erledigt die Reihenfolge,
zwischen Ketten die Spalte „Voraussetzung“. Schnitt: hohe Kohäsion innerhalb, geringe Kopplung zwischen Ketten.
Die Dateien `AUFGABE-K00` … `K08` beschreiben je eine (gemergte) Kette; ihre Umfangspunkte waren die Aufgaben.
Neue Arbeit wird nach dem Ziel geschnitten, nicht nach Form: Aufgaben, die dieselben Dateien ändern, in eine
Kette; Ketten mit getrennten Dateien laufen parallel, Abhängigkeiten nur, wo Code gebraucht wird.

### Regeln für Bearbeiter (gelten vor den Formulierungen weiter unten)

1. **Früh pushen, keine CI.** Nach dem ersten Commit sofort `extern/KETTE-P0x` pushen und einen Draft-PR auf
   `integration/sirens-production` öffnen. GitHub Actions ist abgeschaltet (seit 24.11.2026): Es gibt keine
   CI-Läufe, nicht darauf warten. Die maßgebliche Prüfung (`py -3.11 -m unittest discover -s tests -v` unter
   Windows) macht der Koordinator nach „Ready for review“. Tests müssen unter Linux und Windows laufen (keine
   Symlinks ohne `try/except OSError` + skip, Pfade mit `pathlib`, Textdateien mit `encoding="utf-8"`).
   „Lokal nicht ausführbar“ ist nie ein Grund, nicht zu pushen.
2. **Nie ohne PR enden.** Bei Blockade: Stand pushen, in `ergebnisse/K0x.md` einen Abschnitt „Übergabe“ (fertig,
   offen, nächster Schritt), PR mit Titelanfang `ÜBERGABE` auf Ready for review. Der Koordinator übernimmt.
3. **Was nur am Zielrechner geht** (Live, Plugins, GPU, lokaler Katalog, AMM/SecondRoom-Dienste, Hörtests):
   als Skript oder CLI-Befehl liefern, Aufruf und erwartetes Ergebnisformat in `ergebnisse/K0x.md`, dort als
   „nicht gemessen“ ausweisen. Das hält den PR nicht auf; der Koordinator misst und berichtet nach.
4. **Gerüst vorhanden:** `sirens/production/__init__.py` und `tests/production/__init__.py` existieren bereits;
   nicht ersetzen. Gemeinsame Fixtures nur K00 (`tests/production/fixtures/`); andere Ketten legen eigene
   Minimal-Fixtures in ihren eigenen Testdateien an (temporäre Ordner, erzeugte WAVs).
5. **Vertrag aus K00 benutzen, sobald da:** Liegt auf `origin/extern/KETTE-P00` oder dem Zielzweig bereits
   `sirens/production/contracts.py`, diesen Branch hineinmergen und die Validatoren benutzen (nicht ändern).
   Passt etwas nicht: unter „Anpassungsbedarf“ in `ergebnisse/K0x.md` nennen und im eigenen Modul überbrücken.
6. **Imports nur lazy** auf Module anderer Ketten; fehlt ein Nachbar, Mock aus CONTRACT.md im eigenen Test.
7. **Abschluss:** Alle Punkte fertig, CI grün: PR auf Ready for review. Nicht selbst mergen.

### Engpässe (pflegt der Koordinator)

Was die Externe nicht kann und deshalb parallel zu den Ketten am Zielrechner läuft. Stand 24.11.2026.

| Engpass | Wer | Schaltet frei | Stand |
|---|---|---|---|
| Gerüst `sirens/production`, `tests/production` | Claude | konfliktfreie parallele PRs | erledigt (dieser PR) |
| Offline-Host: DawDreamer + Surge XT (VST3 vorhanden) in Worker-venv, Render-Rauchtest | Claude | K03 Hostwahl, G1 | erledigt: DawDreamer 0.9.0 + Surge XT 1.3.4, Laden 2,2 s, 8,6 s Audio in 0,06 s, 48 kHz, kein NaN |
| Ableton Live / Producer Pal: Capability-Probe im neuen Test-Set | Claude | K07 Spike, K03 | erledigt: Live 12.4.25b1 (Beta; 12.4.16 Suite ohne Pal), Pal 2.5.0; Tempo, Skala, Locators, Spuren, natives Instrument, Arrangement-MIDI mit Readback, WAV-Import ohne Warp ja; Speichern/Rendern unbeaufsichtigt nein |
| AMM-WB (Port 8000, PostgreSQL) und SecondRoom (Port 8099) lokal starten | Claude | K01 echte Geschmacksdaten, K04 Samples, K05 Ketten | prüfen |
| Lokaler TTS-Kandidat (Qwen3-TTS) laden und messen | Claude | K04 Spoken Word, G1 | erledigt: 1.7B-VoiceDesign (Apache-2.0), bf16 cuda, VRAM 4,1 GB, warm 9,4 s für 5,1 s Sprache (RTF 1,8), 24 kHz |
| Clear-Head-Lyrics/Original im lokalen Katalog finden | Claude | K02, B0 | offen |
| Hörurteile G1 (3 Groove-Varianten), B2/G3 (12 Blind-A/B) | Nutzer | G1, G3 | nach K08 |
| Ableton-Roundtrip (Export in Live, Return) | Nutzer (ein Exportdialog) | G2 Ableton | nach P07 |
| Merge nach `main` | Nutzer | Abschluss | nach G2/G3 |

Ziel: integration/sirens-production. Jede Kette erhält einen Branch feat/production-k0X-<name> vom Plan-Commit bzw. freigegebenen Stand, einen eigenen Worktree und einen PR auf den Integrationsbranch. Nie direkt auf main. A0 allein merged und passt gemeinsame Dateien an. Alte .ketten.json und RT-Ketten bleiben unangetastet, damit die laufende Realtime-Entwicklung nicht umgelenkt wird. Dieses Register ist separat; bei Nutzung eines externen Ketten-Orchestrators dessen Konfiguration im eigenen Worktree bewusst auf dieses Register umstellen.

| Kette | Aufgabe | Owner-Dateien (Präfixe) | Start | Integration | Stand |
|---|---|---|---|---|---|
| K0 | Runner und Contract | sirens/production/{__init__,__main__,contracts,runner,jobs,cache,gpu,integration}.py; sirens/production/schemas/; tests/production/test_runner*,test_contract*,test_jobs*,test_integration*; tests/production/fixtures/; __init__.py; gemeinsame App-/Config-/Route-Dateien | sofort | zuerst Mock, zuletzt real | offen |
| K1 | Referenzwissen | sirens/production/references.py; tests/production/test_references*; workers/production_analysis/ | sofort | K0 | offen |
| K2 | Songplanung | sirens/production/arrangement.py; sirens/production/templates/; tests/production/test_arrangement* | sofort | K0; real K1 | offen |
| K3 | Instrumentenrender | workers/production_instruments/; sirens/production/instruments.py; tests/production/test_instruments* | sofort | K0; real K2/K4 | offen |
| K4 | Sounddesign/TTS | workers/production_assets/; sirens/production/assets.py; tests/production/test_assets* | sofort | K0; real K2 | offen |
| K5 | Mix/Master | workers/production_mix/; sirens/production/mixing.py; tests/production/test_mixing* | sofort | K0; real K3/K4 | offen |
| K6 | Qualitätsbenchmark/UI | sirens/production/quality.py; benchmarks/production/; web/js/production.js; web/production.css; tests/production/test_quality*; tests/production_ui.test.mjs | sofort | K0; real alle | offen |
| K7 | Ableton-Adapter, Export/Return | sirens/production/ableton.py; workers/production_ableton/; tests/production/test_ableton* | sofort | K0; echte Live-Installation für Spike/Roundtrip | offen |

Jede Kette darf ausschließlich eigene Pfade ändern und docs/aufgaben/sirens-production/ergebnisse/K0X.md hinzufügen. Neue Tests mit eindeutigen Dateinamen, kein gemeinsames Testfile bearbeiten. Gemeinsame Dateien (server.py, config.py, .env.example, signal_tools.js, index.html, CI, README, CONTRACT.md) nur K0. Keine individuellen Änderungen an Realtime-GPU-Policy. Bei Schnittstellenbedarf PR-Kommentar mit Vorschlag; Lead entscheidet. K6 liefert UI-Modul ohne Registereintrag; K0 bindet es erst nach funktionierendem CLI-Durchstich ein.

## Wiederverwendung ist Abnahmekriterium

Vor jeder Implementierung REUSE-AMM.md lesen. K07 prüft zuerst den bereits vorhandenen Producer-Pal-/SecondRoom-/WB-Pfad, kein neues Live-Steuerungsframework. K03 verwendet vorhandene Instrument-/Preset-/Offline-Renderer, K05 deliver_chain und mastering_engine, K04 vorhandene Sample-/Lieferpfade, K01 AMM-Geschmacksdaten, K02 bestehende Plan-/Groove-Werkzeuge, K06 vorhandene Blindtest-/Messlogik. Alle Ketten liefern Reuse-Tabelle. Nur K00 koordiniert nötige kleine Upstream-PRs; keine neue DB/GUI/Writer. Realer Live-Pilot nur über Claude/Producer Pal, WB-Capture nach exklusivem Handoff. Codex kann parallel planen und entwickeln, nicht gleichzeitig Live verändern.

## Wellen

Welle A: Alle acht Ketten sofort parallel mit Contract/Mocks. Mit zwei Agenten Codex K0/K3/K5, Claude K1/K2/K4; K6 an den zuerst freien. K07 als zusätzliche Agentensitzung möglichst sofort, sonst nach K0/K1: kurzer Live-Capability-Spike vor oder parallel zur K03-Hostwahl. K03 startet mit Offline-Host/Mock unabhängig. K07 besitzt alle Ableton-Dateien und nutzt Mock-WAV/MIDI; K03/K05 verwenden nur den Adaptervertrag. K06 nutzt Mock-Capabilities; K0 verdrahtet die CLI/UI.  A0 kann auch ein separater Lead sein. K0-PR (Mock) zuerst mergen; die restlichen PRs können nach eigenem Test in beliebiger Reihenfolge folgen, sofern Imports nicht auf fehlende Nachbarn angewiesen sind (lazy adapter / mocks). 
Welle B: K07 realer Export-/Import-Roundtrip parallel zur Pipeline, Live-Tests exklusiv (ein Test-Set, eine Instanz, kein fremdes Projekt). Ableton-Render nur bei bestandenem Spike, sonst Standardhost ohne Wartezeit; K1 lokale Referenzanalyse; K2 realer Plan; K3 und K4 unabhängig implementiert, GPU-Runs zeitlich einzeln; K3 platziert fertige Assets; K5 mischt; K6 prüft; A0 integriert. 
Welle C nur bei Qualitätsbedarf: K2/K3/K4/K5 gezielt auf Basis blinder Bewertungen nachbessern, kein Architekturwechsel ohne Beleg. Kritischer Pfad K1→K2→max(K3,K4)→K5→K6. K0 paralleler Enabler und letzter Integrationstest. Ableton-Pfad K07→K0/K06; optionaler Renderpfad K07→K03/K05 nur bei positivem Gate, nicht Voraussetzung des Kernpfads.

## Vergabe-Prompt (pro Kette)

„Bearbeite K0X aus docs/aufgaben/sirens-production. Lies PLAN.md, CONTRACT.md, KETTEN.md und deinen Einzelauftrag. Arbeite ausschließlich in deinem Worktree/Branch und in den genannten Pfaden. Implementiere echte Funktion, keine Attrappen außerhalb von Tests. Benutze Contract-Mocks für fehlende Nachbarn. Keine lokalen Audiodateien, Bewertungen, Secrets, Gewichte oder Lizenzverletzungen in Git. Teste offline, dokumentiere ausgeführte Befehle, Messwerte, Blocker und offene Hörtests in ergebnisse/K0X.md. Erstelle PR auf integration/sirens-production; nicht auf main, nicht selbst mergen. GPU-/Download-Tests nur lokal nach Freigabe und mit bestehender Lease. Bei Konflikten gemeinsame Datei nicht eigenmächtig ändern.“

Ergebnisbericht: Status, Commit, veränderte Dateien, Tests tatsächlich ausgeführt/pass/fail, lokale Messwerte oder nicht_gemessen, Lizenz-/Kompatibilitätsstatus, Abnahmekriterien, verbleibende Risiken. A0 aktualisiert Register nach Merge. 
