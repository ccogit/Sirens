# Echtzeit-Architektur v1

WP01 friert Schnittstellen ein, nicht die Leistungsfähigkeit. Der Bestand bleibt unverändert; standardmäßig ist RT deaktiviert.

## Prozesse und Module

- `sirens/realtime/`: Standardbibliothek, HTTP-Routing, Verträge, später Sessions, Jobs, Assets, GPU-Leases und Supervisor. Keine Modellimporte.
- `workers/`: separat installierte Prozesse mit eigenen Lockfiles und Modellrevisionen; keine automatischen Downloads.
- `web/js/realtime/`: ES-Module, später Scheduler, UI, Transport, AudioWorklet und Effekte.
- Lokaler Sidecar (WP04): binäre PCM-WebSockets, überwacht vom Supervisor; keine Inferenz im HTTP-Thread.
- `native/`: optionaler Host nur nach Mess-Gate.
- `tests/realtime/`, `benchmarks/`, `docs/realtime/`: CPU-/Mock-Tests, Messskripte, Verträge und ADRs.

## Datenfluss

Browser → gleiche Origin /api/rt/v1/ → Orchestrator → kontrollierte Worker-IPC. Jobs sind asynchron; Assets werden über serverseitige IDs aufgelöst. Worker → Sidecar → Browser-Transport → begrenzter Ringbuffer → AudioWorklet → Dry/Wet und Ausgabe. Keine Netzwerkoperation, Allokation oder KI im Audio-Callback. Anfangs MessagePort/Transferables; SharedArrayBuffer erst nach Nachweis und COOP/COEP-Tests. Keine Annahme fester Renderquantengröße.

AudioContext ist einzige Master-Uhr; Quellposition und Ausgabeframe sind getrennt. Pfadlatenz wird deklariert und Dry/Wet kompensiert. Seek/Stop erhöhen die Epoch; alte Blöcke werden verworfen. Resampling außerhalb des Callbacks; tatsächliche Context-Rate beachten (Standard 48 kHz). Scheduler nutzt BeatGrid, bei geringer Konfidenz manuelle Korrektur; kein erzwungener Phrasenwechsel.

GPU-Leases später nach gemessenem Peak plus konfigurierbarer Reserve (initial 2–3 GiB); ohne Telemetrie konservativ sperren. Priorität Audio, nächster Abschnitt, Interaktion, Hintergrund, Visuals. Nur eigene Prozessbäume terminieren. UI-Lifecycle mount/pause/destroy, Dry/Wet, Bypass, Panic, Queue/VRAM und ehrliche Gate-/Verfügbarkeitsanzeige. Audio erst nach Nutzerinteraktion.

WP01 implementiert keine produktive Audio- oder GPU-Funktion. Fallback ist der unveränderte Bestand; Mock ist ausdrücklich kein gemessenes Modell.
