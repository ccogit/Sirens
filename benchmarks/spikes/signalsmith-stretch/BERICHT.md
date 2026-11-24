# Signalsmith Stretch – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/Signalsmith-Audio/signalsmith-stretch (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: C++ Bibliothek (Version offen). Geprüfter README-Stand: [88061fd4eda56a2353c5d65c74aa3f4ccf76f9da](https://github.com/Signalsmith-Audio/signalsmith-stretch/blob/88061fd4eda56a2353c5d65c74aa3f4ccf76f9da/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: MIT (README: License).

Gewichte: Keine Modellgewichte. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Ending, Formant compensation, Compiling. C++ pitch/time, process/seek/flush, inputLatency/outputLatency in Samples, Transposition und Formant. MSVC/AppleClang getestet laut Anbieter; Signalsmith Linear für FFT; CPU, kein Python/CUDA/PyTorch/TensorRT-Bedarf. WASM-Build im Browser gesondert zu testen.

## Messplan und Risiken

C++ Release-Build CPU bzw. später WASM AudioWorklet; Impuls, Stereo, 0.8/1.2 Stretch, Pitch, Flush-Länge, p95 und 10 min Dropouts; Rückfall natives CPU-DSP. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.
