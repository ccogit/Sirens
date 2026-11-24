# WP10: Referenzmessung (lokal)

Manifest nach WP00 validieren: `python -m benchmarks.manifest benchmarks/tracks.local.json`.
Für jeden Track zusätzlich zwei aufsteigende, manuell annotierte Listen ergänzen:
`beat_seconds` und `downbeat_seconds` (Quellposition in Sekunden, vor 360 s,
nicht vom Algorithmus erzeugen); BPM-Referenz aus dem Manifest. Keine lokalen
Pfade oder Musik committen. Beispielaufruf:

    python -m benchmarks.beatgrid.measure benchmarks/tracks.local.json --out benchmarks/results/local/wp10.json
    python -m benchmarks.result benchmarks/results/local/wp10.json

Ergebnis: gemeinsames Ergebnisformat plus tracks-Liste mit anonymen laufenden
Nummern, Konfidenz, Laufzeit, BPM-Fehler, Anzahl sowie Median/p95/Maximum der
Abweichung zur nächsten Rasterposition. Unsichere Raster bleiben ohne BPM.
Bei Halb-/Doppeltempo muss der BPM-Fehler mitbewertet werden; Abstände allein
belegen keine Erkennungsquote. Keine Warm/Kalt- oder GPU-Messung, keine
automatische Gate-Freigabe. Koordinator bewertet Referenzqualität und Ausfälle.
