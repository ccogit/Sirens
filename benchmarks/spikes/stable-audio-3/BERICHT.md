# Stable Audio 3 – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/Stability-AI/stable-audio-3 (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: small-music / medium. Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: MIT (LICENSE/README).

Gewichte: https://huggingface.co/stabilityai/stable-audio-3-small-music ; Community-Lizenz und konkrete Nutzungsbedingungen prüfen; Dateigröße und Hash noch offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `lookahead`, keine Freigabe. README: Models, Usage, CUDA Version, Hardware Support. Audio-to-audio, Inpainting und Text; Dauer, Prompt, init_noise_level. Batch statt belegtem Stream. Small 433M, Medium 1.4B; 44.1 kHz stereo. Hersteller H200 Peak allocated: Small 5 s 1.69 GB, Medium 5 s 5.07 GB, keine RTX-5080-Angabe. Torch 2.7.1/torchaudio 2.7.1, cu128 Variante vorhanden; Medium Flash Attention 2; TensorRT Linux, TFLite CPU Windows. Keine ungeprüften bootstrap-Skripte (curl|bash/iex).

## Messplan und Risiken

Small CPU/CUDA, 4/8 s und mehrere Seeds; Medium erst danach. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
