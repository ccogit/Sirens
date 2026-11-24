# AUFGABE-04 – Audio Core und Data Plane (WP04)

Branch extern/KETTE-22, [PR #11](https://github.com/ccogit/Sirens/pull/11), Basis integration/sirens-rt. Vorgezogen: KETTE-11 zunächst per Fast-forward 05592a62, vor Abschluss 7f69f454 per Merge ce4ca31d übernommen; danach Integrationsstand einschließlich gemergter Voraussetzung und WP02 mit Merge 39825832. Kein eigener Eingriff in Register oder Board.

## Umsetzung

- Zeitadressierter Stereo-Ring, Master-/Source-Clock, Epoch, begrenzter Transport mit acht Credits und Lookahead, PCM-v1-Codec aus WP01 unverändert, lineares Resampling vor dem Worklet.
- AudioWorklet mit variablen Quanten, gemeinsamer maximaler Pfadlatenz, Gain-/Dry-Wet-Rampen, Bypass, Dry-Rückfall und -1 dBFS Peak-Grenze. Context-/Ausgabesperre, Start/Seek/Loop, Stem-Adapter ohne Bestandsänderung.
- Eigener Python-Sidecar: Loopback, genaue Host/Origin-Prüfung, einmalige kurzlebige Tokens, gebundene Streams, Größen-, Raten- und Queue-Grenzen, RFC6455-Binärpfad und privates Producer-IPC. Einbau/Abbau für WP03/WP06 in docs/realtime/hooks/WP04.md.
- Browser-Soak mit synthetischem Gain-Mock und WP00-Ergebnisformat; keine Musikdateien, keine Modelle, keine fremden Abhängigkeiten.

## Abnahme

| Nr. | Beleg | Stand |
|---|---|---|
| 1 | tests/realtime/audio_core.test.mjs: Ring voll/leer/Umlauf/Überlauf, Clock/Loop, Transport-Credits/alte Epoch, Impuls und zwei Spuren, Jitter und Dry-Rückfall, variable Worklet-Quanten | CI grün auf Code-Stand 949c36f5, Run 45453109162 |
| 2 | gleicher Node-Test: NaN/Inf, Dry unverändert bei Unity-Gain/Latenz 0 und unter Limitergrenze, Peak maximal -1 dBFS | CI grün auf 949c36f5 |
| 3 | tests/realtime/test_audio_sidecar.py: echte Loopback-Verbindung, RFC6455-Handshake und binärer Strom, Token/Origin, ungültiger PCM-Kopf/Version/Größe, Backpressure, unerlaubter Upload, Prozessende | fünf Sidecar-Tests bereits in Run 45452827634 einzeln bestanden; Gesamt-CI nach Merge der Vertragskorrektur grün |
| 4 | Node-Test Resampling 44100↔48000: Signallänge eine Sekunde, 440-Hz-Nulldurchgänge | CI grün auf 949c36f5 |
| 5 | benchmarks/audio_core/README.md und serve.py/measure.js/format_result.py; tests/realtime/test_audio_benchmark.py validiert Ergebnisformat | Format-Test in Run 45453279298 grün; 30 Minuten und Geräte-Latenz **nicht gemessen** |
| 6 | python -m unittest discover -s tests -v (Python 3.11, Node 22, CI) | [45453279298](https://github.com/ccogit/Sirens/actions/runs/45453279298) erfolgreich auf 8b58186a, erneute CI nach Integrationsmerge/Ergebnisdatei erforderlich; Board nur Koordinator |

Frühe CI war rot durch den unveränderten WP01-Importinventartest (basic_pitch in sirens/stem_transcribe.py, Run 45452827634); KETTE-11 hat die Abgrenzung korrigiert. Nach Übernahme war CI grün (45452949695). Lokaler vollständiger Checkout und echte Browser-/Gerätemessung nicht durchgeführt.

## Nachstellen / Hardware

- `python -m unittest discover -s tests -v`
- `node --test tests/realtime/audio_core.test.mjs`
- `python -m benchmarks.audio_core.serve --port 8766`, dann http://127.0.0.1:8766/benchmarks/audio_core/index.html, Messung starten. Ergebnis: `python -m benchmarks.audio_core.format_result wp04-rohmessung.json --out benchmarks/results/wp04-browser.json`; validate mit `python -m benchmarks.result benchmarks/results/wp04-browser.json`. Anleitung zur getrennten Geräte-Latenzmessung im Benchmark-README.
- Kein zusätzliches Fremdprojekt, keine Commit-Pins/Lizenzen fremder Gewichte, keine GPU erforderlich für CPU-Tests. Web Audio/AudioWorklet im Zielbrowser und Audio-Hardware für Messung nötig. Kein G2-Nachweis.

## Entscheidungen / Risiken / Anpassungsbedarf

- PCM v1 start_frame bleibt Master-Ausgabeframe. Producer muss Wet auf gemeinsame maximale Pfadlatenz adressieren und native Modellrate vorher umrechnen. Lineares Block-Resampling ist ein Referenzpfad, kein hochwertiger bandbegrenzter Resampler; Blockrandqualität auf Hardware prüfen.
- Bei Loop-Wechsel erfährt der Mainthread die neue Epoch erst durch Statuspoll; Wet kann vorübergehend auf Dry fallen. Die Latenzkompensation benötigt entsprechend vorberechnete Wet-Blöcke. Bei Seek werden alte Blöcke sofort verworfen; ein neuer Start mit Vorlauf kann eine Lücke erzeugen. Dry-Bitgleichheit gilt nach Latenzausgleich bei Gain 1 und unterhalb der Schutzgrenze.
- Browser-Soak isoliert den Audio-Pfad (synthetischer Mock im Browser); E2E über Supervisor/Sidecar mit Mock-Worker, echte Navigation und Hardware-Gate folgen in WP06. Seitlicher Prozessstopp ist automatisiert getestet, echte Worker-Abstürze und Navigation nicht im Browser getestet.
- Beat-Quantisierung für konstante BPM vorhanden; variable Tempo-Map und vollständige samplegenaue zeitgeplante Parameter-/Pause-Befehle sind noch nicht ausgearbeitet. Kein produktiver Echtzeitanspruch. Für WP06 müssen Session-/Epoch-Steuerung, Stream-ID-Mapping, Supervisor-Lifecycle und Feature-Flag-Weiche über den Hook integriert werden.
- Rückbau: RT bleibt standardmäßig aus; keine Bestandsdatei direkt geändert. AudioCore.destroy, IPC revoke/stop, Supervisor wait; bei Bedarf WP04-Dateien/Tests/Hooks als Einheit revertieren, nicht die übernommenen Integrations-Merges.

## Übergabe

Fertig: referenzfähiger Audio-Pfad, Sidecar, CPU-Tests, Messharness und Integrationshook; Code-CI auf 8b58186a grün.
Offen: vollständiger Scheduler (variable Tempo-Map und framegenaue Parameter-/Pause-Befehle), Lifecycle-Negativtests im echten Browser sowie Hardwaremessungen.
Nächster Schritt: finale PR-CI prüfen, Scheduler/Loop-Vorlauf und Browser-Lifecycle gezielt nacharbeiten, anschließend WP06-E2E und Zielrechner-Messung.
Fehlerausgabe: frühe CI: AssertionError: 'basic_pitch' not found … sirens/stem_transcribe.py; durch aktualisierte KETTE-11-Verträge behoben. Keine offene bekannte CPU-Testfehlermeldung auf 8b58186a.
