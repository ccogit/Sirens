# AUFGABE-07 / WP07 – DEMON (Teilstand / Übergabe)

Depends-on: WP06, WP22, Gate G1 DEMON (noch nicht gemessen).

## Umsetzung
- Separater Adapter/IPC-Worker, gesperrter Descriptor, Installationswrapper zum vorhandenen
  isolierten Spike und dessen Versionspins. Kein Download ohne ausdrückliche Zustimmung.
- Adapter prüft Snapshot und Vendor-Pin, setzt Offline-Schalter und weights_only; Session,
  prepare_source, encode_text, stream, tick und decode entsprechen dem Spike.
- Tests mit FakeBackend ohne Modellimporte. Epoch, Prompt, Denoise, Seed, Bypass,
  kooperativer Abbruch zwischen Ticks. Keine fertige PCM-/Session-Integration.
- Hook WP07 für Registry, Session, UI und späteren Delay-Ausgleich.
- Lokaler Engine-Benchmark mit drei Profilen und 30 Minuten Standardlauf, Ergebnisformat
  benchmarks/result.py. Ergebnisordner außerhalb des Repos.

## Abnahmepunkte
1. Teilbeleg: tests/realtime/test_demon.py (Lebenszyklus, stale Epoch, Bypass, Ladefehler,
   Abbruch, ungültige PCM, Descriptor). Fake bildet die Adapter-Backend-Schnittstelle nach,
   nicht Torch; tatsächliche Session/IPC und Quellenwechsel im Browser noch offen.
2. Teilbeleg: fehlende Gewichte/Umgebung führen beim Laden zu Unavailable mit
   Installationshinweis; Registry sperrt Descriptor. Negativtest mit fehlendem Backend.
3. Nicht gemessen: echtes Audio, drei hörbare Transformationen, 30 Minuten ohne Aussetzer,
   G3, Delay/Insert-Quote. Engine-Skript liefert Hörproben und Zeitwerte, aber keinen
   Browser-/Playback-Nachweis. Kein behauptetes Streaming.
4. Lokaler Checkout nicht möglich: fatal: unable to access
   'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com.
   CI maßgeblich; bei Übergabe noch nicht bestätigt. board.md bewusst unverändert.

## Versionen / Grenzen
DEMON-Code 96acc905204d54bfd3055084ca8e9df8a6d9a33f, AGPL-3.0-or-later / MIT-Anteile.
ACE-Step-Gewichte 19671f406d603126926c1b7e2adc169acbcade22, MIT laut Spike-Manifest;
safetensors und SHA-256-geprüftes silence_latent.pt mit weights_only. Keine Weitergabe.
Torch 2.9.1+cu128, torchvision 0.24.1+cu128, torchaudio 2.9.1+cu128, torchao 0.17.0:
Pins aus WP22, nicht ungeprüft auf Torch 2.7.1 wechseln. Upstream uv.lock war beim
Spike nicht verfügbar; transitive Pins und Windows-Wheels bleiben offen. Installer
bricht ohne Lock ab; kein Quellbau. Ziel RTX 5080 16 GB, tatsächlicher Bedarf unbekannt.
PCM höchstens 131072 Frames je Anfrage, 48 kHz Stereo; Decodefenster 0,36 s aus Spike.
Der gesperrte Offline-Descriptor mit hop_frames=1 ist nur ein Schema-Platzhalter,
keine tatsächliche Freigabe. Style-Blend, tatsächlicher Latenzausgleich und
kontinuierliche Ausgabe fehlen; keine nicht belegten Parameter vortäuschen.

## Nachstellen
```powershell
python -m unittest discover -s tests -v
python -m benchmarks.demon.messen --dry-run
.\workers\demon\install.ps1
.\workers\demon\install.ps1 -ModelleLaden
& .\.venv-spike-demon\Scripts\python.exe -m benchmarks.demon.messen --source D:\Musik\song.wav --output D:\Messungen\demon-wp07 --seconds 1800
```
Bezug nur nach Lizenzprüfung und Bestätigung. Lokale WAV-Hörproben nicht einchecken.
Rückbau: Worker nicht freigeben, .\workers\demon\install.ps1 -Entfernen
(entfernt auch DEMON-Spike-Umgebung), lokale Messungen bei Bedarf löschen.

## Übergabe
Fertig: gesperrtes Grundgerüst, Adapter und IPC, Installation am vorhandenen Messpfad,
Fake-Tests, Engine-Messskript, Hook. Offen: vollständiger Windows-Wheel-Lock und
verifizierter Modelllauf; echte Session-/UI-/Delay-Integration, Style-Blend nur falls
belegt, G1/G3 und CI. Nächster Schritt: CI prüfen, mit Koordinator den gemessenen
DEMON-Pfad und dessen Pins abgleichen, dann Hook konkretisieren und Playback testen.
Fehlerausgabe: lokaler Git-Checkout scheitert mit „Could not resolve host: github.com“;
WP22 dokumentiert „Upstream uv.lock fehlt; Paketpins vervollständigen, siehe Bericht“.
Kein lokaler Modelllauf, keine behauptete CI-Freigabe.
