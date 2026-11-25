# AUFGABE-17 – Mix-Rollen: Bass ist nicht Sub

**Stand:** Implementiert; isolierte Linux-FFmpeg-Probe erfolgreich. Vollständige Repo- und Windows-Abnahme durch Koordinator offen. [PR #70](https://github.com/ccogit/Sirens/pull/70), Ziel `integration/sirens-production`. Ausgangscommit `ce1a74052e33fbbe88db02e0cd65028ca994f8aa`.

## Umsetzung

- `sirens/production/mixing.py`: Nur Rolle `sub` oder ausdrückliche Kennung in Track-ID/Plan-Patch (durch Punkt, Unterstrich oder Bindestrich getrennte Tokens `sub`/`subbass`, optional Ziffern) führt in den Sub-Pfad. `gears`/`gear_bass` bleibt Bass, `mono_sub` bleibt Sub; `subtle_bass` ist kein Sub.
- Bass erhält eigenen Hochpass (45 Hz), EQ (250 Hz, −2 dB, Q=1) und Kompressor (Threshold linear .125, Ratio 2, Attack 20 ms, Release 100 ms, Makeup 1); Gain −9 dB wie bei anderen Nicht-Sub-Spuren. EQ und Gain bleiben über die vorhandenen Track-Overrides einstellbar. Diese konservativen Werte sind Implementierungsentscheidungen, keine durch Hörtest freigegebenen Presets.
- Expliziter boolescher Override `plan.mix.tracks[track_id].sidechain`: Bass standardmäßig aus, Sub standardmäßig an; explizites True/False möglich. Ohne Kick kein Ducking. Bass-Pan bzw. obere Stereoanteile bleiben erhalten, auch bei aktiviertem Sidechain. Sub/Kick bleiben im bisherigen Mono-Pfad. Die globale Mono-Summe unter 120 Hz bleibt unverändert.
- `workers/production_mix/ffmpeg_mix.py`: Bestehende Filter und K09-Frame-Angleichung (1024 Samples inkl. letzter Block) für Kick und tatsächlich geduckte Spuren beibehalten. Keine Sidechain-Parameteränderung, keine neue DSP-Engine, Dry-Pfad unverändert. Kompressorparameter im Worker-Bericht ergänzt.
- Tests: `test_mixing_roles.py` prüft Rollen, Kennungen, Graph, explizite Sidechain, Mono, Dry und Typvalidierung. `test_mixing.py` ergänzt WAV-Ausgangstest (Bass stereo, geduckter Bass stereo, Sub mono; Ducking verändert PCM) und erhöht K09-Wiederholungen von fünf auf zehn bei unveränderter ursprünglicher Messfixture.

## Abnahme

| Punkt | Beleg / Stand |
|---|---|
| Bass ≠ Sub | Rollen-/Graph-Tests hinzugefügt; isolierte Probe mit gear_bass und sidechain false/true: beide Ausgaben stereo, unterschiedliche PCM-Daten bei Ducking. |
| Sub bleibt mono | Rollen-/Graph-Test und WAV-Regression hinzugefügt. Isolierte Probe mit mono_sub: L/R-PCM24 sampleweise identisch trotz Pan-Override. |
| Reproduzierbarkeit aus Aufgabe 09 (10x) | K09-Test auf zehn Wiederholungen erweitert. Isoliert je 10/10 identische Float-WAV-Hashes für Bass ohne/mit Sidechain und Sub, sowohl Mono- als auch Stereo-Quelle der Testspur (60 Renderings insgesamt). |
| Bestehende Mix-Tests grün | Vollständige unittest-Ausführung nicht möglich; Koordinator muss sie auf Windows ausführen. Keine grüne CI behauptet. |

## Lokale Prüfbelege

Linux, Python 3.13.5, FFmpeg 7.1.5-0+deb13u1. In temporärer, aus den gelesenen Funktionen nachgebildeter Probe wurden künstliche PCM24-Sinus-Stems (48 kHz, 48000 Frames, Kick mit 100-ms-Signal, Sub bei 55 Hz, Bass bei 440 Hz) durch den geänderten Filtergraph gerendert. Der PCM24-Decode hatte jeweils 48000 Stereo-Frames; Bass blieb stereo, Sub war dual-mono, explizites Ducking änderte PCM. Je Variante genau ein Float-WAV-SHA-256 in zehn Wiederholungen, einmal mit Mono- und einmal mit Stereo-Quelle der Bassspur. Beispiele Stereo-Quellen:

| Variante | SHA-256 |
|---|---|
| Bass ohne Sidechain | f28198cfe69b2b33ea99d519cabfae351d3c1c1d1e6c0c8aa409e2ac029db081 |
| Bass mit Sidechain | f891c77ecf706c32a30be41a0f950b7ef6f1343cf3d563eb13972132751b1a1e |
| Sub | 87dc7764570c4bd39f320ec896786b1e602540e297385c7e287e8d6fa3dfe |

Die Probe ist keine vollständige Repo-Testausführung und kein Nachweis der K09-End-to-End-Master-Hashes auf dem Zielrechner.

## Reuse / Abweichungen / Risiken

REUSE-AMM.md beachtet: vorhandener K05-Adapter zu SecondRoom und AMM mastering_engine sowie bestehende FFmpeg-Filter wiederverwendet; kein neuer Live- oder AMM-Pfad. Kein Zugriff auf lokale Audio-/Modellbibliotheken, keine Fremddaten oder Audiodateien in Git. Keine Änderung an Vertrag, Register, Arrangement oder anderen Ketten.

Git-Checkout lokal blockiert: `git ls-remote https://github.com/ccogit/Sirens.git refs/heads/integration/sirens-production` → `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. Repository-Zugriff, Commits und PR über GitHub-Schnittstelle. GitHub Actions abgeschaltet. Vollständige Tests, Python 3.11, Windows und Hörtest sind nicht gemessen. Neue Bass-EQ-/Kompressorwerte können den Klang und Headroom des realen Mixes ändern (beabsichtigte Rollenänderung, nicht als Hörverbesserung behauptet). Andere FFmpeg-Versionen und AMM-Mode-C-Reproduzierbarkeit nicht gemessen. Keine bekannte Implementierungsblockade.

## Zielrechner-Abnahme

In PowerShell auf dem PR-Branch, mit FFmpeg im PATH:

```powershell
ffmpeg -version
py -3.11 -m unittest tests.production.test_mixing_roles tests.production.test_mixing -v
if ($LASTEXITCODE -ne 0) { throw "AUFGABE-17 Mix-Tests fehlgeschlagen" }
py -3.11 -m unittest discover -s tests -v
```

Erwartung: keine übersprungenen FFmpeg-Tests, erfolgreiche Rollen-/WAV-Regression, zehn K09-Wiederholungen mit identischen Hashes und unveränderten Toleranzen. Bei Fehler FFmpeg-Version, Testname und Fehlerausgabe sichern. Der Koordinator prüft und merged; kein eigener Merge.
