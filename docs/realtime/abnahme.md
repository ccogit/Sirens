# WP19 – Systemabnahme / Gate G4

**Stand: nicht gemessen.** Diese Anleitung ist kein Gate-Entscheid. Die PR-CI ist
für die CPU-Regression maßgeblich; die Zielmessung erfolgt durch den Koordinator
auf Windows 11 / RTX 5080 (16 GiB). Nur freigegebene, lokal installierte Modelle
verwenden; kein Download, keine Kundendaten, keine Audio- oder Gewichtsdatei
einchecken. Audio-, Geräte- und Modellmesswerte werden nicht geschätzt.

## Matrix Funktion × Profil × Gate

E = Eco; P = Performance; N = Neural; T = Training/Render. "–" = nicht geplanter
Modus bzw. absichtlich abgeschaltet, nicht bestanden. Jede zu prüfende Zelle ist
offen (nicht_gemessen). GPU-Worker in Eco sind gesperrt, Profile begrenzen
Worker/Jobs gemäß Registry; keine Annahme, dass zwei Modelle gemeinsam passen.

| Funktion | E | P | N | T | Gate / Messpfad |
|---|---|---|---|---|---|
| Bestandsbetrieb, Flag aus | Regression | Regression | Regression | Regression | G4, unittest + Sichtprüfung |
| AudioCore, PCM, Uhr, Dry | CPU | 2h Soak | CPU + Last | CPU | G2/G4, audio_core, g2, g4 |
| Mock-Durchstich | Mock | Mock | Mock | Mock | G2, g2/soak.js, ohne KI |
| DSP-Rack, Limiter | fast | fast | fast + Last | standard/detail | G3/G4, dsp |
| BeatGrid/Tonart/MIDI | CPU | CPU | CPU | CPU | G3, beatgrid |
| Drum Architect, Crossover, Acid | CPU | Hörtest | Hörtest | Render | G3, performance |
| Aufnahme/Export | PCM | Browser + PCM | Browser + PCM | PCM | G3/G4, recorder |
| Integration, Stop/Panic | Sicht | Sicht/Hörtest | Sicht/Hörtest | Sicht | G3/G4, integration |
| RoFormer (Separation) | – | offline* | offline* | offline* | G1/G3, separation |
| Stable Audio 3 | – | lookahead* | lookahead* | lookahead* | G1/G3, pads |
| Alle weiteren Registry-Fähigkeiten | – bei GPU | Modus* | Modus* | Modus* | G1/G3/G4, je nach Registry |
| Infinite Mutation / Companion | nur falls freigegeben | Modus* | Modus* | Modus* | G3/G4, nach Einbau |

\* Nur bei passender G1-Freigabe und verfügbarer Registry-Capability. G1 RoFormer:
offline; DrumSep nicht freigegeben. Stable Audio: lookahead, keine Streaming-Freigabe.
Das ist keine neue Gate-Entscheidung. Die Suite ermittelt die Modellzeilen bei jedem
Start aus ModelRegistry und G1-Dateien. Sie berücksichtigt gleichnamige Berichte
automatisch (Bindestrich/Unterstrich normalisiert); historische Zuordnungen stehen
in ALIASES. Ein verfügbar gemeldetes Modell ohne passenden G1-Beleg ist ein Fehler
im Hardwarelauf. Ein neuer freigegebener Kandidat ohne Plan-Eintrag wird nicht
stillschweigend übersprungen, sondern als fehlender Messpfad gemeldet.

## Wiederholbarer Aufruf

Im Repo-Wurzelverzeichnis, PowerShell 7 oder Windows PowerShell, Python 3.11
und Node 22 im Pfad:

```powershell
python -m unittest discover -s tests -v
.\benchmarks\suite.ps1 -DryRun
# Ausgabeordner wird angezeigt, suite.json validieren:
python -m benchmarks.result C:\TEMP\sirens-g4-...\suite.json
```

DryRun führt keine Messkommandos, GPU-Abfragen, Netzwerk- oder Modellaufrufe aus.
Er erzeugt einen synthetischen Originalbestand, prüft dessen Hash, ermittelt die
Registry und schreibt ein validiertes Ergebnis mit null-Messwerten sowie
nicht_gemessen je Funktion. Ausgabe außerhalb des Repos, nie überschreiben.

Hardware: Mit synthetischem, separatem Musikordner und dessen Kopie arbeiten.
Sämtliche Dateien im angegebenen Musikordner werden vor/nach dem Lauf SHA-256
gehasht, einschließlich neuer/entfernter Dateien; Symlinks werden abgelehnt.
Vor Beginn alle eigenen Sirens-Worker beenden; fremde Prozesse nicht antasten.
Den Beispielplan nach außerhalb des Repos kopieren, Platzhalter durch echte
lokale Pfade und bereits gemessene Vorgaben ersetzen. Keine Secrets in den Plan.
Nur vertrauenswürdige selbst erstellte Pläne verwenden: argv wird lokal direkt
ohne Shell ausgeführt; keine Anbindung an HTTP/Anfragen.

```powershell
Copy-Item .\benchmarks\g4\plan.example.json C:\TEMP\g4-plan.json
.\benchmarks\suite.ps1 -MusicRoot C:\G4\Synthetisch -Plan C:\TEMP\g4-plan.json -OutputDir C:\TEMP\g4-run-01
python -m benchmarks.result C:\TEMP\g4-run-01\suite.json
```

Jeder Plan-Eintrag ist nach Capability-ID benannt. argv enthält genau eine
Argumentliste oder steps mehrere sequenzielle Argumentlisten. {python} ist der
Hauptinterpreter, {dir} der externe Ausgabeordner und {out} die erwartete
validierte JSON-Messdatei. Worker-Python ausdrücklich aus lokaler Installation
angeben. Optionale instruction wird vor dem Messpfad angezeigt, interactive
schaltet die Konsolenausgabe frei, timeout begrenzt jeden Prozess in Sekunden.
Browser-Rohberichte werden während des Laufs in den angezeigten Ordner
gespeichert (neue Datei, await_file); keine alten Messwerte wiederverwenden.
Messberichte und Logdateien liegen je Funktion getrennt im Ausgabeordner.
Eine fehlende/ungültige Messdatei, roter Bericht, fehlende Mindestdauer,
ungeklärter neuer Worker oder Hashabweichung führt zu Exitcode 1; die Suite
versucht die weiteren Messpfade und schreibt die Sammeldatei. Kein automatisches
G4-Grün. Die Windows-CIM-Prozessprüfung beobachtet eigene Worker/Sidecars und
ihre identifizierten Kindprozesse während und nach der Suite; Prozess-ID plus
Startzeit verhindert Verwechslung bei Wiederverwendung. Kurzlebige Zwischeneltern
zwischen Abtastungen können unentdeckt bleiben; abschließende manuelle Kontrolle
im Prozessmanager ist zusätzlich nötig. Keine automatische Prozessbeendigung
außer beim Timeout des direkt gestarteten Messkommandos.

Neue Streaming-Modelle: Plan-Eintrag mit G4-Rohmessung gemäß unten und
zusätzlichem jeweiligem G3-Messpfad ergänzen; die Suite fordert mindestens 1800 s
und null unerwartete Underruns. Offline/Lookahead separat, nie als Streaming
bewerten. Fehlende Modellinstallation/Registry-Freigabe bleibt nicht_gemessen.

## Soak und Hörtest

1. Audioausgabe bei niedrigem Pegel, 48 kHz bzw. gemessener Gerätekonfiguration.
   Performance-Profil einstellen, repräsentative längere Performance mit
   synthetischer Quelle, Loops, DSP, Stems, Aufnahmen und erlaubten Aktionen
   vorbereiten. Last, Modellrevision, Gerät, Treiber, Puffer, CPU/GPU/RAM/VRAM
   dokumentieren; keine Thermik künstlich erzwingen.
2. Bei aktiver Wiedergabe den Inhalt von benchmarks/g4/soak.js auf der lokalen
   Sirens-Seite als DevTools-Snippet ausführen, 7200 eingeben. Die laufende
   Wiedergabe beibehalten, Fehler und reale hörbare Aussetzer protokollieren.
   Die Messung beobachtet AudioCore-Telemetrie und Wand-/Audiozeit; sie steuert
   keine Performance-Aktionen automatisch.
3. Für jedes wirklich freigegebene Streaming-Modell separat 1800 s, mit realem
   Modellpfad (kein Mock) und dessen G3-Messung (RTF p95 <=0,8,
   Control-to-audio p95 <=250 ms als Ziel). Modellwechsel oder Profilwechsel
   nicht als fortlaufende Messung werten. Lookahead: >=20 Jobs, >=95 %
   rechtzeitig; verspätete Jobs verwerfen/verschieben. Offline: Laufzeit,
   Qualität, VRAM und Grenzen getrennt.
4. Nach Ende Rohbericht extern speichern und Sitzung vollständig schließen.
   `python -m benchmarks.g4.report ROH.json --candidate Performance --out RESULT.json`;
   `python -m benchmarks.result RESULT.json`. Bei Streaming-ID candidate
   entsprechend setzen. Keine Gate-Automatik: selbst null Underruns beweist
   weder analog lückenlose Wiedergabe noch RTF/Steuerlatenz.
5. Separat (nicht in den ungestörten Soak hineinrechnen) Störfälle auslösen:
   Hintergrundtab und Rückkehr, Gerätewechsel, Seek/Loop, Verbindungsabbruch,
   Claude-Start, laufende Produktion, GPU-Druck, Stop/Panic. Jeweils Dry-Rückfall,
   Meldungen, Wiederanlauf, fehlende Fremdprozess-Eingriffe prüfen. Platte-voll
   ausschließlich mit Mock/isoliertem Testbestand; nicht Systemplatte füllen.
6. Gain-matched A/B, sichere Lautstärke: Dry/Wet bei gleichen Pegeln;
   NaN/Inf, Clipping, Knackser, Zeitversatz, Stem-Leakage, Klangtreue,
   Pad-Prompt-Treue, Aufnahme und Export anhören. Output-Peak Ziel <= -1 dBFS,
   True Peak nur gemessen. Physische Geräte-Latenz separat wie WP04.
7. Für jede Matrixzelle Profil, Capability-ID/Revision, Belegdatei, Datum,
   Beobachtung, Grenzen, Fehler und Status (bestanden / fehlgeschlagen /
   nicht_gemessen) extern dokumentieren; jedes Profil separat wiederholen.
   Die Beispiel-Suite enthält einen Durchgang pro Funktions-ID, nicht automatisch
   alle 12 DSP-Profil-/Spurkombinationen oder vier Produktprofile. Weitere
   Durchgänge mit getrennten Ausgabeordnern und Plänen erfassen.

G4-Ziel: zwei Stunden Performance ohne unerwartete Audioaussetzer, CPU-CI grün,
keine Source-Änderung, keine unkontrollierten Worker; dokumentierte Modellgrenzen,
Installationen, Hörprüfungen. Kern/Sicherheit/Bestand bei Fehlern nicht freigeben.
Nur der Koordinator entscheidet über deaktivierte Modelle und Gate G4.
