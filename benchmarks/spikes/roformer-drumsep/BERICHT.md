# RoFormer / DrumSep – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/ZFTurbo/Music-Source-Separation-Training (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: MSST + pymss (2.2+ Python 3.11). Geprüfter README-Stand: [1523206d12a521bdb20673726562524cf0f9635b](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/1523206d12a521bdb20673726562524cf0f9635b/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: MIT für beide Code-Repos (LICENSE).

Gewichte: README: Pre-trained models; https://github.com/pymss-project/pymss (README CLI inference). Modell-/Konfig-Paar und Lizenz einzeln prüfen; Größen und Hashes offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `offline`, keine Freigabe. MSST README Code description: inference.py trennt Dateien; pymss README: CLI inference lädt fehlende Modelle automatisch, daher kein Katalogaufruf ohne kontrollierte Offline-Konfiguration. CUDA cu128 in pymss README, kein Nachweis 5080. Windows/WSL2 separat prüfen. Chunk-/Overlap aus Modellkonfiguration, kein Streaming belegt; Stem-Auswahl, Device, Ensemble. A6000-48GB-Trainingsangabe nicht Inferenz-VRAM.

## Messplan und Risiken

Einzelmodell vor Ensemble; RoFormer Vocals und DrumSep separat, kleine Chunks gegen Artefakte, Demucs-Bestand als Rückfall. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.

Zweiter README-Pin: [pymss e545e10](https://github.com/pymss-project/pymss/blob/e545e10a4a85306e9c78a9d64f91e0d43d170ad2/README.md). MSST `inference.py` lädt mit `torch.load(..., weights_only=False)`; untrusted Pickle ist nicht zulässig. Sicheren Loader oder überprüften Export vorsehen.
