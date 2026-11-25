# AUFGABE-18 – Preview-Plan aus Sprachdauern

**Status:** Implementierung und Offline-Abnahmetests im Branch, bereit für Review; Testausführung und reale Patchbindung am Zielrechner offen. Kein Audio erzeugt oder gemessen.

## Umsetzung und Abnahme

| Anforderung | Beleg im Code / Test |
|---|---|
| Preview 30–60 s, ganze Cues statt Textschnitt | `arrangement.clear_head_plan` mit `preview=True` bzw. Ziel 30–60 s, `_preview_specs` wählt die längste passende Präfixfolge; mindestens ein Takt Intro/Outro/Interlude je Übergang. `validate_arrangement` prüft den vollständigen Wortlaut der ausgewählten Cues auch beim externen Aufruf mit Originalbrief. Test `test_measured_cues_fit_whole_bars_in_all_variants`, `test_preview_rejects_cut_text_and_invalid_durations`. |
| Gemessene 4,8 / 6,3 / 4,9 / 4,8 s | Vier Sekundenwerte in Cue-Reihenfolge, aufgerundete Eventticks plus Sechzehntel-Startoffset und mindestens 0,5 s Pause; Abschnitt auf ganze Takte aufgerundet. Test prüft Cue-IDs, Texte, Dauer, Abschnittsgrenzen und Pausen bei 30, 45, 60 s für alle Varianten. Rechnerisch bei 126 BPM: Sprachabschnitte 3/4/3/3 Takte; 30-s-Ziel 15 Takte + 2 s Tail (30,57 s, drei Cues), 45-s-Ziel 23 Takte + 2 s (45,81 s, vier Cues), 60-s-Ziel 30 Takte + 2 s (59,14 s, vier Cues). Keine Laufzeitmessung. |
| Drei bewusst verschiedene Varianten | Bestehende K02-Muster für Bass und Hook, Preview-Swing 12/24/0 Ticks, separate semantische Bass-/Hook-Patches; Kick/Sub weiterhin synchron. `test_distinct_grooves_swing_and_semantic_patches`; tatsächliche Preset-Bindungen und Hörurteil offen. |
| Vollsong unverändert | Bestehende Dauer-/Abschnittslogik, Patterns, Patchnamen, Seed und 12-Tick-Swing außerhalb Preview unverändert. `test_full_song_retains_original_structure_and_patches` ergänzt vorhandene K02-Regressionstests. |
| Validierung, Reproduzierbarkeit, Eingabe | K00-Validatoren unverändert genutzt; deterministische Pläne, ungültige Dauern und unmögliche Cue-Budgets abgewiesen. `test_explicit_preview_and_estimated_duration_fallback`, weitere Tests oben. |

## Reuse

| Funktion | Quelle | Geprüfte Schnittstelle | Entscheidung | Lücke / Test |
|---|---|---|---|---|
| Songplan und musikalische Varianten | Sirens K02, Integrationsstand ce1a74052e33fbbe88db02e0cd65028ca994f8aa; AMM 26c5ce2fe9641ed958414f78d58643527bc3032f laut REUSE-AMM.md | Bestehendes `clear_head_plan`, `_VARIANTS`, `_HOOKS`, AMM-Adapter im Modul gelesen | ADAPT | Nur Preview-Budget und Variantenparameter ergänzt; keine neue Kompositionsengine. Tests oben. Kein realer AMM-Aufruf. |
| Planvertrag | Sirens K00, gleicher Integrationsstand | `validate_brief`, `validate_plan` gelesen | REUSE | Validierung in den Abnahmetests, nicht ausgeführt. |
| Instrumente und Assets | Sirens K03/K04, SecondRoom 8cd35755376b11ef753cb323576a824a366a2f1e laut REUSE-AMM.md | `instruments._patch`, Asset-Dauerprüfung gelesen | REUSE | Lokale Patchmanifest-Bindung, tatsächliche TTS-Dauer und Render nicht geprüft. Kein neuer Host/Worker/Live-Writer. |

## Dateien und Prüfstatus

- `sirens/production/arrangement.py` (Commits e85cd012 und 6c46fa9)
- `tests/production/test_arrangement_preview.py` (cc0919b)
- `sirens/production/templates/ARRANGEMENT.md` (b03876a)
- dieser Bericht

GitHub-Dateizugriff und Push über Connector erfolgreich, Basis und Dateiumfang geprüft. Kein vollständiger lokaler Checkout: `git ls-remote` scheiterte mit Exit 128, `Could not resolve host: github.com`. Daher **keine Python-Tests lokal ausgeführt**, weder Linux noch Windows als bestanden ausweisen. GitHub Actions laut Auftrag deaktiviert; keine CI-Aussage. Keine Netzwerk-, GPU-, Plugin- oder Live-Abhängigkeit der neuen Tests.

Koordinator aus Checkout (Windows):

```powershell
py -3.11 -m unittest discover -s tests/production -p "test_arrangement*.py" -v
py -3.11 -m unittest discover -s tests -v
```

Linux entsprechend `python3.11`. Erwartet: alle vorhandenen K02-Tests und neuen Preview-Tests OK. Zur realen Planerzeugung mit lokalem Brief:

```powershell
py -3.11 -m sirens.production.arrangement brief.json --preview --variant ratchet --cue-durations 4.8 6.3 4.9 4.8
```

Erwartet: JSON-Plan, 960 PPQ, 4/4, ganze Takte, 30–60 s inkl. Tail, ausschließlich vollständige Cues. Ausgabe als UTF-8-Plan speichern und über bestehenden Renderpfad mit `--plan` verwenden.

## Entscheidungen, Abweichungen, Risiken

- Automatische Preview-Auswahl bei 30–60 s, damit der vorhandene Aufrufer ohne Änderung anderer Owner-Dateien funktioniert. Explizites Preview ohne Ziel nutzt 45 s. Ohne Messwerte bleibt eine Schätzung als Rückfall; keine tatsächliche Dauer behauptet. Messwerte als explizites Argument/CLI-Option, keine automatische TTS-Messung im Planer.
- Präfixauswahl ist deterministisch und bewahrt Reihenfolge; wenn der erste Cue nicht passt, wird ein Fehler gemeldet, statt beliebige spätere Cues auszuwählen. Ein anderer Cue-Schnitt bleibt Agentenentscheidung.
- Alternate semantische Patch-IDs sind neu und benötigen lokale Bindungen an verschiedene vorhandene lizenzierte Presets: `gear_bass_counterweight`, `bell_buoy_counterweight`, `gear_bass_undertow`, `bell_buoy_undertow`. Keine Anpassung an K03-Dateien/echte Konfiguration vorgenommen. Ratchet nutzt die bisherigen IDs. Ohne Bindung schlägt das Rendern der alternativen Varianten absichtlich fehl; echte Kompatibilität und Hörqualität nicht gemessen.
- Koordinator prüft insbesondere tatsächliche TTS-Länge bei neu erzeugten Assets und vollständige Windows-Suite; bei Überlänge neu planen, nie abschneiden. Keine Lizenz- oder Qualitätsbehauptung über lokale Assets. Kein Register geändert, kein Merge nach main oder Integration durch Bearbeiter.
