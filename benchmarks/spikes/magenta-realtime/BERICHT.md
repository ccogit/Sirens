# Magenta RealTime 2 – WP02 / AUFGABE-24

Gate: `nicht_gemessen`. Zunächst nur Offline-Messversuch auf NVIDIA, keine Streaming-Freigabe.

## Quellen und Version (24.11.2026)

- Projektcode Apache-2.0: https://github.com/magenta/magenta-realtime/tree/694a545e4ba0b88bf1150137b129582166d3e07f ; PyPI-Wheel magenta-rt 2.0.3 mit Provenienz auf diesen Commit: https://pypi.org/project/magenta-rt/ .
- Paketpins aus dessen uv.lock, JAX 0.10.1 und CUDA12-Plugin/PJRT 0.10.1 (https://pypi.org/project/jax-cuda12-plugin/0.10.1/). CUDA12-Runtime-Transitive noch nicht vollständig fixiert; PyTorch ist nicht erforderlich. Nur Wheels, kein lokaler Quellbau.
- JAX-API und sicherer Checkpoint-Loader: https://github.com/magenta/magenta-realtime/blob/694a545e4ba0b88bf1150137b129582166d3e07f/magenta_rt/jax/system.py (safetensors.flax.load_file, keine Pickle-Dateien). MusicCoCa verwendet LiteRT und SentencePiece mit lokal geprüften Ressourcen: https://github.com/magenta/magenta-realtime/blob/694a545e4ba0b88bf1150137b129582166d3e07f/magenta_rt/musiccoca.py .
- Gewichte: https://huggingface.co/google/magenta-realtime-2/blob/7803d987f43f7142cfc7d68ba3361c5f83023931/README.md (CC-BY-4.0, zusätzliche Nutzungsbedingungen: Rechte Dritter respektieren; Nutzer verantwortlich für Ausgabe). Öffentlicher Bezug, kein Login/Lizenzdialog auf der Modellseite ersichtlich. Lokale Zustimmung ist dennoch Pflicht.
- Alle sechs Dateien in weights.json aus offiziellen LFS-Pointern (genaue Bytezahl und SHA-256). Nur mrt2_small (230M); die eingebetteten SpectroStream-Parameter kommen aus dem JAX-Checkpoint. Kein MLX-Export, kein zusätzlicher SpectroStream-Download, kein Text-Mapper für Audiokonditionierung. Insgesamt rund 2 GB Gewichte, zusätzlicher Plattenbedarf für CUDA-Wheels und venv.

## Installation und Aufruf (Windows 11 / WSL2)

Native Windows-JAX-CUDA-Ausführung ist nicht vorgesehen. JAX-Installationsmatrix: https://docs.jax.dev/en/latest/installation.html . Ubuntu 24.04 (Python 3.12), WSL2, aktueller NVIDIA-Windows-Treiber für RTX 5080; kein Linux-Grafiktreiber in WSL installieren. Falls WSL fehlt, in administrativer PowerShell:

```powershell
wsl --install -d Ubuntu-24.04
```

Nach Abschluss der WSL-Einrichtung Ubuntu öffnen und dort:

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv
nvidia-smi
```

Im Sirens-Repo-Root in PowerShell (Ubuntu 24.04 muss Standarddistribution sein, ggf. `wsl --set-default Ubuntu-24.04`):

```powershell
python -m benchmarks.spikes.magenta-realtime.messen --dry-run
.\benchmarks\spikes\magenta-realtime\install.ps1
.\benchmarks\spikes\magenta-realtime\install.ps1 -ModelleLaden
wsl --cd (Get-Location).Path
```

Nach Bestätigung im WSL-Terminal, weiterhin im Repo-Root:

```bash
PY="$HOME/.venv-spike-magenta-realtime/bin/python"
MODEL="$HOME/.venv-spike-magenta-realtime/magenta-rt-v2"
"$PY" -m benchmarks.spikes.magenta-realtime.messen --model "$MODEL" --device cpu --duration 1 --repeats 2
"$PY" -m benchmarks.spikes.magenta-realtime.messen --model "$MODEL" --device cuda --duration 4 --repeats 3
"$PY" -m benchmarks.spikes.magenta-realtime.messen --model "$MODEL" --device cuda --duration 4 --repeats 3 --seconds 60
```

Bei CPU-JIT kann der erste Lauf lange dauern. Optional andere Fixtures via `--signal sinus440` etc. Der native Hop ist 40 ms / 1920 Samples bei 48 kHz Stereo; --block 1920 ist fest. --rate steuert ausschließlich die Fixture-Rate. MusicCoCa resampelt intern auf 16 kHz und verwendet 10-s-Fenster (kürzere Eingaben werden gepolstert). Kein Audio verlässt den Rechner.

Die Messung nutzt den gemeinsamen runner-Parser und dessen Sampler, common.timed/summarize/make_result sowie das Ergebnisformat. Der Torch-spezifische runner.run wird nur im Dry-Run verwendet; JAX liefert hostmaterialisierte PCM-Daten, deshalb kein Torch-Sync. Kalt: Laden/JIT, Embedding, erste Ausgabe; warm: je 40-ms-Block fortlaufender Zustand, p50/p95/p99 und einzelne RTF in JSON. Hörprobe und JSON/MD in benchmarks/results/local/magenta-realtime-*. Kein Gate, keine echte Control-to-audio-Messung oder Underrun-Zahl. VRAM-Abtastung per nvidia-smi, unter WSL ggf. keine Prozesswerte. 

## Risiken / Rückbau

Installation, JIT, Blackwell-Tauglichkeit, VRAM und Hörprobe auf RTX 5080 nicht gemessen. Wheelauflösung (insbesondere CUDA-Laufzeit) und vollständiger Netzfrei-Nachweis am Zielrechner noch offen. Inferenz liest ausschließlich vorab hashgeprüfte Dateien; keine Downloadfunktion aufgerufen. Bei fehlendem Gewicht oder CUDA-Gerät Abbruch. Keine automatische Freigabe.

Rückbau: `.\benchmarks\spikes\magenta-realtime\install.ps1 -Entfernen` entfernt nur das eigene WSL-venv einschließlich Gewichte. Lokale Ergebnisordner separat löschen. Keine Änderung am Hauptdienst.
