# AUFGABE-12 – Generative Performance Pads (WP12)

Stand: Übergabe, keine Produktfreigabe. Voraussetzungen: WP02/G1 Stable Audio 3, WP06, WP10. G1-Bericht: `benchmarks/results/g1/stable-audio-3.md`.

## Umsetzung und Abnahme

| Punkt | Beleg / Stand |
|---|---|
| 1 | `tests/realtime/pad_scheduler.test.mjs`: sechs Typen, exakter Startframe bei 120 BPM, Preview, verspätete Ergebnisse verschieben oder Dry, Queue-Limit, Phrasenraster und Stretch-Warnung. Test geschrieben, CI noch nicht bestätigt. |
| 2 | Derselbe Test: Konfidenz 0,1 ergibt Dry; keine automatische Quantisierung. |
| 3 | **Nicht gemessen**: `benchmarks/pads/measure.py` erzeugt 20 echte Warm-Jobs und wertet Renderzeiten im tatsächlichen JS-Scheduler aus. Das ist nur die Vorstufe, noch keine Browser-/Audio-End-to-End-Messung. G3 nicht bestanden/nicht gemessen. |
| 4 | `python -m unittest discover -s tests -v` maßgeblich im PR; lokal kein vollständiger Checkout möglich (DNS), CI-Ergebnis ausstehend. Board gemäß KETTEN.md nicht geändert. |

Adapter isoliert: explizites Load, Warmup, Jobvalidierung, PCM-Chunks, Unload und Heartbeat. CPU-Test `tests/realtime/test_stable_audio_pads.py` verwendet injizierten Fake statt Modell. Installationsweg mit externem InstallRoot, explizitem Modellbezug, offline Laufzeit, Revision und SHA-256-Prüfung. Kein Inpainting; Extend ist reine Prompt-Neugenerierung. Stärke ist Wet-Anteil beim Einsatz, nicht eine ungemessene Modellsteuerung.

## Nachstellen

PowerShell am Zielrechner (InstallRoot außerhalb des Repos, Lizenz und HF-Login erforderlich):

```powershell
.\workers\stable_audio\install.ps1 -InstallRoot C:\SirensModels\sa3 -ModelleLaden
$env:SIRENS_RT_STABLE_AUDIO_CACHE = 'C:\SirensModels\sa3\hf-cache'
& C:\SirensModels\sa3\venv\Scripts\python.exe benchmarks/pads/measure.py --p95-ms 430 --out C:\SirensModels\sa3\pads.json
py -3.11 -m benchmarks.result C:\SirensModels\sa3\pads.json
node --test tests/realtime/pad_scheduler.test.mjs
py -3.11 -m unittest discover -s tests -v
```

JSON im gemeinsamen Benchmarkformat; zusätzlich `jobs` und `deadline` (timely, shifted, dry, ratio). 430 ms ist die obere beobachtete Warmzeit aus G1, kein neuer p95-Messwert. G3 benötigt >=19/20 tatsächliche rechtzeitige Einsätze einschließlich Transfer, Dekodierung, Preview-Freigabe und Audioausgabe.

## Versionen, Grenzen, Risiken

- Stable Audio 3 Code MIT: `790793b89ddceea612be9ce42ff6830d18f6fa57`; small-music Gewichte Community-Lizenz, eingeschränkte kommerzielle Nutzung: `8bdfb53c6b0fbc62113cd571fd37373efe15fa14`; Gemma-Bedingungen für Textencoder prüfen.
- Python 3.11, Torch/Torchaudio 2.7.1+cu128, direkte G1-Pins in requirements.lock; transitive Pins und Hatchling nicht vollständig gelockt. Ziel RTX 5080 16 GiB; G1 kalt 9–21 s, Prozesspeak 2,2 GiB, warm ca. 1,7 GiB. Keine neue Hardwaremessung. 44,1 kHz Stereo; Ausgabe auf Sitzungsrate resamplen.
- Modell-API, Installationsskript, tatsächliche Prompttreue, Audioformat und Stretch/Pitch/Crossfade am Zielrechner noch zu prüfen. 30 s maximale Jobdauer; längere Takte ablehnen, Dry erhalten.
- Supervisor v1 lehnt Prozessparameter für Nicht-Mock ab und begrenzt PCM auf 1 MiB. Worker bietet daher begrenzte Abrufe; gemeinsamer Supervisor/Sitzung/Adressen nicht verändert. Manifest bewusst `available: false`; notwendiger Einbau als Hook `docs/realtime/hooks/WP12.md`. Keine produktive Nutzung behauptet.
- Rückbau: eigene Dateien/Commits revertieren, externe Worker-Umgebung bei Bedarf separat löschen; keine Bestandsdatei oder Originalmusik betroffen.

## Übergabe

Fertig: gepushte Scheduler-/Worker-Grundlage, Tests, Manifest, Installationspins, Benchmark-Vorstufe und Hook.
Offen: vollständige CI-Bestätigung, Supervisor-/Registry-Einbau, Browser-Audiointegration, tatsächliche 20 G3-Einsätze, verifizierter Installations- und Modellaufruf. 
Nächster Schritt: CI des PR prüfen, Fehler beheben; Hook mit KETTE-41/Koordinator abstimmen, fehlende Supervisor-Parameter und Chunk-Serialisierung innerhalb des freigegebenen Scopes ergänzen, dann 20 echte E2E-Jobs messen. 
Fehlerausgabe lokaler Checkout: `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. GitHub-API-Schreibzugriff funktioniert. CI bei letzter Abfrage noch ohne Workflow-Run für den abgefragten Commit.
