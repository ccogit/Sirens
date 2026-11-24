# G1 Stable Audio 3 small-music – Messung am Zielrechner (24.11.2026)

**Gate: grün für den Modus `lookahead`** (Performance Pads, Aufgabe 12).

- Zielrechner: Windows 11, RTX 5080 16 GB, Treiber 621.24; Torch 2.7.1+cu128 (`sm_120`), fp16, 8 Schritte.
- Code: `Stability-AI/stable-audio-3` @ `790793b89ddceea612be9ce42ff6830d18f6fa57` (MIT), nur Wheels
  (`--only-binary=:all:`), flash-attn ausgelassen (nur für Medium nötig).
- Gewichte: `stabilityai/stable-audio-3-small-music` @ `8bdfb53c6b0fbc62113cd571fd37373efe15fa14` (Community-Lizenz:
  Forschung und privat frei, kommerziell eingeschränkt), Laden nur über safetensors.

| Fall | Zeit | RTF | Speicher (Prozess) | GPU gesamt |
|---|---:|---:|---:|---:|
| Kalt, erster Lauf nach Installation (Laden 7,0 s + erste Erzeugung 14,2 s), 8 s | 21,2 s | 2,65 | 2,2 GiB | 4,1 GiB |
| Kalt, zweiter Prozess, 30 s | 9,4 s | 0,31 | 2,2 GiB | 4,0 GiB |
| Warm 8 s (4 Takte bei 120 BPM), 3 Seeds | 0,35–0,40 s | 0,043–0,050 | 1,7 GiB | 4,1 GiB |
| Warm 16 s (8 Takte), 3 Seeds | 0,39–0,43 s | 0,024–0,027 | 1,7 GiB | 4,0 GiB |
| Warm 30 s, 3 Seeds | 0,37–0,39 s | 0,012–0,013 | 1,7 GiB | 4,0 GiB |

Ausgabe: 44,1 kHz Stereo, −20 bis −26 dBFS RMS, tonal (spektrale Flachheit 0,01–0,30), mit gleichem Seed
reproduzierbar. Noch nicht durch Hören beurteilt; Prompt-Treue (Rise, Fill, Drop) ist offen.

Folgen für Aufgabe 12: Modell vorab laden und einmal aufwärmen (Kaltstart 9–21 s); Vorlauf je Pad weit unter
einem Takt. Medium nicht gemessen.

## Gewichte (SHA-256)

| Datei | Bytes | SHA-256 |
|---|---:|---|
| model.safetensors | 2270384940 | da85866b11b01d0694d990785f6abbd79c8064df1b0e6f8aea52935e0ef84b64 |
| model_config.json | 10341 | 100776f25af5aa83f70e0c6b384de6690cb4e5ad01c24f7cfbb6524d18765f06 |
| t5gemma-b-b-ul2/model.safetensors | 1183022944 | 9b05ea5a4f211d023832f706fb2c0e83e4fc721b6da35ab69ceb0b55eb7800d3 |
| t5gemma-b-b-ul2/tokenizer.json | 34362429 | 7794135caa3ea73918949c902a781cc61dab674a4b59c17d85931c77c1114cbd |
| t5gemma-b-b-ul2/tokenizer.model | 4241003 | 61a7b147390c64585d6c3543dd6fc636906c9af3865a5548f27f31aee1d4c8e2 |

## Installation (Zielrechner)

```powershell
py -3.11 -m venv .venv-spike-stable-audio-3
# Code am Pin in .venv-spike-stable-audio-3\sa3 (git fetch --depth=1 … 790793b8…)
pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.7.1+cu128 torchaudio==2.7.1+cu128
pip install --only-binary=:all: einops==0.8.2 einops-exts==0.0.4 numpy==2.2.6 packaging==26.0 safetensors==0.7.0 tqdm==4.67.3 huggingface-hub==1.7.1 transformers==5.8.0 soundfile==0.13.1 tokenizers==0.22.2 hatchling
pip install --no-deps --no-build-isolation .\.venv-spike-stable-audio-3\sa3
```
Gewichte per `snapshot_download` (Hugging-Face-Login mit bestätigter Lizenz); für den Offline-Betrieb
`refs/main` im Cache auf die Revision setzen.
