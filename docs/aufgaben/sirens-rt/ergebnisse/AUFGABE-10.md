# AUFGABE-10 – BeatGrid, Tonart, MIDI (WP10)

KETTE-24, [PR #13](https://github.com/ccogit/Sirens/pull/13) gegen
`integration/sirens-rt`. Depends-on KETTE-11 (#8, inzwischen gemergt).
Erster eigener Commit dfcf4acd; Draft unmittelbar eröffnet. Voraussetzung
zunächst per Fast-Forward (05592a62), danach aktualisiert (7f69f454) und
Integration nach deren Merge (ae58b386) übernommen; kein Force-Push.

## Umsetzung

- `music_analysis.py`: vorhandene Onset-Merkmale und Tempo-Hypothese aus
  beat.py, Regression der Impulspositionen gegen Langzeitdrift, Akzentanalyse
  für 4/4, bestehende Phrasenanalyse aus dramaturgie.py. Frame-Anker im
  eingefrorenen BeatGrid-v1-Schema. Unzureichende Evidenz: kein Raster
  (`grid=None`), niedrige Konfidenz. Chroma per Goertzel, konservative
  Dur/Moll-Schätzung; sichere numerische Basic-Pitch-Noten in Quellframes.
- `CorrectionStore`: Half/Double-Time, Taktverschiebung, Phase, Tap-Tempo;
  atomare JSON-Datei pro SHA-256 der Quelle, Rate gespeichert/umgerechnet.
  Kein Schreiben in Audioquelle.
- `beat_grid.js`: reine Source-Frame/Schlag/Takt-Funktionen, nächste
  Taktgrenze strikt nach Eingabe, Quantisierung, stetige stückweise konstante
  Tempo-Karte. Unsicheres Raster blockiert automatische Quantisierung.
- GET-Hook und Integration der Korrekturen/Noten für WP31 (keine Änderung
  gemeinsamer Dateien). Beat-This-Live-Manifest und Stub bleiben gesperrt.
- Lokale Referenzmessung unter benchmarks/beatgrid; keine Trackdaten im Repo.

## Abnahme und Prüfbelege

| Nr. | Beleg | Stand |
|---|---|---|
| 1 | test_music_analysis.MusicAnalysis.test_click_truth: WP00-Klickspuren 120/140/150 BPM, 24 s, BPM-Toleranz 0,2; alle Beat-/Downbeat-Positionen ab 2 s innerhalb 960 Frames bei 48 kHz (20 ms) | erster Test-CI-Lauf bestanden |
| 2 | test_corrections, test_silence_noise, test_chroma, test_midi_adapter; Persistenz nach Neuinstanziierung, Rate, Hash-Isolation, fehlerhafte Taps, deterministisches Rauschen/Stille, C-Dur | erster Test-CI-Lauf bestanden |
| 3 | beat_grid.test.mjs über test_web.Seite.test_logik_mit_node: konstante/variable Karte, Rundlauf, Quantisierung, Taktwechsel, invalid/unsicher; zusätzlich Quellgrenzen | erster Lauf bestanden, ergänzte Grenztests im abschließenden CI-Lauf |
| 4 | fünf unveränderte test_beat-Tests | erster Lauf bestanden |
| 5 | benchmarks.beatgrid.measure, test_reference_report (Mock), siehe Aufruf unten | reale Tracks nicht gemessen |
| 6 | python -m unittest discover -s tests -v | maßgeblicher abschließender Status im PR; board.md gemäß KETTEN.md nicht geändert |

Erster CI-Lauf [45452789735](https://github.com/ccogit/Sirens/actions/runs/45452789735)
auf b2543552: 106 Tests, 1 Fehler, 4 Skips. Alle damaligen WP10-Tests und
test_beat.py grün; Fehler im damaligen KETTE-11-Importinventar:
`AssertionError: 'basic_pitch' not found ... sirens/stem_transcribe.py`.
KETTE-11 hat den Alt-CLI-Fall korrigiert und den Schema-Validator nach
`sirens.realtime.schemas` verschoben; beides durch Merge übernommen, eigene
Imports angepasst. Nachfolgende Läufe wurden durch neue Pushes abgelöst.
Abschließender Lauf: [PR Checks](https://github.com/ccogit/Sirens/pull/13/checks).
Lokal vollständiger Checkout nicht möglich: `Could not resolve host: github.com`.
Alle Änderungen über GitHub gepusht; keine lokale Vollsuite behauptet.

## Nachstellen

    python -m unittest discover -s tests -v
    node --test tests/realtime/beat_grid.test.mjs
    python -m benchmarks.manifest benchmarks/tracks.local.json
    python -m benchmarks.beatgrid.measure benchmarks/tracks.local.json --out benchmarks/results/local/wp10.json
    python -m benchmarks.result benchmarks/results/local/wp10.json

Reale Tracks, ffmpeg-Dekodierung auf Zielhardware, Modell/Browser mit Tonausgabe:
**nicht gemessen**. Referenzen: manuell annotierte beat_seconds/downbeat_seconds
im lokalen Manifest. Format: benchmarks/result.py, zusätzliche anonymisierte
tracks-Liste; Median/p95/Maximum der Positionsfehler, BPM-Fehler, Konfidenz
und Laufzeit. Keine automatische Gate-Freigabe.

## Entscheidungen, Risiken und Anpassungsbedarf

- Python 3.11 Standardbibliothek, ES-Module (Node 22); ffmpeg nur bestehende
  externe Dekodierung, konkrete lokale Version/Lizenz gemäß baseline.collect
  auf Zielrechner ermitteln. Keine neue Fremdbibliothek oder Modellgewichte.
  Bestehender Basic-Pitch-Worker bleibt unberührt, keine neue Version gepinnt.
- Beat This! Live nach WP02-Bericht (Branch KETTE-12): README-Revision
  353065f154b50442b1bddfa5c020a40f0e64c564, MIT Code und veröffentlichte
  Gewichte laut Bericht; konkrete Gewichts-Hashes/Abhängigkeitspins offen.
  Kein CUDA-/VRAM-Beleg; gesperrt, keine Schein-Capability. Manifest im
  eigenen Benchmark-Verzeichnis gemäß Dateizuständigkeit.
- CPU-Fit bewusst konservativ: 65–185 BPM für automatische Erkennung,
  konstantes Tempo, 4/4, erste 360 s (Chroma erste 30 s). Schwache Akzente,
  komplexe Synkopen, wechselndes Tempo, uneindeutige Tonarten oder leise
  Quellen können zu unsicherem Ergebnis führen. Tempo-Karten werden im
  Frontend verarbeitet, nicht automatisch geschätzt; manuelle Korrekturen
  nur für konstantes Raster. Konfidenz 1 bei expliziter Benutzervorgabe
  bedeutet keine gemessene Modellqualität. Tonart-Heuristik kein Ersatz
  für manuelle Referenz, MIDI nur Notenadapter, kein Modellstart.
- Schema verlangt BPM >=1; unsicher intern ohne Grid, GET-Route 503. Route,
  separate Metadaten und manuelle Befehle sind Hook/Integrationsbedarf,
  kein eingefrorenes Schema geändert. Quellpositionen von Output-Frames
  unterscheiden. Keine UI- oder Bestandsroutenänderung in WP10.
- Tests ohne Musik, GPU oder Downloads. Board/Register nicht eigenständig
  geändert (nur von Koordinator/Voraussetzung stammende Merge-Inhalte
  übernommen). Keine Beobachtung außerhalb des Umfangs außer obigem
  inzwischen upstream adressiertem CI-Fehler.

## Rückbau

WP10-eigene Dateien und Tests revertieren; keinen Dependency-Merge rückgängig
machen. Hook nicht einbauen bzw. Registrierung entfernen. Nur die optionalen
BeatGrid-Korrekturdateien im eigenen RT-Cache entfernen, Originalaudio belassen.
