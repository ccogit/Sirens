# Lokale Testdaten

Synthetische Fixtures werden ausschließlich zur Laufzeit aus `benchmarks.fixtures` erzeugt; siehe `benchmarks/README.md`. Keine WAV-, Musik- oder Modell-Dateien einchecken. Tests verwenden temporäre Ordner und keine echten Tracks.

Für manuelle Hör- und Modellmessungen eine Kopie von `benchmarks/tracks.example.json` als `benchmarks/tracks.local.json` anlegen. Die Beispielpfade sind Platzhalter. Lokale Dateien außerhalb des Repositorys belassen. Jeder Eintrag in `tracks` hat:

| Feld | Bedeutung |
|---|---|
| `pfad` | Absoluter Pfad oder relativer Pfad zum Manifestordner |
| `sha256` | SHA-256 der Datei, 64 Hexzeichen; `null` nur vor dem Eintragen |
| `genre` | Techno, House, Psytrance, Industrial oder Ambient |
| `lizenz` | Nachweis der lokalen Nutzungserlaubnis, keine personenbezogenen Angaben in veröffentlichten Berichten |
| `bpm` | Optionale positive BPM-Referenz; weglassen oder `null`, falls unbekannt |

```sh
python -m benchmarks.manifest benchmarks/tracks.local.json --fill-hashes
python -m benchmarks.manifest benchmarks/tracks.local.json
```

`--fill-hashes` ergänzt nur fehlende Hashes; ein abweichender vorhandener Hash ist ein Fehler. Die Prüfung liest die Tracks, ändert sie nicht und überprüft keine Lizenzrechte. Diese prüft der Koordinator vor Nutzung. Das lokale Manifest und `benchmarks/results/local/` werden ignoriert. Keine Pfade oder Audiodaten in öffentliche Messergebnisse übernehmen.
