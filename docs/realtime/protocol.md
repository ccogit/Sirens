# Protokoll v1

## Steuer-API

Gleiche Origin, JSON UTF-8, Pfadpräfix /api/rt/v1/. Keine Inferenz im HTTP-Request. Fehler im Bestandformat {error, meldung, feld}; unavailable 503, busy_gpu/deadline_missed/stale_epoch 409, not_found 404, invalid 400. Host/Origin-Fehler 403. IDs sind servergenerierte 32 kleine Hexzeichen (UUID ohne Bindestriche).

| Methode und relativer Pfad | Anfrage | Erfolg |
|---|---|---|
| GET capabilities | – | 200 capabilities |
| GET gpu | – | 200 telemetry |
| POST sessions | session_create | 201 session |
| GET sessions/{id} | – | 200 session |
| POST sessions/{id}/commands | command | 200 session |
| POST sessions/{id}/close | {} | 200 session |
| GET jobs/{id} | – | 200 job |
| POST jobs/{id}/cancel | {} | 200 job |
| GET assets/{id} | – | 200 asset |

Schemas unter sirens/realtime/schemas. WP01 stellt nur capabilities bereit, übrige Pfade 503. Befehle enthalten command, epoch, seq, args; seq strikt steigend pro Epoch, beginnt bei 0; alte Epoch ergibt stale_epoch. Seek/Stop erhöhen Epoch atomar, seq wird zurückgesetzt; kein Überlauf (neue Session/Stream). JSON-Framezahlen maximal 2^53−1, PCM start_frame uint64.

Sitzung: created→loading→ready→playing↔paused; aus jedem aktiven Zustand stopping→closed oder error; error→stopping; stopping→error bei Fehler. Job: queued→running→ready, queued/running→error/cancelled; Endzustände terminal. Keine Selbstübergänge. Close ist später auf HTTP-Ebene idempotent, nicht als Zustandsübergang. schedule erlaubt play/pause/set_param/bypass mit output_frame und verschachteltem Befehl ohne eigene Sequenz. seek verwendet source_frame. Parameter sind endliche Zahlen, zusätzlich Capability-Grenzen prüfen.

## Data plane

Ein WebSocket-Binärmessage entspricht genau einem Block. Keine Base64-Daten, keine Fragmentierung auf Anwendungsebene. Alle Mehrbyte-Felder unsigned LE; Header exakt 32 Bytes, ohne Padding.

| Offset | Breite | Feld |
|---:|---:|---|
| 0 | 4 | protocol_version = 1 |
| 4 | 4 | stream_id (1…2^32−1) |
| 8 | 4 | epoch |
| 12 | 4 | seq |
| 16 | 8 | start_frame (Master-Ausgabeframe, JS BigInt) |
| 24 | 2 | nframes (256…2048) |
| 26 | 1 | channels = 2 |
| 27 | 1 | flags = 0 (reserviert) |
| 28 | 4 | sample_rate (8000…192000, tatsächliche Context-Rate) |
| 32 | nframes × 8 | Float32 LE, L/R interleaved |

Maximal 16416 Byte je Nachricht. Falsche Länge, Version, Flags, Kanalzahl, Framezahl oder Frame-Überlauf verwerfen; Codec erhält sämtliche Payload-Bits (auch NaN), Empfänger vor Audioausgabe nicht-endliche Werte durch Stille ersetzen. Transport prüft Stream, Epoch und Sequenz, verwirft alte Chunks. Begrenzte Queues, maximal 8 Blöcke je Stream initial; Backpressure statt wachsender Latenz. Kein Überlauf der Zähler. Bei Unterlauf Dry/Fallback, keine Blockade des Audio-Callbacks.
