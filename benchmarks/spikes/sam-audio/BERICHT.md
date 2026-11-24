# SAM Audio – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/facebookresearch/sam-audio (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: sam-audio-small / base / large. Geprüfter README-Stand: [bb4c6999d2677c7402360e426afc01ddfad6dce0](https://github.com/facebookresearch/sam-audio/blob/bb4c6999d2677c7402360e426afc01ddfad6dce0/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: SAM License (README License und LICENSE); Bedingungen und Weitergabe prüfen.

Gewichte: https://huggingface.co/facebook/sam-audio-small ; Zugang beantragen, Authentifizierung; keine Secrets im Repo. Größe und Gewichtslizenz vor Bezug prüfen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `offline`, keine Freigabe. README: Setup, Basic Text Prompting, Prompting Methods, Span Prediction. Python >=3.11, CUDA empfohlen; Text, Zeitanker, Video-Masken, Ausgabe target/residual. Span prediction und Reranking steigern Rechenbedarf. Keine belegte Streaming-API; Windows/WSL2, sm_120, Torch/TensorRT-Pins und VRAM offen.

## Messplan und Risiken

Small, Textprompt, predict_spans=False, reranking_candidates=1; kurze Ausschnitte, CPU-Versuch und GPU separat. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.

## AUFGABE-21 – Fortsetzung

- [pyproject.toml am Projektpin](https://github.com/facebookresearch/sam-audio/blob/bb4c6999d2677c7402360e426afc01ddfad6dce0/pyproject.toml): sam_audio 0.1.0; Python >=3.11; transformers >=4.54.0; torch, torchvision, torchaudio, torchcodec, torchdiffeq. Git-Abhängigkeiten (ausgewählte tatsächlich aufgelöste Revisionen, **noch kein getesteter Lock**): [dacvae](https://github.com/facebookresearch/dacvae/commit/414c20785fc3a28373073ea8ef7a1316eeeaca6e), [ImageBind](https://github.com/facebookresearch/ImageBind/commit/53680b02d7e37b19b124fa37bae4b6c98c38f5be), [CLAP](https://github.com/lematt1991/CLAP/commit/b85cb7ecac0af7d064cbf03ebd990e709e959fe7), [perception_models](https://github.com/facebookresearch/perception_models/commit/e72b6810b1133e1c879f2cc965d276eb73803f1f). Windows-Kompatibilität insbesondere torchcodec/FFmpeg offen.
- [Gewichtsdateien](https://huggingface.co/facebook/sam-audio-small/tree/main): checkpoint.pt ca. 5,1 GB, config.json ca. 2,25 kB; direkte Blob-Abfrage ohne Freigabe HTTP 401. Exakte Bytes, SHA und Revision nicht bestätigt. [SAM License](https://huggingface.co/facebook/sam-audio-small/blob/main/LICENSE) vom 19.11.2025, Bedingungen vor Bezug akzeptieren.
- [BaseModel](https://github.com/facebookresearch/sam-audio/blob/bb4c6999d2677c7402360e426afc01ddfad6dce0/sam_audio/model/base.py) lädt checkpoint.pt mit weights_only=True. Allerdings können die Konstruktoren des Textencoders und optionaler Ranker/Span-Prädiktoren weitere Modelle beziehen. Für den Textpfad müssen diese optionalen Komponenten in der Konfiguration explizit deaktiviert und der T5-Encoder samt Tokenizer lokal bereitgestellt werden. T5-Safetensors-Quelle siehe weights.json; die vollständige Abhängigkeits- und Gewichtsclosure fehlt.
- Der Installer bleibt bewusst gesperrt. Kein Modellbezug, keine tatsächliche Inferenz oder Hardwaremessung in diesem Durchlauf. Nächster Schritt: authentifiziertes Metadaten-Lesen, vollständige Hashliste und kompatibler CUDA-/torchcodec-Lock, danach abgesicherte lokale Inferenz.
