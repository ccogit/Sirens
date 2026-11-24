# WP02 – Spike-Übersicht

Alle Gates `nicht_gemessen`. Lizenzampel ist nur Vorprüfung, keine Gate-Freigabe. Reihenfolge priorisiert gesperrte Folgeketten.

| Reihenfolge | Kandidat | Lizenzampel | Modus (Hypothese) | Gate |
|---|---|---|---|---|
| 1 | [RoFormer / DrumSep](roformer-drumsep/BERICHT.md) | gelb | offline | RoFormer: green (offline, [Messung](../results/g1/roformer.md)); DrumSep: nicht_gemessen |
| 2 | [SAM Audio](sam-audio/BERICHT.md) | gelb | offline | nicht_gemessen |
| 3 | [DEMON](demon/BERICHT.md) | gelb | streaming (zu prüfen) | nicht_gemessen; [Teilstand und Befehle](demon/BERICHT.md#kopierbare-befehle-windows-repo-root) |
| 4 | [RAVE](rave/BERICHT.md) | gelb | streaming (zu prüfen) | nicht_gemessen |
| 5 | [AFTER](after/BERICHT.md) | gelb | streaming / lookahead (zu prüfen) | nicht_gemessen |
| 6 | [Stable Audio 3](stable-audio-3/BERICHT.md) | gelb | lookahead / offline | nicht_gemessen |
| 7 | [Magenta RealTime 2](magenta-realtime/BERICHT.md) | gelb | offline (WSL2/JAX; [Installations- und Messbefehle](magenta-realtime/BERICHT.md#installation-und-aufruf-windows-11--wsl2)) | nicht_gemessen |
| 8 | [GPU Audio SDK](gpu-audio-sdk/BERICHT.md) | gelb | streaming (DSP) | nicht_gemessen |
| 9 | [Beat This! Live](beat-this-live/BERICHT.md) | grün | streaming (Beat-Tracking) | nicht_gemessen |
| 10 | [Signalsmith Stretch](signalsmith-stretch/BERICHT.md) | grün | streaming (DSP) | nicht_gemessen |

1. Code-Commit, Abhängigkeiten, Gewichte (Quelle, Lizenz, Größe, Hash) vor Bezug festlegen; keinerlei automatische Downloads. Separate Umgebung außerhalb der produktiven venv.
2. Baseline: `python -m benchmarks.baseline --out benchmarks/results/local/baseline.json`.
3. Synthetische Fixtures: `python -m benchmarks.fixtures --out benchmarks/results/local/fixtures`.
4. Kandidaten einzeln CPU/GPU prüfen, keine parallelen Modelle, dann unter normaler Visualisierungslast wiederholen. Berichte enthalten den jeweiligen Messplan. Keine Freigabe allein durch RTF < 1.
5. Nur A0 entscheidet Gates; JSON und Hörproben lokal, keine Musik oder Gewichte committen. KETTE-26: Separation; 27: SAM; 33: DEMON; 34: RAVE/AFTER; 35: SA3; 36: Magenta.

## Aktueller Teilstand

Außer dem experimentellen RoFormer-Bezug erzeugen/leeren Installationsskripte nur isolierte Umgebungen; Modellbezug bleibt gesperrt. Experimentelle Inferenzpfade existieren für RoFormer, RAVE, SA3 und SAM Audio; keine Hardwareabnahme. Aufruf im Repo-Root ohne Modell:

```powershell
python -m benchmarks.spikes.roformer-drumsep.messen --dry-run
python -m benchmarks.spikes.rave.messen --dry-run
python -m benchmarks.spikes.stable-audio-3.messen --dry-run
python -m benchmarks.spikes.sam-audio.messen --dry-run
```

Nach manuell geprüfter Installation im jeweiligen venv: `python -m benchmarks.spikes.<kandidat>.messen --model <lokaler Pfad> --device cpu` bzw. `--device cuda`. RAVE benötigt zusätzlich `--sha256 <Hash>` des TorchScript-Exports; SA3 erwartet den lokalen HF-Cache, SAM den lokalen Snapshot. Kein vollständiger Hardware- oder Streaming-Nachweis. RAVE/AFTER/GPU Audio SDK haben nichtkommerzielle Lizenzbestandteile; keine kommerzielle Freigabe.

## AUFGABE-21 – Versuch RoFormer (Windows, Repo-Root)

Nur nach Prüfung des Berichts und der Lizenz, mit Python 3.11 und Git im PATH. Der transitive Lock ist noch nicht reproduzierbar; Installation und Hardwarelauf sind nicht abgenommen. Ohne Schalter wird nur ein venv angelegt.

```powershell
.\benchmarks\spikes\roformer-drumsep\install.ps1
.\benchmarks\spikes\roformer-drumsep\install.ps1 -ModelleLaden
$py = ".\.venv-spike-roformer-drumsep\Scripts\python.exe"
$weight = ".\.venv-spike-roformer-drumsep\weights\MelBandRoformer.ckpt"
$sha = "87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e"
& $py -m benchmarks.spikes.roformer-drumsep.messen --dry-run
& $py -m benchmarks.spikes.roformer-drumsep.messen --model $weight --sha256 $sha --device cpu
& $py -m benchmarks.spikes.roformer-drumsep.messen --model $weight --sha256 $sha --device cuda
```

DrumSep bleibt gesperrt (Gewichtslizenz, Größe, Hash). Reihenfolge der weiteren Bearbeitung: SAM Audio, Stable Audio 3, dann übrige Kandidaten. SAM und SA3 benötigen zunächst authentifizierte, lizenzkonforme Metadaten und vollständige Pins; ihre bestehenden Dry-Runs sind keine Freigabe zur Modellinstallation. Details in den Kandidatenberichten und der Ergebnisdatei AUFGABE-21.
