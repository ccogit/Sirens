# SAM Audio – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/facebookresearch/sam-audio (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: sam-audio-small / base / large. Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: SAM License (README License und LICENSE); Bedingungen und Weitergabe prüfen.

Gewichte: https://huggingface.co/facebook/sam-audio-small ; Zugang beantragen, Authentifizierung; keine Secrets im Repo. Größe und Gewichtslizenz vor Bezug prüfen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `offline`, keine Freigabe. README: Setup, Basic Text Prompting, Prompting Methods, Span Prediction. Python >=3.11, CUDA empfohlen; Text, Zeitanker, Video-Masken, Ausgabe target/residual. Span prediction und Reranking steigern Rechenbedarf. Keine belegte Streaming-API; Windows/WSL2, sm_120, Torch/TensorRT-Pins und VRAM offen.

## Messplan und Risiken

Small, Textprompt, predict_spans=False, reranking_candidates=1; kurze Ausschnitte, CPU-Versuch und GPU separat. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
