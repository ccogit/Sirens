# Aufgabe 04: Audio Core und Data Plane (WP04)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Plan: Kapitel 4 („Data plane“, „Zeitbasis“) und Abschnitt „WP04“ in
`docs/aufgaben/sirens-rt/PLAN.md`. Setzt Aufgabe 01 voraus.

## Ziel

Der Browser bekommt einen Audio-Kern mit einer einzigen Uhr: AudioWorklet mit Ringpuffer, Transport, Dry/Wet, Bypass, Limiter. Ein lokaler Sidecar-Prozess liefert PCM-Blöcke über WebSocket. Damit lässt sich später jedes Modell anschließen, ohne den Tonpfad anzufassen.

## Ausgangslage

- Verträge aus Aufgabe 01: `docs/realtime/` (`architecture.md`, `protocol.md`, `model-adapter.md`, `security.md`), `sirens/realtime/contracts.py`, Schemas unter `sirens/realtime/schemas/`, Mock in `sirens/realtime/mock.py` und `web/js/realtime/mock_api.js`. Sie sind eingefroren.
- `web/js/stem_audio.js`: heutiger Stem-Player (gemeinsamer AudioContext, synchron gestartete BufferSourceNodes, Gain). `web/js/live_audio.js`, `web/js/stem_synth.js`: weitere Tonquellen. Ihre Schnittstellen bleiben unverändert.
- PCM-Format und Kopf: `sirens/realtime/pcm.py`, `web/js/realtime/pcm.js` aus Aufgabe 01.

## Umfang

1. `web/js/realtime/ringbuffer.js`, `clock.js`, `transport.js`: reine Funktionen bzw. Klassen ohne DOM, unter Node testbar. Begrenzte Warteschlange, Lookahead-Grenze, Gegendruck, Verwerfen veralteter Blöcke nach Seek/Stop (Epoch), Zähler für Underruns.
2. `web/js/realtime/worklet_processor.js`: liest aus dem Ringpuffer, verarbeitet die tatsächlich angeforderte Blockgröße (keine Annahme von 128 Frames), keine Allokation und kein Netz im Callback; Übergabe zunächst über MessagePort mit Transferables.
3. `web/js/realtime/audio_core.js`: ein AudioContext, Mehrspur-Mixer, Dry/Wet mit Latenzausgleich, Gain-Rampen, Bypass, Schutzlimiter (Spitze höchstens −1 dBFS), samplegenaue Start-, Loop- und Seek-Epochs, Umrechnung der Abtastrate vor dem Callback. Nur ein aktiver Ausgabepfad je Suite.
4. `web/js/realtime/stem_adapter.js`: bindet den bestehenden Player aus `web/js/stem_audio.js` an, ohne ihn zu ändern.
5. Sidecar `sirens/realtime/sidecar.py` (nur Standardbibliothek, eigener Prozess, eigener WebSocket nach RFC 6455): hört nur auf Loopback, prüft Origin und kurzlebiges Sitzungs-Token, binäre PCM-Blöcke, Größen- und Ratengrenzen; Port dynamisch oder aus der Einstellung. Start und Überwachung als Hook für den Supervisor (Aufgabe 03) in `docs/realtime/hooks/WP04.md` beschreiben.
6. Messskript `benchmarks/audio_core/` für den Koordinator: 30 Minuten Mock-Wiedergabe im Browser mit Zählung der Underruns, Messung der Geräte-Latenz (Anleitung), Ergebnis im Format aus Aufgabe 00.

## Nicht im Umfang

- Keine Änderung an `web/js/stem_audio.js`, `web/js/live_lab.js`, `web/js/main.js`, `sirens/server.py`.
- Kein SharedArrayBuffer (erst nach ADR und Messung), kein nativer Host.
- Keine Effekte (Aufgabe 09), keine Oberfläche (Aufgabe 05).

## Abnahme

1. Node-Tests: Ringpuffer (voll, leer, Überlauf, Umlauf), Uhr und Transport; Impuls und zwei gleiche Spuren bleiben nach Latenzausgleich auf höchstens 1 Sample deckungsgleich; Seek verwirft Blöcke alter Epoch; künstlicher Jitter führt zu gezähltem Underrun und klickarmem Dry-Rückfall, nicht zu Müll.
2. Node-Tests: kein NaN, kein Inf, keine Spitze über −1 dBFS am Ausgang des Referenzpfads; Dry/Wet bei 0 ist bitgleich zum Eingang.
3. Python-Tests gegen den Sidecar (echter Loopback-Socket im Test): gültiger Strom kommt an; falsches Token, fremde Origin, zu großer Block, ungültiger Kopf und falsche Version werden getrennt bzw. abgelehnt; der Prozess endet sauber.
4. Negativ: verschiedene Abtastraten (44,1 und 48 kHz) werden umgerechnet, nicht falsch schnell abgespielt (Test über Signallänge und Frequenz).
5. Alles, was Zielrechner, Browser mit Tonausgabe oder ein echtes Modell braucht, kommt als Skript unter `benchmarks/` mit Aufruf und Ergebnisformat (`benchmarks/result.py`); in der Ergebnisdatei steht dafür „nicht gemessen“. Betrifft: 30 Minuten ohne unerwartete Underruns, Geräte-Latenz.
6. `python -m unittest discover -s tests -v` läuft durch; `docs/realtime/board.md` ist fortgeschrieben.
