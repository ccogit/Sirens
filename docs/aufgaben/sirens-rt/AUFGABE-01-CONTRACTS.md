# Aufgabe 01: Verträge und Architektur (WP01)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Kapitel 4 und
Abschnitt „WP01“ in `docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 00 voraus.

## Ziel

Nach dieser Aufgabe können alle weiteren Aufgaben unabhängig voneinander gegen feste, versionierte Verträge
entwickeln: Steuer-API, PCM-Format, Zeitbasis, Sitzungs- und Job-Zustände, Fehler, Modell-Adapter, Telemetrie.
Dazu gibt es Mock-Bausteine in Python und JavaScript. Echte Funktion entsteht hier noch nicht.

## Ausgangslage

- `sirens/server.py`: `ThreadingHTTPServer`; Routing in `do_GET`/`do_POST`, Prüfung von Host, Origin und JSON;
  statische Dateien über `_statisch`. Fehler als `Ablehnung` (`sirens/contracts.py`: Code, Meldung, Feld,
  Status).
- `sirens/config.py`: liest Einstellungen und `SIRENS_`-Zeilen aus `.env`.
- `sirens/contracts.py`: `safe_audio_path` löst Pfade sicher unter dem Musikordner auf.
- `auftrag.schema.json`: Beispiel für ein JSON-Schema im Repo.
- Aus Aufgabe 00: `tests/realtime/`, `benchmarks/fixtures.py`, `docs/realtime/adr/0000-vorlage.md`.

## Umfang

1. **Dokumente** unter `docs/realtime/`: `architecture.md` (Prozesse, Module nach der Struktur in `PLAN.md`
   Kapitel 4, Datenfluss, was wo läuft), `protocol.md` (Control plane und Data plane, Byte für Byte),
   `model-adapter.md` (Adapter-Lebenszyklus und Capability-Descriptor), `security.md` (Loopback, Origin,
   Token, Pfade, Grenzen für Größen und Raten, was ein Worker darf).
2. **ADRs** unter `docs/realtime/adr/`: Transport der Data plane (WebSocket-Sidecar; Begründung und
   Alternative), Zeitbasis (AudioContext als einzige Uhr), Worker-IPC (Format ohne Pickle, Heartbeat),
   Zulassung eines nativen Hosts und eines Build-Systems (nur nach Mess-Gate bzw. belegtem Nutzen),
   Schalter `SIRENS_RT_ENABLED`.
3. **Control plane v1** als Schema und Code: Adressen unter `/api/rt/v1/`: `GET capabilities`, `GET gpu`,
   `POST sessions`, `GET sessions/{id}`, `POST sessions/{id}/commands`, `POST sessions/{id}/close`,
   `GET jobs/{id}`, `POST jobs/{id}/cancel`, `GET assets/{id}`. Befehle: `load`, `play`, `pause`, `seek`,
   `set_param`, `schedule`, `bypass`. Sitzungszustände `created → loading → ready → playing/paused →
   stopping → closed` und `error`; Job-Zustände `queued/running/ready/error/cancelled`. Sitzungs-ID vom
   Server, Sequenznummer und Epoch je Transport-Generation. Fehlercodes mindestens `unavailable`, `busy_gpu`,
   `deadline_missed`, `stale_epoch`, `not_found`, `invalid`. JSON-Schemas unter `sirens/realtime/schemas/`.
4. **PCM v1**: Float32 little endian, Stereo interleaved, Kopf mit `protocol_version`, `stream_id`, `epoch`,
   `seq`, `start_frame` (uint64), `nframes`, `channels`, `sample_rate`, `flags`; Kopfgröße und Byteordnung
   festgelegt; 256 bis 2048 Frames je Block. `sirens/realtime/pcm.py` (packen, entpacken, prüfen, nur
   Standardbibliothek) und `web/js/realtime/pcm.js` (dasselbe, reine Funktionen ohne DOM).
5. **`sirens/realtime/contracts.py`**: Konstanten, Zustandsautomaten für Sitzung und Job mit erlaubten
   Übergängen, Prüfung von Befehlen, Capability-Descriptor (`mode`, `sample_rates`, `channels`,
   `context_frames`, `hop_frames`, `latency_frames`, `controls`, `vram_peak_bytes` oder `unknown`, `device`,
   `license`, `model_revision`), BeatGrid-Schema (BPM, `beat0`, `bar0`, `confidence`, optionale Tempo-Karte),
   Telemetrie-Schema, sichere Asset-IDs und Cache-/Sitzungspfade (aufbauend auf `safe_audio_path`). Fehler
   als `Ablehnung`.
6. **Mock**: `sirens/realtime/mock.py` (Mock-Adapter mit `probe`, `load`, `warmup`, `process`, `cancel`,
   `unload`, `health`; deterministischer Gain/Delay; als Mock gekennzeichnet) und `web/js/realtime/mock_api.js`
   (liefert dieselben Antworten wie die spätere API, für UI-Entwicklung ohne Backend). Beispieldaten unter
   `docs/realtime/examples/` (je Adresse Anfrage und Antwort, ein PCM-Block als Hex).
7. **Schalter**: `sirens/config.py` kennt `SIRENS_RT_ENABLED` (Vorgabe aus) und einen Ordner für
   Echtzeit-Cache und Sitzungen; `.env.example` beschreibt beides. Diese zwei Dateien darf diese Aufgabe
   ändern. `sirens/server.py` darf diese Aufgabe nur um eine einzige Weiche ergänzen: Adressen unter
   `/api/rt/v1/` gehen an `sirens/realtime/routes.py`; bei ausgeschaltetem Schalter antworten sie mit
   `unavailable` (Status 503). `routes.py` bedient in dieser Aufgabe nur `GET capabilities` (leere Liste plus
   Mock-Eintrag, wenn ein Testschalter gesetzt ist); alles andere `unavailable`.
8. `docs/realtime/board.md` fortschreiben (WP01).

## Nicht im Umfang

- Kein AudioWorklet, kein Sidecar-Prozess, kein GPU-Manager, keine Oberfläche (Aufgaben 03 bis 05).
- Keine Modellbibliothek, kein Download.
- Keine Änderung an bestehenden Adressen oder an `web/js/live_lab.js`, `web/js/main.js`.

## Abnahme

1. Tests: Jedes Beispiel unter `docs/realtime/examples/` besteht sein Schema; je Schema mindestens ein
   ungültiges Beispiel wird abgelehnt.
2. Tests: PCM packen und entpacken ist in Python und in JavaScript verlustfrei; ein in Python gepackter Block
   (als Hex im Repo) wird vom JavaScript-Test gleich gelesen und umgekehrt. Falsche Version, falsche
   Kanalzahl, `nframes` außerhalb der Grenzen und abgeschnittener Block werden abgelehnt.
3. Tests: Zustandsautomaten erlauben genau die festgelegten Übergänge; ein Befehl mit alter Epoch ergibt
   `stale_epoch`; unbekannter Befehl ergibt `invalid`.
4. Tests über HTTP (wie `tests/test_server.py`): Schalter aus → `/api/rt/v1/capabilities` antwortet 503 mit
   Code `unavailable`; Schalter an → 200 und gültig gegen das Schema; fremde Origin und fremder Host werden
   wie bei den bestehenden Adressen abgewiesen; alle bisherigen Adressen antworten unverändert.
5. Test: Kein Modul unter `sirens/` importiert etwas außerhalb der Standardbibliothek (Prüfung über die
   Importzeilen, wie `test_keine_fremden_importe` in `tests/test_web.py`).
6. Test: Mock-Adapter liefert bei gleichem Eingang gleichen Ausgang; Delay und Gain stimmen auf das Sample.
7. `python -m unittest discover -s tests -v` läuft durch.
