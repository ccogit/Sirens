# AFTER – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/acids-ircam/AFTER (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: v2 (v1 inkompatibel). Geprüfter README-Stand: [21298c907f469d6c7787c60dd38d46f98981b75c](https://github.com/acids-ircam/AFTER/blob/21298c907f469d6c7787c60dd38d46f98981b75c/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: CC BY-NC 4.0 (LICENSE.md; nicht kommerziell, Namensnennung; kommerzielle Nutzung separat klären).

Gewichte: README: Pretrained codecs und models; nubo.ircam.fr; Größe, Hash und separate Gewichtslizenz offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Changelog, Installation, Export, Notebooks. Diffusion kombiniert Timbre mit Audio-/MIDI-Struktur; v2 STFT-Codec AE_4096, 32 latente Dimensionen, Kompression 4096; export_stream.ts ist Codec, nicht automatisch vollständige Diffusion. Python 3.12; Max/Pd nn~ für Live; CPU/CUDA und MPS erwähnt, sm_120, Windows/WSL2, VRAM und Ende-zu-Ende-Hop nicht belegt.

## Messplan und Risiken

Zuerst Codec, dann komplette Diffusion über audio_to_audio_demo; falls nicht live, Lookahead oder RAVE. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.

Pretrained: https://nubo.ircam.fr/index.php/s/8NFD5gWwbkT4G5P ; Max4Live benötigt zur .ts auch die .png-Latentkarte. V2-Audio- und MIDI-Notebooks zuerst gegen gepinnte API prüfen.


## AUFGABE-23: lokaler v2-Export, Lookahead

Das gepinnte Notebook wurde aus GitHub gelesen: https://github.com/acids-ircam/AFTER/blob/21298c907f469d6c7787c60dd38d46f98981b75c/notebooks/audio_to_audio_demo.ipynb . Es beschreibt die Inferenz eines vollständigen TorchScript-Modells: Codec, Struktur- und Timbre-Encoder, Diffusionssampling mit 10 Schritten, Decoder; 44100 Hz und 64 latente Frames. Implementiert ohne Notebook-Fallback auf konstantes Timbre. Code-Referenz CC BY-NC 4.0, keine kommerzielle Freigabe. Nur Torch 2.7.1+cu128 zur Inferenz (Windows-Wheel: https://download.pytorch.org/whl/cu128/torch/); Python 3.11 für den Messpfad, Upstream-Training/Export laut README mit 3.12. Keine Trainingsabhängigkeiten installiert, transitive Auflösung nicht vollständig gepinnt.

**Blockade:** offizieller Share https://nubo.ircam.fr/index.php/s/8NFD5gWwbkT4G5P war im Webabruf nicht zugänglich. Konkretes v2-Audio-to-Audio-Gewicht, Dateiname, Lizenz, Bytezahl und Herausgeberhash nicht verifiziert. Kein automatischer Bezug und keine Lizenzannahme. Der Koordinator/Nutzer muss dort die konkrete Lizenz und Herkunft prüfen bzw. vom Projekt bestätigen lassen und einen vertrauenswürdigen vollständigen v2-Export bereitstellen (nicht nur den Codec). Bei eigenem Export den SHA-256 direkt nach der vertrauenswürdigen Erzeugung erfassen. Für Fremddateien einen unabhängig verifizierten SHA-256 verwenden; der Hash ist kein Sicherheitsnachweis. Lokale Quittung enthält Größe, Hash, Lizenz und Herkunft. Keine Checkpoint-Deserialisierung.

Repo-Root, Windows, Python 3.11:
```powershell
.\benchmarks\spikes\after\install.ps1
$export = Read-Host 'Pfad zum geprüften vollständigen lokalen v2 .ts-Export'
$sha = Read-Host 'Unabhängig geprüfter SHA-256'
$license = Read-Host 'Konkrete geprüfte Gewichtslizenz'
.\benchmarks\spikes\after\install.ps1 -ModelleLaden -LokalerExport $export -Sha256 $sha -Gewichtslizenz $license
$py = ".\.venv-spike-after\Scripts\python.exe"
$weight = ".\.venv-spike-after\weights\after-audio-to-audio.ts"
& $py -m benchmarks.spikes.after.messen --dry-run
& $py -m benchmarks.spikes.after.messen --model $weight --sha256 $sha --rate 44100 --duration 8 --device cpu
& $py -m benchmarks.spikes.after.messen --model $weight --sha256 $sha --rate 44100 --duration 8 --device cuda
```

Runner misst die ganze konditionierte Diffusionsinferenz (Lookahead); kein Block-Streaming behauptet. Struktur aus Fixture, Timbre aus unabhängigem synthetischem 440-Hz-Sinus. 64 Frames des Codecs (bei ratio 4096 ca. 5,94 s) pro Inferenz; zu kurze Eingabe wird abgelehnt. Ergebnis und Hörproben lokal. Kein Gate, keine Hardwaremessung. Offene Risiken: kompatibler vollständiger Export, separate Gewichtslizenz, mögliche interne CPU-Konstanten auf CUDA und zustandsbehaftete Encoder. Rückbau: install.ps1 -Entfernen.
