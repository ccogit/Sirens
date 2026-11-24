# Worker-IPC

Status: vorgeschlagen zur Freigabe mit WP01.

## Entscheidung
Längenpräfix uint32 LE, dann UTF-8-JSON (max. 1 MB), Version 1, request_id, type, payload; Heartbeat alle 1 s, nach 3 s ohne Heartbeat unhealthy, kontrollierter Abbruch. Audio getrennt binär; keine Pickle-Daten.

## Alternativen und Folgen
Pickle erlaubt Codeausführung; HTTP ohne dedizierte Aufsicht löst Lebenszyklus nicht.

Keine Hardwaremessung in WP01; nachfolgende WPs implementieren und messen die Vorgaben.
