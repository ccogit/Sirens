# DEMON – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/daydreamlive/DEMON (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: ACE-Step v1.5 Turbo, Stable Audio 3 small. Geprüfter README-Stand: [96acc905204d54bfd3055084ca8e9df8a6d9a33f](https://github.com/daydreamlive/DEMON/blob/96acc905204d54bfd3055084ca8e9df8a6d9a33f/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: AGPL-3.0-or-later (README: Authors and license); MIT-Anteile separat. Bei Weitergabe und ggf. Netzinteraktion Quellpflichten prüfen.

Gewichte: ACE-Step v1.5 (~18 GB laut Quickstart), LoRAs separat prüfen; keine Gewichtsfreigabe abgeleitet. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Quickstart, The streaming engine, Benchmarks. Ring mit mehreren Denoising-Stufen; Seed, Denoise, Guidance und Kurven steuerbar. Hersteller RTX 5090: ~12 GB Working Set für ACE-Step 2B, 60 s Latent, 14–81 ms Kurvenreaktion am Engine-Ausgang je Tiefe; nicht Browserlatenz. 3090/4090/5090 getestet, 5080 nicht belegt; TensorRT und CUDA-Build prüfen, WSL2 bevorzugt, Windows nicht bestätigt. uv, Node 20+ für Demo, ca. 40 GB Platte laut Anbieter. demon-setup führt Downloads und Engine-Build aus; nicht ungeprüft ausführen.

## Messplan und Risiken

SA3 small statt ACE-Step; Ringtiefe 1/4, 10 min echte Ausgabe und Kontrollsprung messen. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.

[Session-API und TRT 10.16.x](https://github.com/daydreamlive/DEMON/blob/96acc905204d54bfd3055084ca8e9df8a6d9a33f/docs/ACESTEP.md): `prepare_source`, `encode_text`, `stream`, `tick`, `decode`; Web-Demo lädt beim ersten Gebrauch Fixtures und installiert Frontend, daher nicht als abgeschotteten Messweg verwenden.
