# Baseline am Zielrechner (WP00)

Der Koordinator führt die folgenden Befehle in einem vollständigen Checkout von `integration/sirens-rt` aus, ohne fremde lokale Änderungen zu überschreiben. Python 3.11 und Node 22 müssen im Pfad sein. Windows PowerShell:

```powershell
git status --short
git rev-parse HEAD
python --version
node --version
python -m unittest discover -s tests -v
python -m benchmarks.baseline --out benchmarks/results/local/baseline.json
python -m benchmarks.fixtures --out benchmarks/results/local/fixtures --rate 48000 --duration 4 --channels 2
```

Den SHA und die Testanzahl protokollieren. `baseline.json` erfasst OS, Python, Node, ffmpeg, NVIDIA-Treiber, GPU und VRAM in MiB, WSL-Verfügbarkeit, freien Speicher des Repo-Laufwerks und Git-SHA/Arbeitsbaumzustand. Fehlende oder nicht auswertbare Werkzeuge liefern `null` mit Hinweis; keine Roh-Ausgaben, Benutzernamen, Home-Pfade, Hostnamen oder WSL-Distributionsnamen werden gespeichert. Das Skript speichert unter Windows nur einen normalen Laufwerksbuchstaben, nicht UNC-Pfade. Auf POSIX ist `drive` null.

Audio-Gerät, Audiotreiber, tatsächliche Ausgaberate und Browser-Audio-Latenz sind separat am Zielrechner zu erfassen (Windows-Soundeinstellungen, gewähltes Audio-Gerät und ggf. ASIO-/WASAPI-Treiber). Keine Seriennummern oder persönlichen Gerätenamen veröffentlichen. WP00 misst noch keine Echtzeitleistung. Die Zielhardware bleibt ausdrücklich **nicht gemessen**, bis der Koordinator die Baseline erzeugt hat.

Fixture-Wahrheit steht in den JSON-Dateien neben den WAV-Dateien. Die Dateien bleiben im ignorierten lokalen Ergebnisordner. Falls ein anderer Ausgabeordner genutzt wird, außerhalb des Repositorys wählen. Lokale Testtracks gemäß `testdaten.md` auswählen und prüfen.
