# GPU Audio SDK – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/gpuaudio/gpuaudio-sdk (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: SDK (Version offen). Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: LICENSE: konkrete Rechte/SDK-Laufzeit separat prüfen.

Gewichte: Keine Modellgewichte für Gain-Beispiel; SDK-Binaries und Lizenz vor Installation prüfen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Installation, Gain Processor, APIs. Native Engine-/Processor-API mit Graphen, sync/async; Hersteller beschreibt 100–200 µs Scheduler-Fenster (keine End-to-end-Messung). Plattformguide und Compiler/SDK prüfen, sm_120 nicht belegt, kein PyTorch nötig für Gain. Windows nativ bevorzugt; WSL2-Audiopfad ungeprüft.

## Messplan und Risiken

C++ nativer Sidecar statt Browser-GPU-Zugriff; Gain-Beispiel mit Impuls, 128/256/512 Frames, CPU-Baseline, Transfers, 10 min Dropouts. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
