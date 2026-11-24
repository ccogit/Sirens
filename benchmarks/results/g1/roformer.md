# WP02: roformer-drumsep

Gate: nicht_gemessen; Modus: offline; Zeitpunkt: 2026-11-24T18:09:02.828289+00:00

| Messwert | Kalt | Warm |
|---|---:|---:|
| p50_ms | 23843.328499991912 | 1146.7643000069074 |
| p95_ms | 23843.328499991912 | 1153.230579997762 |
| p99_ms | 23843.328499991912 | 1153.7393959978363 |
| peak_vram_mib | nicht gemessen | nicht gemessen |
| rtf | 0.7947776166663971 | 0.038225476666896914 |
| underruns | nicht gemessen | nicht gemessen |

## Rechner

    {"os": {"system": "Windows", "release": "10"}, "python": "3.11.9", "node": "24.20.0", "ffmpeg": "9.0.2", "gpus": [{"driver": "621.24", "name": "NVIDIA GeForce RTX 5080", "vram_total_mib": 16303, "vram_free_mib": 12395}], "wsl": true, "disk": {"drive": "C:", "free_bytes": 1092474474496}, "git": {"sha": "316a225fddddc618adc7e84d14056806d559483f", "clean": true}, "audio_device": null, "notes": ["Audio-Gerät und Treiber separat am Zielrechner erfassen (nicht gemessen)"]}

## Nachstellen

    python -m benchmarks.spikes.roformer-drumsep.messen (lokale Modellpfade separat)

## Notizen

- Device: cuda
- VRAM per nvidia-smi abgetastet, kurze Peaks ggf. verfehlt.
- Keine hörbare End-to-End-Latenz, kein Gate; Audio außerhalb des Timings gespeichert.
- Seeds: kalt 0, warm fortlaufend ab 1.

## Gate-Entscheidung des Koordinators (24.11.2026)

**G1 RoFormer (MelBandRoformer, Vocals): grün für den Modus `offline`.** Echte Inferenz auf der RTX 5080
(Torch 2.7.1+cu128, `sm_120`), 30 s Testsignal: kalt 23,8 s (inklusive Laden), warm 1,15 s (RTF 0,038).
Der geplante Modus für das Stem Studio (Aufgabe 08) ist ein Vorbereitungsschritt, kein Streaming; dafür reicht
das deutlich. Peak-VRAM nicht erfasst (12,4 GB waren frei); misst der Worker in Aufgabe 08 selbst.
Installationsabweichung: `demucs==4.0.0` aus `requirements.lock` lässt sich unter Windows ohne C++-Build-Tools
nicht bauen (`diffq`); für RoFormer nicht nötig und weggelassen. DrumSep bleibt gesperrt.
