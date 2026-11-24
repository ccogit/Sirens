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
