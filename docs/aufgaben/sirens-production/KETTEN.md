# Vergabe und Parallelisierung

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
