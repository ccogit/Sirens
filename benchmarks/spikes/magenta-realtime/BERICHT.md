# Magenta RealTime 2 – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/magenta/magenta-realtime (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: mrt2_small / mrt2_base. Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: Apache-2.0 (LICENSE/README).

Gewichte: README: Models & checkpoints, https://github.com/magenta/magenta-realtime/blob/main/docs/models.md ; Ressourcen und Gewichte separat, Größe/Lizenz nicht abschließend geprüft. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `offline`, keine Freigabe. README: Hardware requirements, Quickstart, Python Development. Apple Silicon für Echtzeit laut Anbieter; NVIDIA nur Offline über Python JAX/MLX-Bibliothek, Python 3.12; C++ Kern. 230M/2.4B Parameter; Prompt, Dauer, Notensteuerung. WSL2/JAX CUDA als Versuch, Windows nativ nicht belegt; keine sm_120- oder VRAM-Zahl belegt. mrt models init/download laden Ressourcen.

## Messplan und Risiken

Small, kurze Begleitspur Lookahead; JAX Offline-Benchmark und tatsächliche Chunk-API vor Freigabe. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
