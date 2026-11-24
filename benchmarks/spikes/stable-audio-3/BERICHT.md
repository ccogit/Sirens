# Stable Audio 3 – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/Stability-AI/stable-audio-3 (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: small-music / medium. Geprüfter README-Stand: [790793b89ddceea612be9ce42ff6830d18f6fa57](https://github.com/Stability-AI/stable-audio-3/blob/790793b89ddceea612be9ce42ff6830d18f6fa57/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: MIT (LICENSE/README).

Gewichte: https://huggingface.co/stabilityai/stable-audio-3-small-music ; Community-Lizenz und konkrete Nutzungsbedingungen prüfen; Dateigröße und Hash noch offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `lookahead`, keine Freigabe. README: Models, Usage, CUDA Version, Hardware Support. Audio-to-audio, Inpainting und Text; Dauer, Prompt, init_noise_level. Batch statt belegtem Stream. Small 433M, Medium 1.4B; 44.1 kHz stereo. Hersteller H200 Peak allocated: Small 5 s 1.69 GB, Medium 5 s 5.07 GB, keine RTX-5080-Angabe. Torch 2.7.1/torchaudio 2.7.1, cu128 Variante vorhanden; Medium Flash Attention 2; TensorRT Linux, TFLite CPU Windows. Keine ungeprüften bootstrap-Skripte (curl|bash/iex).

## Messplan und Risiken

Small CPU/CUDA, 4/8 s und mehrere Seeds; Medium erst danach. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.

[pyproject.toml](https://github.com/Stability-AI/stable-audio-3/blob/790793b89ddceea612be9ce42ff6830d18f6fa57/pyproject.toml): Version 0.1.0, Python >=3.10, Torch/torchaudio 2.7.1. [Inference Methods](https://github.com/Stability-AI/stable-audio-3/blob/790793b89ddceea612be9ce42ff6830d18f6fa57/docs/workflows/inference.md): Seed, Device, Init-Audio.

## AUFGABE-21 – Fortsetzung

- [Offizielle Dateiliste small-music](https://huggingface.co/stabilityai/stable-audio-3-small-music/tree/main): model.safetensors ca. 2,27 GB, model_config.json ca. 10,3 kB. Der zusätzliche [T5Gemma-Encoder](https://huggingface.co/stabilityai/stable-audio-3-small-music/tree/main/t5gemma-b-b-ul2) hat model.safetensors ca. 1,18 GB, tokenizer.json ca. 34,4 MB, tokenizer.model ca. 4,24 MB sowie Konfigurationsdateien. Die gerundeten Angaben sind keine verifizierten Bytezahlen. Blob-Abruf für model.safetensors: HTTP 401 Unauthorized.
- [Community-Lizenz](https://huggingface.co/stabilityai/stable-audio-3-small-music/blob/main/LICENSE.md), Stand 05.07.2024: Forschung und private Nutzung; kommerzielle Nutzung unter Bedingungen, insbesondere Registrierung und Umsatzgrenze. Zusätzlich [Gemma Terms of Use](https://ai.google.dev/gemma/terms). Beide Bedingungen vor Bezug akzeptieren; keine pauschale Freigabe für Weiterverteilung.
- Projektpin aus dem vorigen Bericht beibehalten. Upstream nennt Torch/Torchaudio 2.7.1; CUDA-12.8-Wheels vorhanden. Der vollständige kompatible Lock, authentifiziert aufgelöste Modellrevision, genaue Bytezahlen und Hashes für Modell und Textencoder sowie das Absichern des bestehenden lokalen Inferenzpfades sind offen. Deshalb Installer weiter gesperrt, keine automatische Beschaffung und keine Messung.
