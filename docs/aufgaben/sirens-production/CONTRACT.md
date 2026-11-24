# Vertrag V1 – gemeinsame Schnittstellen

Dies ist eine verbindliche Planvorgabe, noch kein implementierter Vertrag. A0 liefert Validatoren, Mock-Fixtures und CLI; Änderungen nur als kurzer abgestimmter Contract-PR. Kein neues Framework.

Alle JSONs UTF-8, schema_version=1, unbekannte Werte null, IDs stabil, Zahlen endlich. Pfade relativ zu jeweiligem Run oder konfiguriertem, validiertem Referenzroot, niemals freie absolute Pfade aus Agenten-Input. WAV 48 kHz, PCM24, Mono oder Stereo, volle Projektlänge für Stems; feste 4/4-Taktart, Tempo konstant, MIDI 960 PPQ. Takt 0 und Tick 0 = Sample 0. Events positioniert in Ticks, gesprochenes Audio in Ticks plus Duration, Audioschnitt in Samples. Rundung aus absoluter Position, nicht kumuliert. Audio-Assets dürfen beliebig lang sein, nur Stems haben volle Länge. Keine beliebigen Code-/Shell-Felder.

## Brief und Referenzen

brief.json:
```json
{"schema_version":1,"title":"Clear Head, Broken Heart","style":"motorik electro-funk","negative_tags":["sung melody","EDM drop"],"lyrics":"Clear head.\nCracked-open heart.\nA sober view.","bpm":126,"key":null,"target_seconds":181,"seed":101,"reference_ids":[],"vocal_mode":"spoken"}
```
Referenzprofil (K1, references.json) enthält schema_version, tracks:[{id, song_family, relative_path, rating:null|−2..2, raw_ratings:[], favorite:boolean|null, axes:{}, style_text:null, lyrics:null, description:null, bpm_measured:null, bpm_confidence:null, key:null, key_confidence:null, features:{}, source:{}, usage:"analysis_only"}], selected:[ids], holdout:[ids], profile:{music:{},production:{},coverage:{}}. IDs und Dateihashes stabil; private Daten nicht ins Repo. Stil-/Tempoangaben aus Text als eigene Felder. Rohkommentare separat. Keine automatische Übernahme von Audio.

## Plan (K2, plan.json)

```json
{"schema_version":1,"seed":101,"bpm":126,"key":"D minor","meter":[4,4],"ppq":960,"total_bars":8,"tail_seconds":2,"sections":[{"id":"intro","start_bar":0,"bars":8,"intent":"gears and buoy"}],"tracks":[{"id":"kick","role":"drums","backend":"instrument","patch":"tight_kick","events":[{"tick":0,"duration_ticks":240,"note":36,"velocity":115}],"automation":[]},{"id":"voice","role":"spoken","backend":"asset","patch":"spoken_calm","events":[{"tick":3840,"duration_ticks":7680,"asset_id":"cue1"}],"automation":[]}],"asset_requests":[{"id":"cue1","kind":"speech","text":"Clear head.","prompt":"calm close male spoken","seed":101,"duration_seconds":4}],"mix":{"target_lufs":null,"ceiling_dbtp":-1}}
```
Die Beispieldatei zeigt Format, nicht ein vollständiges musikalisches Arrangement. sections decken lückenlos total_bars ab, events liegen im Projekt, duration_ticks>0, MIDI note 0..127, velocity 1..127, automation als [{tick,parameter,value}] mit Backend-Allowlist. Weitere Asset-Arten: texture, foley, loop, fill, sample; speech text unverändert. Patches stabile semantische IDs, keine VST-Pfade aus Plan. Rhythmus-/Instrumentereignisse ohne harte Backend-Bindung; lokales Patch-Manifest mappt IDs auf Instrument/Presets. Bei fehlendem Patch/Asset expliziter Fehler, nur Mock im Test. A0 dokumentiert verbindliche Parameter-/Wertebereiche. voice events können bei längerer Sprachdauer neu geplant werden statt Text abzuschneiden.

## Assets und Stems

assets.json (K4): {"schema_version":1,"assets":[{"id":"cue1","file":"assets/cue1.wav","kind":"speech","sample_rate":48000,"channels":1,"frames":192000,"sha256":"…","source":{"backend":"…","revision":"…","seed":101,"license":"…","use":"…"},"measured":{"bpm":null,"key":null}}]}. Jeder Request bekommt Ergebnis oder expliziten Fehler. Lizenzstatus "unknown" blockiert kommerziellen Export; keine stillen Downloads.

stems.json (K3, kombiniert durch K0 mit K4-Assets): {"schema_version":1,"sample_rate":48000,"frames":831429,"stems":[{"track_id":"kick","role":"drums","file":"stems/kick.wav","channels":1,"sha256":"…","source":{"backend":"…","patch":"…","revision":"…"}}]}. Framezahl im Beispiel schematisch; Validator berechnet sie aus total_bars, bpm und tail. K3 rendert Instrumente und platziert K4-Assets auf Timeline; kann K4 mit Mock-WAV simulieren. Alle Spuren beginnen bei 0. Bei Teilerneuerung alte Runs unverändert; neue Stems im neuen Run.

## Mix / Report / Jobstatus

K5 liest stems.json + plan.mix und schreibt mix.wav (Premaster), master.wav und mix_report.json (Pegel, Einstellungen, Headroom, Effekte, measured true peak, LUFS, LRA, Warnungen). K6 liest alle Manifeste, erzeugt report.json mit technical:{}, music:{}, production:{}, gates:{}, missing:[], provenance:{}, listening:{blind_pairs:[], results:[]}; keine subjektiven Scores ohne tatsächliches Hörurteil. K0 führt status.json: queued/running/succeeded/failed/cancelled, stage, progress nullable, error nullable, timestamps; atomar schreiben, Recovery und Abbruch. Erst erfolgreiche validierte Run-Ausgabe als fertig kennzeichnen. Ausgeführte Befehle/Versionen/Seeds, GPU-/CPU-Zeit und Warnungen loggen, keine Secrets.

## Aufrufe (Ziel-CLI, noch nicht implementiert)

python -m sirens.production inventory
python -m sirens.production references --brief <file>
python -m sirens.production validate --plan <file>
python -m sirens.production render --brief <file> --plan <file> --mode preview|full
python -m sirens.production inspect --run <id>
python -m sirens.production revise --run <id> --plan <file> 
python -m sirens.production benchmark --manifest <file>
python -m sirens.production export --run <id> --destination <approved-root-relative-path>

Agent erhält JSON-Bericht aus CLI und schreibt neuen validierten Plan. revise erzeugt neue Run-ID; Cache nur bei identischem Input+Backend+Version+Seed. Kein GPU-Job ohne Lease / explizite Nutzeraktion. Signal-Room nutzt später exakt denselben Runner, keine zweite Implementierung. Mock-Backend nur für Tests, klar gekennzeichnet.

## Tests
A0 erstellt Beispiel-Fixtures und Validatoren. K1–K6 dürfen bis dahin eigene lokale Minimal-Fixtures aus diesen Beispielen nutzen, keine konkurrierenden Änderungen am gemeinsamen Contract. Tests mit temporären Verzeichnissen, stummen/Impuls-WAVs, künstlichen Bewertungen und ohne Netzwerk, Plugins oder GPU. 
