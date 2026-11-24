# G1 RAVE (IIL-Gitarrenexport, kausal) – Messung am Zielrechner (24.11.2026)

**Gate: grün für den Modus `streaming`** (Block 2048 Samples @ 48 kHz = 42,7 ms; nur nichtkommerziell).

- Zielrechner: Windows 11, RTX 5080 16 GB, Treiber 621.24; Torch 2.7.1+cu128 (`sm_120`), fp32, TorchScript.
- Modell: Intelligent Instruments Lab `rave-models` @ `8471a1691f659ce52fcb2bb393afcc6f80187b17`,
  `guitar_iil_b2048_r48000_z16.ts` (modifiziertes RAVE v1, kausal, 16 latente Dimensionen, mono).
  Lizenz CC BY-NC 4.0 (Code ebenfalls CC BY-NC 4.0): kein kommerzieller Einsatz.
- TorchScript ist ausführbarer Code: geladen nur nach Größen- und SHA-256-Prüfung (Integrität, kein Schutz
  gegen bösartigen Inhalt; Herkunft = IIL-Repo am gepinnten Commit).
- Messung: `benchmarks.spikes.rave.messen` (zustandsbehaftet, Block für Block `decode(encode(x))`, synchronisiert)
  und ein Zusatzlauf über 120 s Audio mit `torch.cuda.max_memory_allocated` und Steuerlatenztest.

| Fall | p50 je Block | p95 je Block | p99 je Block | RTF p95 je Block | Hinweis |
|---|---:|---:|---:|---:|---|
| GPU kalt (Prozessstart, Seed 0, 234 Blöcke) | 9,5 ms | 11,8 ms | 26,6 ms | 0,28 | erster Block 5,4 s (Laden 0,5 s) |
| GPU warm, 5 Durchläufe × 234 Blöcke | 8,8–9,7 ms | 11,1–17,7 ms | 12,9–23,9 ms | 0,26–0,41 | erster Block 9–12 ms |
| GPU 120 s Audio am Stück (2812 Blöcke) | 8,9 ms | 11,7 ms | 20,2 ms | 0,27 | max 26,9 ms; 2 Blöcke > 42,7 ms (Anlauf) |
| CPU warm, 3 Durchläufe × 234 Blöcke | 26,1 ms | 28,0–28,6 ms | 29,4–31,8 ms | 0,66–0,67 | knapp, nicht empfohlen |

Speicher (GPU): `max_memory_allocated` 294 MiB, reserviert 334 MiB; ganze GPU per nvidia-smi höchstens
2,3 GiB (davon ca. 1,3 GiB Grundlast anderer Prozesse) → rund 13,6 GiB frei.

Steuerung zu Audio: Latent-Offset (+1,5 auf z0–z3) ab Block 20 wirkt bereits im selben Ausgabeblock
(erste Abweichung bei Sample 113 von 2048); vorher bitgleich bei gleichem Seed. Damit Steuerlatenz ≈ ein Block
Pufferung (42,7 ms) + Rechenzeit (p95 11,7 ms) + Audiogeräte-Puffer ≈ 55 ms zuzüglich Gerät, deutlich unter 250 ms.

Ausgabe (Eingang Klick 120 BPM, 10 s): 48 kHz mono, RMS −38 bis −39 dBFS, Peak −1,6 bis −3,2 dBFS,
spektrale Flachheit Median 0,006–0,007 (tonal, nicht Rauschen/Stille). Noch nicht durch Hören beurteilt;
kein Echtzeit-Pacing-/Underrun-Test mit echtem Audiogerät, kein 10-Minuten-Lauf.

Ergebnisse lokal: `benchmarks/results/local/rave-57e11f3dd2` (GPU), `rave-d4e6a032ac` (CPU),
`rave-blocks-a32f4e51c8.jsonl`, `rave-blocks-48e341d115.jsonl`, `rave-extra.json`.

## Gewichte (SHA-256)

| Datei | Bytes | SHA-256 |
|---|---:|---|
| guitar_iil_b2048_r48000_z16.ts | 163881670 | 02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0 |

## Installation (Zielrechner)

```powershell
py -3.11 -m venv .venv-spike-rave
.\.venv-spike-rave\Scripts\python.exe -m pip install --only-binary=:all: --index-url https://download.pytorch.org/whl/cu128 torch==2.7.1+cu128 torchaudio==2.7.1+cu128
# Gewicht hashgeprüft über install.py (obtain_weight), ohne interaktive Abfrage:
.\.venv-spike-rave\Scripts\python.exe -c "from pathlib import Path; from benchmarks.spikes.rave.install import manifest, obtain_weight; print(obtain_weight(manifest(), Path('.venv-spike-rave/weights')))"
$sha = "02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0"
.\.venv-spike-rave\Scripts\python.exe -m benchmarks.spikes.rave.messen --model .\.venv-spike-rave\weights\guitar_iil_b2048_r48000_z16.ts --sha256 $sha --rate 48000 --block 2048 --device cuda --duration 10 --repeats 5
```
numpy fehlt im venv (nur Warnung von Torch, ohne Einfluss).
