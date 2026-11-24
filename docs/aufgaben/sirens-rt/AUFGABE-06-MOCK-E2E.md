# Aufgabe 06: Mock-Durchstich und Gate G2 (WP06)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Abschnitt „WP06“ und Kapitel 7 (Gate G2) in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt die Aufgaben 03, 04 und 05 voraus.

## Ziel

GPU-Manager, Audio-Kern und Oberfläche werden hinter dem Schalter `SIRENS_RT_ENABLED` verbunden. Echtes Testaudio läuft über denselben Weg wie später die Modelle durch einen deterministischen Gain/Delay-Mock, gesteuert aus der Oberfläche. Das ist der Nachweis für Gate G2.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- Hooks der Vorgänger: `docs/realtime/hooks/WP03.md`, `WP04.md`, `WP05.md`.
- `sirens/server.py`: Weiche nach `sirens/realtime/routes.py` aus Aufgabe 01.

## Umfang

1. Alle Adressen der Control plane in `sirens/realtime/routes.py` und `sirens/realtime/sessions.py` umsetzen (Sitzungen, Befehle, Jobs, Assets) mit Zustandsautomaten aus Aufgabe 01. Diese Aufgabe darf `sirens/server.py`, `sirens/config.py` und `.env.example` ändern, soweit die Hooks es verlangen.
2. Sitzung startet Sidecar und Mock-Worker über den Supervisor, gibt ein kurzlebiges Token aus; Oberfläche verbindet den Audio-Kern. Der Mock ist in Oberfläche und API als Testmodus benannt.
3. Assets und Quellen werden serverseitig über sichere Pfade aufgelöst; nichts schreibt in den Musikordner.
4. Skript `benchmarks/g2/` für den Koordinator: 30 Minuten Durchlauf, Underruns, Fixture-Deckung, Dry-Rückfall bei Worker-Kill, Ergebnis im Format aus Aufgabe 00.
5. README-Abschnitt „RTX Neural Lab (Testmodus)“: Einschalten, Grenzen. Diese Aufgabe darf `README.md` ändern.

## Nicht im Umfang

- Kein echtes Modell.
- Die alte CUDA-Sperre beim Claude-Start bleibt unverändert.

## Abnahme

1. Tests über HTTP: vollständiger Lebenszyklus einer Sitzung; Stopp durch Nutzer; Worker-Kill führt zu Zustand `error` bzw. Dry-Rückfall und keinem verwaisten Prozess; Gegendruck; alte Epoch → `stale_epoch`; simulierter Speichermangel → `busy_gpu`.
2. Negativ, je ein Test: falsches Token, fremde Origin, Pfad mit `..`, ungültiges PCM, zu große Anfrage.
3. Test: Hauptprozess importiert weiterhin nur die Standardbibliothek; mit Schalter aus antworten alle neuen Adressen `unavailable` und alle alten wie zuvor.
4. Test: Nach einem Durchlauf sind alle Quelldateien unverändert (Hash vorher und nachher).
5. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft Gate G2: 30 Minuten stabil, Deckung höchstens 1 Sample.
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
