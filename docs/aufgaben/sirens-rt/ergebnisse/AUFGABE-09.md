# AUFGABE-09 – DSP Rack (WP09)

## Umsetzung

CPU-Referenz in ES-Modulen ohne Fremdabhängigkeiten: FFT/STFT mit Overlap-Add, spektrale Maske, Freeze und Pitch, granularer Cloud-Pfad und WSOLA-Stretch für endliche Clips, uniform partitionierte FFT-Faltung mit zwei generierten IRs und Morphing. Gemeinsame Stereo-Frame-Schnittstelle, begrenzte Parameter, lineare Rampen, Wet/Dry, Bypass, Presets und Profile. Rack-Latenz fast/standard/detail: 896/1664/3200 Frames (deklarierte Summen, keine Geräte-Messwerte). RackPath kompensiert zusätzliche Pfadlatenz. Audio-Core-Einbau als Hook WP09, keine eigenen Änderungen an WP04-Dateien. Limiter bleibt die letzte Stufe im Core; Rack begrenzt Wet-Spitzen defensiv. Kein GPU-Code.

Depends-on: KETTE-11 (integriert) und KETTE-22 (zuletzt nachgezogen: 51fdeb3040d86d411650087e93e5ed82dc63bee8), integration/sirens-rt (4af7c1dae487436e28cd170175b0078f3a29da34). Keine fremden Projekte, Code- oder Gewichts-Pins, keine zusätzlichen Lizenzen; keine Modelle oder Gewichte. Python 3.11 / Node 22 gemäß CI, Browser mit AudioWorklet; CPU-only, keine RTX erforderlich.

## Abnahmebelege

| Punkt | Beleg / Stand |
|---|---|
| 1 | tests/realtime/dsp_spectral.test.mjs: FFT-Rundlauf, Stereo-Impuls und Latenz auf Sample; dsp_granular_convolution.test.mjs: Stereo-Impuls, Cloud und Faltung; dsp_rack.test.mjs: Wet=0 und Bypass bitgleich nach deklarierter Latenz, Morph-Rampe, Glättung, Pfadausrichtung, Mask/Freeze endlich. Bypass-Wechsel mit 256 Frames Rampe (Bitgleichheit nach Rampe). |
| 2 | Oktave: 375 Hz → 750 Hz, Toleranz 30 Hz; Stretch: Faktor 2, 400 Hz ±30 Hz über den stationären Abschnitt, exakt doppelte Framezahl; IR: Impulsantwort sampleweise ±1e-6, Stereo. |
| 3 | Begrenzung endlicher Parameter, Ablehnung von NaN/Inf, falschem Bypass-Typ, unbekanntem Preset/Parameter und fehlerhaftem Stereo-PCM; IR-Größe und Werte geprüft. |
| 4 | **Nicht gemessen**: G3-Zusatzlatenz und Control-to-audio am Zielrechner, Dropouts, Hörtest. Node- und Browser-Messskripte, synthetische Inputs, mehrere Stems und Profile, Ergebnis-Konverter und Test in benchmarks/dsp/ bzw. tests/realtime/test_dsp_report.py. Browser-Ausgabezeitstempel sind eine Schätzung, physischer Loopback bleibt separat. |
| 5 | Maßgeblicher Befehl: python -m unittest discover -s tests -v. PR #15; CI-Läufe 45452844913 (Kerne), 45452978488 (Rack), 45453076484 (nach WP04-Merge), 45453226983 (Messskripte), 45453433320 (Bypass-Rampe, Steuerantwort und Ergebnis) jeweils success. Neuere Pushes separat über PR-Checks prüfen. Lokaler Checkout nicht möglich: DNS für github.com nicht auflösbar; keine lokale Gesamtprüfung. board.md nicht selbst geändert (KETTEN.md-Regel). |

Nachstellen: `node --test tests/realtime/dsp_*.test.mjs` (Shell mit Glob-Unterstützung) bzw. `python -m unittest discover -s tests -v`; Messaufrufe siehe benchmarks/dsp/README.md. `python -m benchmarks.dsp.report <input.json> <result.json>` validiert das gemeinsame Format. Messwerte werden erst am Zielrechner erzeugt.

## Anpassungsbedarf / Grenzen / Risiken

- WP31 muss Hook in den Core einbauen und DSP-Capability erst nach G3 freigeben. Kein separater AudioContext im Produkt; Benchmark verwendet einen eigenen, isolierten Context. Vor Freigabe tatsächliche Browser-Deadlines und Geräteausgabe prüfen.
- Stretch ist eine Clip-Funktion außerhalb des Rendercallbacks (ein kontinuierlicher Faktor ungleich 1 kann nicht dauerhaft in einen gleich langen Echtzeitpfad geschrieben werden). Cloud ist streaming-fähiger Referenzalgorithmus, jedoch nicht als Echtzeit freigegeben. Stationärer Sinus ist keine Qualitätsaussage für Transienten oder komplexe Musik.
- Spektrale Bin-Zuordnung und Freeze können Artefakte verursachen; Schaltwechsel werden über OLA verteilt, nicht als samplegenauer Klickfreiheitsnachweis für alle Musiksignale belegt. IR/FFT-/Kornprofile nur bei gestopptem Neuaufbau. Gemessene Zusatzlatenz des neutralen Impulses ist nicht gleich der variablen Cloud-Leseposition.
- G3: fast bei 48 kHz deklarierte 18,67 ms, standard/detail höherlatent; keine Freigabe oder Dropout-Zahl erfunden. CPU-vs-GPU-Vergleich vorbereitet, WP02-Bericht GPU Audio SDK (README-Pin 4cde62009594e0f4f1db712d27be4fea8b0d06c8, CC BY-NC-SA 4.0 laut Bericht) benennt nur einen ungeprüften Kandidaten, Gate nicht_gemessen, sm_120 nicht belegt. Kein belastbarer Vorteil oder Eignungsnachweis, daher kein GPU-Backend oder GPU-ADR. Keine Fremdkomponenten übernommen.
- Bypass ist nach Einregelung bitgleich zum verzögerten Dry-Pfad; kein harter Wechsel bei laufender Wiedergabe. Core-Limiter kann bei Pegeln oberhalb seiner Grenze bewusst abweichen.

## Rückbau

Hook nicht einbauen bzw. dspEnabled=false, Rack-Module und eigene Tests/Messskripte entfallen. Kein Eingriff in Musikdateien, bestehende HTTP-Routen oder Modellumgebungen.
