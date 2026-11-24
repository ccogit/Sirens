# Messwerkzeuge

Alle Module verwenden ausschließlich Python 3.11-Standardbibliothek. Die Befehle im Repository-Wurzelverzeichnis ausführen. Kein Modell, keine Netzverbindung und keine GPU für die Tests erforderlich.

```sh
python -m unittest discover -s tests -v
python -m benchmarks.baseline --out benchmarks/results/local/baseline.json
python -m benchmarks.fixtures --out benchmarks/results/local/fixtures --rate 48000 --duration 4 --channels 2
python -m benchmarks.manifest benchmarks/tracks.local.json --fill-hashes
python -m benchmarks.manifest benchmarks/tracks.local.json
python -m benchmarks.result benchmarks/results/local/ergebnis.json --markdown benchmarks/results/local/ergebnis.md
```

## Signale

`benchmarks.fixtures.generate(signal, rate=48000, duration=4.0, channels=1)` liefert ein `Fixture` mit `samples` (Liste interleaved Float-Abtastwerte in [-1,1]) und `truth` (Metadaten inklusive Framezahl, Frequenzen, Impuls- bzw. Schlagpositionen). `write_wav(path, fixture)` schreibt 24-bit PCM, signed little endian. Die CLI schreibt pro Signal eine WAV-Datei und eine JSON-Datei mit Wahrheit; Stereo-Sinus ist immer zweikanalig, alle anderen folgen `--channels` (1 oder 2). Dauer in Sekunden; Framezahl und Schläge werden auf den nächsten Frame gerundet. Klicks sind einzelne Samples; jeder vierte Schlag ist betont. Gleiche Parameter in derselben Laufzeitumgebung ergeben gleiche Bytes; plattformübergreifende Bitidentität der Sinus-Rundung wird nicht vorausgesetzt.

## Messformat

`result.schema.json` beschreibt das Format. `result.write(path, data)` prüft vor dem Schreiben, `result.read(path)` prüft beim Lesen, `result.markdown(data)` erzeugt einen Bericht. `rechner` ist das Objekt aus `baseline.collect()`; Zeitpunkt im ISO-8601-Format mit Zeitzone. `messwerte.warm` und `messwerte.kalt` enthalten jeweils `p50_ms`, `p95_ms`, `p99_ms` (Millisekunden), `peak_vram_mib` (MiB), `rtf` (Rechenzeit/Audiodauer), `underruns` (Anzahl). Nicht gemessene Werte sind `null`, niemals geschätzte Werte. Definition der Stichprobe und Messmethode in `notizen` festhalten. `gate` ist `green`, `amber`, `red` oder `nicht_gemessen`; `modus` ist `streaming`, `lookahead`, `offline` oder `unbekannt`. Ein gültiges Format ist kein bestandenes Gate.

Beispiel einer leeren Ergebnisdatei erzeugen (nach Erzeugung der Baseline; nur lokale Datei):

```python
import datetime
import json
from pathlib import Path
from benchmarks import result

root = Path('benchmarks/results/local')
result.write(root / 'ergebnis.json', {
    'wp': 'WP00', 'kandidat': 'Baseline', 'gate': 'nicht_gemessen',
    'modus': 'unbekannt', 'zeitpunkt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'rechner': json.loads((root / 'baseline.json').read_text(encoding='utf-8')),
    'messwerte': {phase: dict.fromkeys(result.METRICS) for phase in ('warm', 'kalt')},
    'notizen': ['Noch keine Messung'], 'befehl': 'python -m benchmarks.baseline --out benchmarks/results/local/baseline.json',
})
```

Keine erzeugten WAVs, lokalen Trackpfade oder personenbezogenen Daten committen. Vor Veröffentlichung von Messergebnissen alle Felder auf sensible Informationen prüfen. Siehe `docs/realtime/testdaten.md` und `docs/realtime/baseline.md`.
