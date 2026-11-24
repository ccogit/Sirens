# G1 DEMON (ACE-Step v1.5 Turbo 2B) – Messung am Zielrechner (24.11.2026)

**Gate: gelb für den Modus `streaming`.** Die Engine streamt stabil (Fensterdecode weit unter Echtzeit,
VRAM reicht). Eine Änderung pro Anfrage (Seed, Denoise, Prompt) braucht im Eager-Betrieb aber 333 ms (Tiefe 1)
bzw. 650–1300 ms (Tiefe 4) bis zum neuen Latent, also mehr als 250 ms. TensorRT/compile nicht gemessen;
1-Tick-Pfad über Shared Curves nicht gemessen.

- Zielrechner: Windows 11, RTX 5080 16 GB, Treiber 621.24; Torch **2.9.1+cu128** (Upstream-Pin, `sm_120` läuft),
  bf16, 8 Schritte, `decoder_backend=eager`, `vae_backend=eager`, SDPA statt flash-attn, Textencoder auf CPU ausgelagert.
- Code: `daydreamlive/DEMON` @ `96acc905204d54bfd3055084ca8e9df8a6d9a33f` (AGPL-3.0-or-later, MIT-Anteile).
- Gewichte: `ACE-Step/Ace-Step1.5` @ `19671f406d603126926c1b7e2adc169acbcade22` (MIT), nur safetensors;
  `silence_latent.pt` mit `weights_only=True`; DiT über die vendierte Klasse (kein `trust_remote_code`).
- Quelle: synthetischer Klick 120 BPM, Task `cover`, Tags „instrumental electronic drums“, Denoise 1,0
  (bei 0,35/0,75 bleibt die Ausgabe nahe an der fast stillen Quelle, etwa −59 dBFS).

| Fall | Tick p50 / p95 / p99 | Fertiges Latent alle | Seed-Wechsel bis neues Latent | VRAM allokiert (max) | GPU gesamt (nvidia-smi) |
|---|---:|---:|---:|---:|---:|
| Tiefe 1, Song 10 s | 39 / 45 / 47 ms | 8 Ticks (≈ 0,31 s) | 7 Ticks, 333 ms | 6,1 GiB | 8,0 GiB |
| Tiefe 4, Song 10 s | 51 / 70 / 77 ms | 1 bzw. 5 Ticks | 11 Ticks, 650 ms | 6,1 GiB | 8,1 GiB |
| Tiefe 4, Song 30 s | 107 / 112 / 115 ms | 1 bzw. 5 Ticks | 11 Ticks, 1295 ms | 6,8 GiB | 9,2 GiB |

Wiedergabepfad (Fensterdecode, 0,36 s je Fenster, durchgehend über den ganzen Song): p50 7,8–8,4 ms,
p95 8,9–10,5 ms, also RTF p95 0,025–0,029 je Fenster. Das erste Fenster nach dem Start dauert 180–220 ms.
Volldecode 10 s: 51–116 ms, 30 s: 183 ms. Die Grundlast anderer Prozesse lag bei ca. 1,3–1,5 GiB.
Frei blieben damit mindestens 6,7 GiB.

Kaltstart (zweiter und weitere Prozesse): Laden 7,4–7,9 s, `prepare_source` 1,6 s (erster Lauf nach der
Installation 11,4 s), `encode_text` 0,9–7,8 s, erster Tick 0,3–2,3 s. Gesamt bis zum ersten fertigen Ton 10–30 s:
Session vorab laden.

Ausgabe (Denoise 1,0): 48 kHz Stereo, RMS −18,6 dBFS (10 s) bzw. −14,7 dBFS (30 s), Peak 0 dBFS (clippt,
Hörprobe auf ±1 begrenzt), spektrale Flachheit Median 0,001–0,002 (tonal). Zum Vergleich `session.generate`
(nicht streamend): −17 bis −19 dBFS. Noch nicht durch Hören beurteilt.

Standard-Runner `benchmarks.spikes.demon.messen` (Tiefe 1, 4 s, Denoise 0,35/0,75) lief ebenfalls:
Er misst Ticks bis zum Latent plus Decode eines 0,36-s-Fensters, warm p50 381 ms (RTF 1,06 bezogen auf 0,36 s).
Das ist kein Streaming-RTF, weil jedes Sample ein ganzes Latent neu erzeugt. Ausgabe dort −59 dBFS (siehe oben).

CPU nicht gemessen (2B-DiT, nicht sinnvoll). Ergebnisse lokal: `benchmarks/results/local/demon-8c8020d2e2`,
`demon-engine-d{1,4}-10s-den1`, `demon-engine-d4-30s-den1`, `demon-engine-d{1,4}-10s` (Denoise 0,75),
`demon-diag`.

## Gewichte (SHA-256)

Die vier großen Dateien entsprechen den auf Hugging Face veröffentlichten Hashes.

| Datei | Bytes | SHA-256 |
|---|---:|---|
| acestep-v15-turbo/model.safetensors | 4787825604 | 3f6e0797fad420a39bd33979eb6e840e30989e34a3794e843d23b60ec6e422d7 |
| acestep-v15-turbo/silence_latent.pt | 3841215 | a778e9dd942f5e8b2c09c55370782d318834432b03dabbcdf70e6ed49ad6358b |
| acestep-v15-turbo/config.json | 1968 | 74745ff704ea49164c3d2d1c99fc0670f3fc635a869f0aec2d1311e6a52d400a |
| vae/diffusion_pytorch_model.safetensors | 337431388 | da17edb604c40deaf09e9b24974e590d1ca83a374070e5d0884cfa4bed9a99b0 |
| vae/config.json | 425 | 14e019904df567f26df750317a70e2bd08f9f8f3c40ff4a24c97d1cd3f20ccd2 |
| Qwen3-Embedding-0.6B/model.safetensors | 1191586416 | 0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd |
| Qwen3-Embedding-0.6B/added_tokens.json | 707 | c0284b582e14987fbd3d5a2cb2bd139084371ed9acbae488829a1c900833c680 |
| Qwen3-Embedding-0.6B/chat_template.jinja | 4116 | 87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5 |
| Qwen3-Embedding-0.6B/config.json | 1359 | bb23c1607cfe059a58d8f0196cf1cebb52082b1056b8e358a579da80a5759420 |
| Qwen3-Embedding-0.6B/merges.txt | 1671853 | 8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5 |
| Qwen3-Embedding-0.6B/special_tokens_map.json | 613 | 76862e765266b85aa9459767e33cbaf13970f327a0e88d1c65846c2ddd3a1ecd |
| Qwen3-Embedding-0.6B/tokenizer.json | 11423705 | def76fb086971c7867b829c23a26261e38d9d74e02139253b38aeb9df8b4b50a |
| Qwen3-Embedding-0.6B/tokenizer_config.json | 5404 | 443bfa629eb16387a12edbf92a76f6a6f10b2af3b53d87ba1550adfcf45f7fa0 |
| Qwen3-Embedding-0.6B/vocab.json | 2776833 | ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910 |

## Installation (Zielrechner)

Das Upstream-`uv.lock` fehlt am Pin, daher bricht `install.py` ab. Die Schritte wurden manuell ausgeführt,
nur mit Wheels:

```powershell
py -3.11 -m venv .venv-spike-demon
$v = ".venv-spike-demon\demon-src"
git init $v; git -C $v fetch --depth=1 https://github.com/daydreamlive/DEMON.git 96acc905204d54bfd3055084ca8e9df8a6d9a33f; git -C $v checkout --detach FETCH_HEAD
$py = ".\.venv-spike-demon\Scripts\python.exe"
& $py -m pip install --only-binary=:all: --index-url https://download.pytorch.org/whl/cu128 torch==2.9.1+cu128 torchaudio==2.9.1+cu128 torchvision==0.24.1+cu128
& $py -m pip install --only-binary=:all: "transformers>=4.51.0,<4.58.0" diffusers einops loguru accelerate soundfile scipy torchao==0.17.0 safetensors numpy "vector-quantize-pytorch>=1.27.15" "pytorch-wavelets>=1.3" "PyWavelets>=1.5" "setuptools<81"
# aufgelöst: transformers 4.57.6, diffusers 0.39.0, accelerate 1.16.0, vector-quantize-pytorch 1.34.1, numpy 2.4.6 (vollständig in .venv-spike-demon\installed.lock)
# Gewichte: je Datei aus weights.json per curl von der gepinnten resolve-URL nach .venv-spike-demon\weights\checkpoints\<filename>,
# danach install.obtain()/verify_snapshot() (prüft Hashes, schreibt verified.json). urllib-Download blieb hängen, curl lief mit ca. 13 MB/s.
$env:SIRENS_DEMON_DEPTH = "1"
& $py -m benchmarks.spikes.demon.messen --model .\.venv-spike-demon\weights\checkpoints --device cuda --rate 48000 --duration 4 --repeats 5
```

Ausgelassen, weil für den Eager-Session-Pfad nicht nötig: tensorrt, onnx, onnxscript, polygraphy, cuda-python
(TRT-Engines), triton-windows, flash-attn (Fremd-Wheel von GitHub), gradio, fastapi, uvicorn, mcp, websockets,
torchcodec, numba, librosa, sounddevice, modelscope, peft, lightning, tensorboard, hf_xet. Warnungen ohne
Einfluss: torchao-C++-Erweiterungen (verlangen torch ≥ 2.11), „Unable to import torchao Tensor objects“.
