# Aufgabe 27: Generative Performance Pads Teil 2 – Verdrahtung (Rest von WP12)

Gemeinsame Bedingungen, Begriffe und Regeln: `docs/aufgaben/sirens-rt/README.md`. Setzt Aufgabe 12
(Teilstand, gemergt) voraus. Umfang und Abnahme von Aufgabe 12 (`AUFGABE-12-PERFORMANCE-PADS.md`) gelten weiter.

## Ziel

Ein Pad im RTX Neural Lab erzeugt mit Stable Audio 3 echten Klang und setzt ihn taktgenau ein; ohne
installiertes Modell bleibt der Pad-Knopf abgeschaltet und benannt.

## Ausgangslage

- Ergebnis und Übergabe von Aufgabe 12: `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-12.md` (offen:
  Supervisor-/Registry-Einbau, Browser-Audio, Chunk-Übertragung, 20 echte Einsätze).
- Vorhanden: `workers/stable_audio/` (Manifest, Adapter, Worker, `install.ps1`, Lockfile),
  `web/js/realtime/pad_scheduler.js`, Hook `docs/realtime/hooks/WP12.md`, `benchmarks/pads/`.
- Messung: `benchmarks/results/g1/stable-audio-3.md` (lookahead grün, warm 0,35–0,43 s je Clip, Kaltstart
  9–21 s, ~1,7 GiB). Erzeugte Clips sind ganze Dateien: Übertragung über den Dateijob nach
  `docs/realtime/adr/0006-dateijob.md` (setzt KETTE-28 parallel um; gegen die ADR entwickeln und nach deren Merge
  `origin/integration/sirens-rt` hineinmergen), Ergebnis als Asset, Wiedergabe im Audio-Kern.

## Umfang

1. Worker über Supervisor und Registry starten (Lease, Vorladen und Aufwärmen bei Öffnen der Pads nach
   Nutzeraktion, Entladen beim Verlassen).
2. Pad-Job: Prompt aus Pad-Typ und Kontext (Tempo und Tonart aus dem BeatGrid), Länge in Takten, Seed; Ergebnis
   als Asset; der Scheduler setzt es mit Crossfade an der nächsten passenden Taktgrenze ein.
3. Oberfläche: Pad-Leiste in der Lab Shell nach Hook WP12 (Vorhören, Einsatz, Verwerfen, Zustand).
4. `benchmarks/pads/`: 20 Einsätze messen (der Koordinator führt aus), Quote rechtzeitig.

## Nicht im Umfang

- Dateien anderer laufender Ketten (Tabelle „Dateien je Kette“), Katalog-API.

## Abnahme

1. Tests mit nachgebautem Worker: Vorladen nur nach Nutzeraktion, Job bis Asset, Einsatz auf das Sample an der
   Taktgrenze, verspäteter Job wird verschoben oder verworfen, Entladen beim Verlassen.
2. Ohne installiertes Modell: Pads abgeschaltet und benannt.
3. CI des PR grün.
