# Beat This! Live – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/CPJKU/beat_this_live (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: Live / Large / Zero (ISMIR 2026). Unveränderlicher Commit-Pin noch offen; vor Installation festlegen.

## Lizenz und Gewichte

Code: MIT für Code und veröffentlichte Gewichte (README: License), Trainingsdaten teils eingeschränkt.

Gewichte: README Evaluation: verlinkte Checkpoints auf cloud.cp.jku.at; Größe/Hash offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Training, Evaluation. Kausale Convolutions/Transformer; Zero mit sclm_lookahead_size=1 und label shift; Beat-/Downbeat-Events statt PCM. Python-Worker, requirements.lock.txt prüfen, CUDA/Blackwell/Windows/WSL2 nicht bestätigt; kein VRAM-Beleg.

## Messplan und Risiken

CPU gegen CUDA, click120/140/150 mit bekannten Frames, Verzögerung und Fehlerquote messen; Zero gegen Live, 10 min; Rückfall BeatGrid. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
