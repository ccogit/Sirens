# AUFGABE-10 – Instrument-Host unter Windows

**Stand: implementiert, zur Zielrechnerprüfung; nicht abgenommen.** PR [#66](https://github.com/ccogit/Sirens/pull/66), extern/KETTE-P10 → integration/sirens-production. Ausschließlich eigene Instrument-Dateien, Tests und diese Ergebnisdatei geändert. Registeränderungen des Koordinators per Merge a84eea0b übernommen, keine eigenen Registeränderungen.

## Hostentscheidung und Reuse

Genau ein Produktionshost: **Pedalboard über den bestehenden AMM/WB-Renderer**. Der erste echte Lauf hat diesen Pfad bereits genutzt (Aufgabenbefund). DawDreamer ist daher trotz früherem Rauchtest keine zweite Produktionsoption; kein neuer Renderer und kein automatischer Synth-Fallback. Installation ausschließlich in der Instrument-Worker-venv, keine Audio-/Modellimporte im Sirens-Hauptprozess.

| Funktion | Bestand / geprüfter Quellstand | Entscheidung | Lücke / Test |
|---|---|---|---|
| Offline-VST3 | AMM 26c5ce2fe9641ed958414f78d58643527bc3032f, backend/app/audio_engine/render_instruments.py: render_vst3_instrument | REUSE | Echter Windows-Render nicht gemessen |
| Laden, Warm-up, Parameter | AMM plugin_control.load/render_instance, render_effects.load_vst3 | REUSE | Kein neues Host-Backend |
| Plugin-/Presetauflösung | AMM plugins.plugin_path, factory_presets.preset_file/apply_preset | ADAPT | Nur workerlokale, temporäre Lookup-Anpassung; Bundle-/Datei-Fixtures |
| Konfiguration | Sirens integration.settings, AMM core/config.py | REUSE/ADAPT | Worker-Umgebung, keine globale Änderung; subprocess-Mock |

## Installation und lokale Konfiguration

PowerShell, aus dem Sirens-Checkout. `$ammBackend` bezeichnet das vorhandene AMM-Verzeichnis music-workbench/backend; `$venv` den lokalen Instrument-Worker-Ordner unter workers/ (nicht committen).

```powershell
py -3.11 -m venv $venv
$workerPython = Join-Path $venv 'Scripts/python.exe'
& $workerPython -m pip install -r (Join-Path $ammBackend 'requirements.txt') -r workers/production_instruments/requirements.txt
```

Die ergänzende Liste pinnt Pedalboard 0.9.16, NumPy 1.26.4, SoundFile 0.12.1 wie im geprüften AMM-Stand. Installation nur manuell auf dem Zielrechner; keine Downloads im Test oder Worker. Bereits vorhandene, kompatible Worker-venv kann weiterverwendet werden.

In der bestehenden vertrauenswürdigen UTF-8-Konfigurationsdatei (`SIRENS_PRODUCTION_CONFIG`, schema_version=1) zusätzlich `wb_data_dir` auf ein vorhandenes lokales WB-Datenverzeichnis setzen. Es wird ausschließlich im Environment des Render-Subprozesses als WORKBENCH_DATA_DIR gesetzt. Ohne Schlüssel gilt das bestehende Worker-Environment bzw. der WB-Default /data. Keine Kopie von Plugins oder Presets nötig. Beispielstruktur (Platzhalter, keine tatsächlichen Installationspfade oder Hashes):

```json
{
  "schema_version": 1,
  "instrument_python": "C:/local/worker/Scripts/python.exe",
  "amm_backend": "C:/local/AMM/music-workbench/backend",
  "wb_data_dir": "C:/local/workbench-data",
  "instrument_revision": "<actual AMM/host/plugin revisions>",
  "patches": {
    "tight_kick": {
      "instrument": {
        "type": "vst3",
        "plugin": "C:/local/plugins/Surge XT.vst3",
        "preset_file": {
          "path": "C:/local/presets/kick.fxp",
          "sha256": "<actual SHA256, lowercase>"
        },
        "gain_db": -6
      },
      "revision": "<actual patch revision>",
      "license": "<verified license>",
      "use": "<confirmed use>"
    }
  }
}
```

Absolute Plugin- und Presetpfade stammen ausschließlich aus der Betreiberkonfiguration, nie aus dem Plan. Optionaler AMM-Plugin-Subname (#Name) bleibt erhalten. Windows x64: Bundle-Ordner wird auf Contents/x86_64-win/<Bundle-Dateiname> aufgelöst; Linux/macOS bleiben unverändert. Relative WB-Pluginreferenzen und vorhandene WB-Preset-IDs bzw. State-Bindungen bleiben kompatibel. Für externe Presets ist der absolute Pfad plus SHA256 maßgeblich; AMM übernimmt die vorhandene FXP-/JSON-Dekodierung und Zustandsanwendung. Kein automatisches Suchen in beliebigen Verzeichnissen. Hash kann lokal mit Get-FileHash -Algorithm SHA256 ermittelt werden (Kleinbuchstaben).

## Abnahmepunkte

| Punkt | Beleg | Prüfstatus |
|---|---|---|
| Ein Host + Installation | requirements.txt, AMM-Quellcode, Hostentscheidung oben | Quellstand geprüft; Installation nicht ausgeführt |
| Windows-Bundle, Linux/macOS unverändert | resolve_bundle; test_bundle_resolution (Windows-Flag auf beiden Plattformen) | Test geschrieben, nicht ausgeführt |
| wb_data_dir nur im Worker | WBWorker, test_worker_environment_is_private (Mock subprocess, unverändertes Parent-Environment, UTF-8) | Test geschrieben, nicht ausgeführt |
| Externe Presets/Plugins ohne Kopie | local_bindings, verified_preset, WBWorker.prepare; test_external_plugin_and_preset_without_copy, test_prepare_rejects_changed_preset_before_cache, test_legacy_wb_lookup_and_errors | Tests geschrieben, nicht ausgeführt |
| Klare Fehler | fehlender Interpreter/AMM/Preset/Plugin, Hash-Abweichung und Bundle unvollständig mit Handlung; test_host_missing, Bundle-/Lookup-Tests, Worker-Fehlerweitergabe | Tests geschrieben, nicht ausgeführt |
| 1-Takt-Render | smoke.py und Befehl unten | nicht_gemessen |

## Zielrechnerprüfung

```powershell
py -3.11 -m unittest discover -s tests -v
py -3.11 -m unittest discover -s tests/production -p 'test_instruments*.py' -v
$env:SIRENS_PRODUCTION_CONFIG = '<lokale JSON-Konfiguration>'
py -3.11 workers/production_instruments/smoke.py --output '<neuer lokaler Ordner außerhalb Git>' --patch tight_kick
```

Erwartet: JSON mit render_seconds, sample_rate=48000, frames=91429 (1 Takt bei 126 BPM), einem Stem mit Hash, Backend amm_wb_vst3 und Peak; stems/smoke.wav (PCM24 Stereo, nicht still, ausreichender Headroom), stems.json und sidechain-control.wav. Kein Cache im Rauchtest, kein Live/GPU/Netz. Mit echtem Surge-Preset messen und tatsächliche Versionen, Renderzeit und Peak nachtragen. Keine Audioartefakte committen.

## Abweichungen, offene Risiken und Prüfstatus

- Vollständiger Checkout nicht verfügbar: git ls-remote https://github.com/ccogit/Sirens.git refs/heads/integration/sirens-production → Exit 128, fatal: unable to access ... Could not resolve host: github.com. Keine lokalen Unittests durchgeführt. GitHub Actions abgeschaltet; kein CI-Grün behauptet und nicht darauf gewartet. Maßgeblich bleibt der Windows-Test des Koordinators.
- Wegen verbindlicher Dateigrenze wurde integration.py nicht verändert: WBWorker liest bei fehlendem explizitem wb_data_dir lazy die bestehende integration.settings-Konfiguration. Ein ausschließlich programmatisch an RealBackend übergebenes options-Dict ohne entsprechende Konfigurationsdatei reicht für diesen neuen Schlüssel noch nicht; falls benötigt, muss dessen Owner das optionale Keyword durchreichen.
- AMM-Lookups werden nur im separaten Renderprozess temporär ersetzt und anschließend wiederhergestellt. Schnittstellen sind am gepinnten AMM-Quellstand geprüft; eine abweichende lokale AMM-Version kann Anpassungen benötigen. Windows-ARM-Bundles sind nicht zugesagt; Ziel ist x64. Legacy-Preset-ID und Plugin-Revision bleiben operatorseitige Cache-Verantwortung; explizite Presetdateien werden vor Cache-Hits erneut gehasht.
- Tatsächliche Plugin-Scan-/Preset-Kompatibilität, Lizenz, Audioqualität und Laufzeit am Zielrechner offen. Keine erfundenen Messwerte.

## Übergabe an den Koordinator

Fertig: Implementierung und Test-Fixtures gepusht, Ein-Takt-Skript und Anleitung vorhanden. Offen: lokale Linux-/Windows-Tests und echter Windows-Render gemäß Befehlen. Nächster Schritt: Windows-Gesamttest ausführen, dann echte Instrument-venv und Presetdatei konfigurieren und smoke.py aufrufen. Fehlerausgabe der externen Umgebung siehe oben; keine CI vorhanden. PR Ready for review, kein Selbst-Merge.
