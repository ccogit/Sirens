# Aufgabe 05: Live Lab Shell und GPU-Anzeige (WP05)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Kapitel 4 („UI-Contract“) und Abschnitt „WP05“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 01 voraus.

## Ziel

Im Live Lab gibt es einen neuen Bereich „RTX Neural Lab“: Song- und Stem-Auswahl, Transport, Presets, A/B, Dry/Wet, Panic, Anzeige von Latenz und GPU, Installationshilfe und klare Moduskennzeichen. Er arbeitet vollständig gegen die Mock-API und zeigt ehrlich, was nicht verfügbar ist.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- `web/js/live_lab.js`: Navigation und Wechsel der Spielzeuge im Live Lab samt Aufräumen beim Verlassen. `web/js/main.js`: Einstieg der Seite. `web/js/dom.js`: Helfer `h(...)` zum Bauen von Elementen. `web/js/api.js`: bestehende API-Aufrufe (bleibt unverändert). `web/live_lab.css`, `web/theme.css`, `web/modern.css`: bestehende Gestaltung („Quiet Glass“, dunkles Thema).
- Offener Draft-PR #5 (`ui/live-lab-tool-library`) ändert `web/js/live_lab.js` und `web/live_lab.css`. Eingriffe dort deshalb so klein wie möglich halten (eine Registrierung).

## Umfang

1. `web/js/realtime/api.js` (Aufrufe der Control plane; umschaltbar auf `mock_api.js`), `capabilities.js`, `shell.js`, `gpu_panel.js`, `controls.js` und `web/realtime.css`.
2. Lebenszyklus `mount` / `pause` / `destroy` nach dem UI-Vertrag; ein Adapter bindet ihn an die heutige Logik in `web/js/live_lab.js`. Diese Aufgabe darf `web/js/live_lab.js`, `web/js/main.js` und `web/index.html` ändern, aber nur für die Registrierung des neuen Bereichs und das Einbinden der CSS.
3. Zustände sichtbar und verständlich: Schalter aus, keine GPU, kein Modell installiert, Mock aktiv (als „Testmodus“ benannt), Fehler der API, leere Bibliothek, beschäftigt (`busy_gpu`).
4. Bedienung: Song und Stems wählen (bestehende Katalog-Adressen), Play/Pause/Seek, Dry/Wet, Bypass, Panic (alles stumm und Dry), A/B, Presets (lokal gespeichert), Moduskennzeichen Live / Lookahead / Offline je Fähigkeit, Latenz, Warteschlange, VRAM. Tastatur bedienbar; MIDI vorbereitet (Zuordnung als Datenstruktur, noch ohne Gerät).
5. Beim bloßen Öffnen startet nichts auf der GPU; Ton erst nach Nutzeraktion; nach Verlassen läuft kein Timer und kein zweiter AudioContext weiter.

## Nicht im Umfang

- Kein eigener Tonpfad: Der Audio-Kern kommt aus Aufgabe 04 und wird in Aufgabe 06 verbunden; bis dahin steuert die Oberfläche den Mock.
- Keine Änderung an `sirens/`.
- Keine neuen Frameworks ohne ADR.

## Abnahme

1. Node-Tests für die reinen Teile (Zustandsableitung aus Capabilities, Presets, Tastaturzuordnung): je Zustand aus Umfang 3 ein Test mit erwarteter Anzeige (Text und abgeschaltete Bedienelemente).
2. Test: Nach `destroy` sind alle Timer und Listener abgemeldet (Zähler im Test), kein zweiter AudioContext wird angelegt.
3. Negativ: API antwortet 503 oder unlesbar → Oberfläche zeigt den Zustand, wirft keinen Fehler.
4. Bestehende Spielzeuge im Live Lab sind unverändert erreichbar; `test_javascript_module_syntax` grün.
5. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: Sichtprüfung im Browser (Anleitung mit Schritten unter `docs/realtime/`).
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
