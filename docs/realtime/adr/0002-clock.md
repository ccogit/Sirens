# AudioContext als Master-Uhr

Status: vorgeschlagen zur Freigabe mit WP01.

## Entscheidung
Ein Master-Frame-Counter, getrennt von Quellposition; Epoch bei Seek/Stop; deklarierte Pfadlatenz.

## Alternativen und Folgen
Wallclock und Worker-Uhr driften; keine zweite Master-Uhr.

Keine Hardwaremessung in WP01; nachfolgende WPs implementieren und messen die Vorgaben.
