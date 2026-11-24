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

## AUFGABE-22 – Teilstand (Übergabe)

Quellen: [DEMON pyproject](https://github.com/daydreamlive/DEMON/blob/96acc905204d54bfd3055084ca8e9df8a6d9a33f/pyproject.toml), [Session](https://github.com/daydreamlive/DEMON/blob/96acc905204d54bfd3055084ca8e9df8a6d9a33f/acestep/engine/session.py), [ModelContext](https://github.com/daydreamlive/DEMON/blob/96acc905204d54bfd3055084ca8e9df8a6d9a33f/acestep/engine/model_context.py), [HF-Snapshot](https://huggingface.co/ACE-Step/Ace-Step1.5/tree/19671f406d603126926c1b7e2adc169acbcade22). HF nennt MIT und zeigt öffentlichen Zugriff ohne Login/Lizenzschranke. Die drei safetensors und silence_latent.pt haben veröffentlichte SHA-256; exakte Bytezahl bzw. nicht veröffentlichte Hashes werden beim expliziten Bezug lokal dokumentiert und bei späteren Läufen überprüft. Keine Python-Dateien aus dem Modellrepo; DEMON lädt die vendierte DiT-Klasse und silence_latent.pt mit weights_only=True. TORCH_FORCE_WEIGHTS_ONLY_LOAD=1 zusätzlich gesetzt. Kein LM benötigt für diese Session, kein XL, keine LoRAs. Der kleinere 2B-Turbo und ausgelagerter Textencoder sind der erste 16-GB-Versuch; kein SA3-Ersatz implementiert.

Upstream verlangt Torch 2.9.1+cu128, torchvision 0.24.1+cu128, torchaudio 2.9.1+cu128 und torchao 0.17.0. Der auf dem Zielrechner belegte 2.7.1-Build ist daher nicht automatisch kompatibel. Upstream uv.lock war via GitHub-Dateiabruf 404 und Webabruf nicht verfügbar; transitive Pins nicht verifiziert. Installer akzeptiert nur vorhandenes Upstream-Lock mit uv sync --locked --no-build, andernfalls bricht er ab. TensorRT-Wheels bzw. triton-windows können auf Windows trotz Eager-Auswahl blockieren; dann minimalen Inferenz-Lock separat erstellen, keine C/C++-Builds. Kein eigener echter Modelllauf.

### Kopierbare Befehle (Windows, Repo-Root)

Git, uv und Python 3.11 müssen vorliegen. Bezug nur nach bewusster Prüfung. Achtung: Teilstand, bei fehlendem Lock wird nach dem Snapshot-Bezug abgebrochen; nicht als lauffähig abgenommen.

```powershell
.\benchmarks\spikes\demon\install.ps1
.\benchmarks\spikes\demon\install.ps1 -ModelleLaden
$py = ".\.venv-spike-demon\Scripts\python.exe"
$model = ".\.venv-spike-demon\weights\checkpoints"
& $py -m benchmarks.spikes.demon.messen --dry-run
$env:SIRENS_DEMON_DEPTH = "1"
& $py -m benchmarks.spikes.demon.messen --model $model --device cuda --rate 48000 --duration 4 --seconds 600
$env:SIRENS_DEMON_DEPTH = "4"
& $py -m benchmarks.spikes.demon.messen --model $model --device cuda --rate 48000 --duration 4 --seconds 600
```

Runner schreibt result.json/result.md und lokale Hörproben. Ein Sample umfasst die Ticks bis zur fertigen Ausgabe plus 0,36-s-Decodefenster; RTF bezogen auf tatsächliche Fensterdauer, kein RTF je leerem Tick. Denoise-Wechsel ab Sample 2; keine separate Propagationsmessung, kein kontinuierlicher Playback-Cursor, kein Browser-/Control-to-audio-Nachweis. Wiederholtes Fenster ist ein Engine-Mikrobenchmark, keine hörbare Echtzeitfreigabe. CPU optional mit --device cpu, nicht bestätigt. Rückbau: install.ps1 -Entfernen, lokale Resultate bei Bedarf löschen.
