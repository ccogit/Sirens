# WebSocket-Sidecar

Status: vorgeschlagen zur Freigabe mit WP01.

## Entscheidung
Binäres PCM über lokalen überwachten WebSocket-Sidecar; HTTP bleibt Steuerkanal.

## Alternativen und Folgen
HTTP-Polling/Base64 erzeugt Zusatzkosten; WebTransport oder nativer Host nur nach G2 und neuer ADR.

Keine Hardwaremessung in WP01; nachfolgende WPs implementieren und messen die Vorgaben.
