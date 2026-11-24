# RAVE – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/acids-ircam/RAVE (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: v2.4 beta. Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: LICENSE: separate Lizenzprüfung offen, keine Freigabe.

Gewichte: README: pretrained models / Export; nur selbst exportiertes oder geprüftes lokales TorchScript, Größe und Gewichtslizenz offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Export, High-level manipulation, Offline usage. Streaming-Export nutzt gecachte Convolutions; sonst Klickartefakte. Latentprojektion, Temperatur, receptive_field in Samples; GPU laut README experimentell. CPU zuerst; CUDA/PyTorch Version, sm_120, Windows/WSL2 und VRAM nicht belegt.

## Messplan und Risiken

Causal/raspberry-Variante, Blockgröße aus Export, 10 min stateful Verarbeitung und Impulsantwort. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
