# RAVE – WP02

Gate: `nicht_gemessen`.

## Quellen und Version

https://github.com/acids-ircam/RAVE (README und dort genannte Abschnitte, Abruf 24.11.2026). Untersuchte Variante: v2.4 beta. Geprüfter README-Stand: [7280bd5c11890b2043c5591f8da0ea5f4d5bf647](https://github.com/acids-ircam/RAVE/blob/7280bd5c11890b2043c5591f8da0ea5f4d5bf647/README.md). Abhängigkeitspins und Gewichts-Hashes separat.

## Lizenz und Gewichte

Code: CC BY-NC 4.0 (LICENSE; nicht kommerziell, Namensnennung; kommerzielle Nutzung separat klären).

Gewichte: README: pretrained models / Export; nur selbst exportiertes oder geprüftes lokales TorchScript, Größe und Gewichtslizenz offen. Keine Weitergabe ohne Prüfung der konkreten Lizenz.

## Modus und Voraussetzungen

Quellenbasierter Kandidatenmodus: `streaming`, keine Freigabe. README: Export, High-level manipulation, Offline usage. Streaming-Export nutzt gecachte Convolutions; sonst Klickartefakte. Latentprojektion, Temperatur, receptive_field in Samples; GPU laut README experimentell. CPU zuerst; CUDA/PyTorch Version, sm_120, Windows/WSL2 und VRAM nicht belegt.

## Messplan und Risiken

Causal/raspberry-Variante, Blockgröße aus Export, 10 min stateful Verarbeitung und Impulsantwort. Kalt/Warm, erste Ausgabe, Block-RTF p50/p95/p99, Peak-VRAM für Prozess und ganze GPU, CPU/GPU, Hörprobe und Artefakte, tatsächliche Control-to-audio-Latenz. Keine fremde Leistungszahl als eigene Messung. Exakte Hop-/Kontextwerte, Abhängigkeitspins und Gewichtshashes soweit nicht oben angegeben offen. Keine Installation ohne Prüfung des fremden Codes. Zielhardware nicht gemessen.


## AUFGABE-23: erster messbarer Kandidat

Statt des noch nicht identifizierten Raspberry-Exports dient der vom Intelligent Instruments Lab veröffentlichte kausale, modifizierte RAVE-v1-Gitarrenexport als erster Versuch (48 kHz, 2048 Samples, 16 latente Dimensionen). Modellkarte: https://huggingface.co/Intelligent-Instruments-Lab/rave-models ; gepinnter LFS-Pointer mit 163881670 Bytes und SHA-256: https://huggingface.co/Intelligent-Instruments-Lab/rave-models/commit/8471a1691f659ce52fcb2bb393afcc6f80187b17 . Modelllizenz CC BY-NC 4.0, Namensnennung Intelligent Instruments Lab (DOI 10.57967/hf/1235). Kein kommerzieller Einsatz. Der Export ist TorchScript (ausführbar), daher nur nach ausdrücklicher Vertrauensentscheidung; Hash schützt Integrität, nicht gegen bösartigen Code. Der öffentliche Modellhost kennzeichnet das Dateiformat als verdächtig; die Herkunft ist vor dem Laden zu prüfen. Kein Training und kein Fremdpaket nötig; allein Torch 2.7.1+cu128 (Windows-Wheel: https://download.pytorch.org/whl/cu128/torch/). Transitive Abhängigkeiten werden bei der Installation lokal festgehalten, nicht vorab vollständig gepinnt.

Im Repo-Root (Windows, Python 3.11):
```powershell
.\benchmarks\spikes\rave\install.ps1
.\benchmarks\spikes\rave\install.ps1 -ModelleLaden
$py = ".\.venv-spike-rave\Scripts\python.exe"
$weight = ".\.venv-spike-rave\weights\guitar_iil_b2048_r48000_z16.ts"
$sha = "02458214e23890d6818504319a5b9903eabfe87a524491f6524f453e7f3dbcf0"
& $py -m benchmarks.spikes.rave.messen --dry-run
& $py -m benchmarks.spikes.rave.messen --model $weight --sha256 $sha --rate 48000 --block 2048 --device cpu
& $py -m benchmarks.spikes.rave.messen --model $weight --sha256 $sha --rate 48000 --block 2048 --device cuda
& $py -m benchmarks.spikes.rave.messen --model $weight --sha256 $sha --rate 48000 --block 2048 --device cuda --seconds 600
& $py -m benchmarks.spikes.rave.messen --model $weight --sha256 $sha --rate 48000 --block 2048 --device cuda --signal impuls
```

Runner schreibt result.json, result.md und Hörproben lokal; zusätzliche rave-blocks-*.jsonl mit synchronisierten Blockzeiten, RTF-Perzentilen und erster Blockzeit (Seed 0 kalt, weitere warm). Unvollständige letzte Eingabeblöcke werden ausgelassen, der Zustand bleibt über Wiederholungen erhalten; --seconds 600 misst 10 Minuten Wallclock, nicht 10 Minuten Audio. Kein Echtzeit-Pacing/Underrun-Test, keine Control-to-audio-Messung. RTX-5080-Inferenz, VRAM, CPU und Exportkompatibilität nicht gemessen. Rückbau: install.ps1 -Entfernen, lokale Ergebnisse separat entfernen.
