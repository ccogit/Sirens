# AUFGABE-12 – Qwen3-TTS VoiceDesign

PR #65, extern/KETTE-P11 → integration/sirens-production. Nach AUFGABE-11.

## Umsetzung und Abnahme

| Abnahmepunkt | Beleg |
|---|---|
| VoiceDesign statt CustomVoice | workers/production_assets/worker.py: load_speech_model, speech, speech_batch; unveränderter text, instruct aus prompt, language aus Request (Standard English), kein Speaker-Preset/Cloning |
| Konfiguration | Worker(tts_model=…) bzw. vertrauenswürdige lokale SIRENS_PRODUCTION_CONFIG mit tts_model, bestehender tts_snapshot bleibt kompatibler Pfadparameter. Lokaler gepinnter Snapshot, config.json mit tts_model_type=voice_design; falsche Revision, Lizenz, Modelltyp, fehlender Prompt und fehlender Pfad führen zu expliziten AssetError-Meldungen |
| 48 kHz PCM24 und Dauer | Bestehender write_wav mit resample_poly und soundfile PCM_24 im Worker; inspect_wav misst Frames/rate, Dauer, Hash und technische Werte. Keine Kürzung der gesprochenen Worte; Slotüberschreitung bleibt Fehler |
| Provenienz | assets.json / asset_provenance.json: source.model, backend=qwen3-tts-voicedesign, revision=lokaler Snapshot-SHA, seed, license=Apache-2.0, voice_language, voice_clone=false, prompt, text; bestehende Lizenzfreigabe und Cache-Schlüssel bleiben wirksam |
| Ein Modellladen pro Run | render_assets sammelt nur freigegebene, nicht gecachte Speech-Cues; Worker.generate_speech_batch startet einen Prozess mit einer zentralen Lease; speech_batch lädt genau einmal, setzt Seed je Cue. Reuse und Cache-Hits erzeugen keinen GPU-Job. Manifest-Reihenfolge bleibt unverändert |
| Offline-Mock-Tests | tests/production/test_assets_voicedesign.py: Qwen-/Torch-API-Mocks, ein Loader-Aufruf für zwei Cues, exakte Texte/Prompts, per-Cue Seeds, native Rate an write_wav; Mock-Subprozess mit 48k/24bit-Fixtures, eine Lease, ein Batch, Dauer/Provenienz/Cache, falsche/fehlende Konfiguration |
| Lokaler Einzelcue | PowerShell-Aufruf unten; nicht gemessen |

Reuse (REUSE-AMM.md): vorhandene K04 AMM-/SecondRoom-Resolver, K00-Lizenz-/Cache-/GPU-Lease, Worker-Resampling und PCM24-Ausgabe (REUSE/ADAPT). Keine zusätzliche Sample-DB, kein Live-Writer, keine neue GPU-Verwaltung. ADAPT des vorhandenen Qwen-Workers aufgrund belegter CustomVoice-/VoiceDesign-Inkompatibilität aus AUFGABE-12.

## Lokale Konfiguration und Einzelcue (Windows)

In der bestehenden UTF-8-Konfiguration außerhalb von Git (`SIRENS_PRODUCTION_CONFIG`), `tts_model` als absoluter lokaler Snapshot-Pfad (Verzeichnisname = 40-stelliger Commit-SHA), `asset_python` als vorhandene Asset-Worker-venv. Falls `tts_snapshot` noch gesetzt ist, muss es denselben VoiceDesign-Snapshot bezeichnen oder entfernt werden. In `generated_sources.speech` backend=qwen3-tts-voicedesign, revision=Snapshot-SHA, license=Apache-2.0, license_confirmed=true nach bestätigter Lizenzprüfung, use=production; confirmed_gap_ids nur tatsächlich belegte Lücken. Keine automatische Modellinstallation oder Downloads.

Der folgende direkte Worker-Rauchtest ist ausschließlich für den Koordinator nach ausdrücklicher GPU-Freigabe und sichergestellter exklusiver GPU-Lease/Handoff gedacht. Kein paralleler Modell-/Live-Job und kein Ersatz für den regulären App-Lauf mit zentraler Lease.

```powershell
$cfg = Get-Content -Raw -Encoding UTF8 $env:SIRENS_PRODUCTION_CONFIG | ConvertFrom-Json
$dir = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
[IO.Directory]::CreateDirectory($dir) | Out-Null
$job = Join-Path $dir "job.json"
$out = Join-Path $dir "cue.wav"
$payload = @{
    kind = "speech"
    model_dir = $cfg.tts_model
    output = $out
    request = @{
        id = "smoke"; kind = "speech"; seed = 101
        text = "A calm test sentence."
        prompt = "Calm close-miked spoken English, natural pauses, no singing."
        language = "English"; duration_seconds = 10
    }
}
[IO.File]::WriteAllText($job, ($payload | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
& $cfg.asset_python workers/production_assets/worker.py $job
if ($LASTEXITCODE -ne 0) { throw "VoiceDesign worker failed" }
py -3.11 -c "import sys,json; from sirens.production.assets import inspect_wav; print(json.dumps(inspect_wav(sys.argv[1],duration_seconds=10,speech=True),indent=2))" $out
```

Erwartet: WAV im temporären Ordner, PCM24 48000 Hz, Mono oder Stereo, positive Frames, duration_seconds=frames/48000, SHA256, Peak/RMS und keine Clips. Worttreue/Prompt-Treue anhören; Dauer/VRAM/RTF lokal protokollieren. Für die volle Manifest-/Provenienz-Abnahme anschließend App-Run mit genau einem freigegebenen Cue und obiger Konfiguration (zentrale GPU-Lease); für einmaliges Laden zwei uncached Cues im selben Run messen. Keine Audiodateien ins Repository.

## Prüfstatus / Risiken

- Vollständiger Checkout im Container blockiert: `git ls-remote https://github.com/ccogit/Sirens.git` → `fatal: unable to access ... Could not resolve host: github.com` (128). GitHub-Schreibzugriff funktioniert. Tests geschrieben, nicht ausgeführt; GitHub Actions abgeschaltet. Koordinator: `py -3.11 -m unittest discover -s tests -v`; gezielt `py -3.11 -m unittest discover -s tests/production -p test_assets*.py -v`.
- Echte Qwen-API-/CUDA-/Resampling-/Hörprüfung nicht gemessen. Worker-Timeout gilt für den ganzen Batch; bei Prozessfehler sind alle Cache-Misses des Batches explizit als Fehler markiert (kein partieller Cache-Publish). Bestehende Slotprüfung kann bei langen Cues Neuplanung erfordern.
- Owner-Grenze: integration.py liest bisher tts_snapshot und reicht es als model_dir weiter. Der Worker liest tts_model aus der bestehenden settings()-Funktion, wenn kein expliziter Pfad übergeben wurde. Eine spätere direkte Übergabe des neuen Schlüssels durch die Kompositionswurzel wäre sauberer; programmatisch injizierte RealBackend.options mit ausschließlich tts_model (ohne lokale Konfigurationsdatei) werden dadurch noch nicht berücksichtigt. Keine Änderung außerhalb der Owner-Pfade.
- Keine neue Qualitäts- oder kommerzielle Freigabebehauptung. Zielrechnerprüfung und Review offen.
