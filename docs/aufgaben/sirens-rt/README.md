# Sirens 2.0 (RTX Neural Music Playground): Aufgaben

Dieses Verzeichnis enthält die Aufgaben, mit denen der Plan `PLAN.md` (im selben Verzeichnis) umgesetzt wird.
Sie werden als Ketten vergeben (Register und Regeln für Bearbeiter: `KETTEN.md`). Diese Datei beschreibt, was
für **alle** Aufgaben gilt. Jede Aufgabendatei verweist hierher.

## 1. Ausgangslage

Sirens ist ein lokaler Dienst (Python 3.11, nur Standardbibliothek, `sirens/server.py` mit
`ThreadingHTTPServer`) mit einer Seite aus ES-Modulen ohne Build (`web/`). Er verwaltet Song-Aufträge und hat
ein „Live Lab“ mit Spielzeugen (Auto-DJ, Kick-Tausch, Stem Studio mit Demucs, Visualisierung). KI-Arbeit läuft
schon heute in getrennten Python-Umgebungen als Unterprozess (`sirens/stems.py`, `sirens/stem_notes.py`).

Es gibt noch keine Echtzeit-Schicht: kein AudioWorklet-Kern, keinen GPU-Manager, keine Modell-Worker, keinen
PCM-Transport.

## 2. Ziel

Ein lokales Live-Musiklabor nach `PLAN.md`: KI-Transformation, taktgenaue Neugenerierung, spektrale und
granulare Effekte, Stems, Klang-Morphing, Automatisierung und Aufnahme, auf einem Windows-Rechner mit
NVIDIA RTX 5080 (16 GB VRAM). Alles Neue ist einzeln abschaltbar und hinter dem Schalter `SIRENS_RT_ENABLED`
(Vorgabe: aus); der bisherige Betrieb bleibt unverändert funktionsfähig.

## 3. Aufgaben und Reihenfolge

Eine Aufgabe entspricht einem Arbeitspaket (WP) des Plans: `AUFGABE-nn` = `WPnn`. Der Abschnitt „WPnn“ in
`PLAN.md`, Kapitel 5, gehört verbindlich zum Umfang der Aufgabe; die Aufgabendatei schärft ihn und geht bei
Widerspruch vor. Die Wellen des Plans (Kapitel 6) sind die Ketten: erste Ziffer der Kettennummer = Welle.

| Nr | Datei | Inhalt | Setzt voraus |
|---|---|---|---|
| 00 | `AUFGABE-00-BASELINE.md` | Testgerüst, Fixtures, Vorlagen, Baseline-Skript | – |
| 01 | `AUFGABE-01-CONTRACTS.md` | Architektur, eingefrorene v1-Verträge, Mock | 00 |
| 02 | `AUFGABE-02-MODELL-SPIKES.md` | Machbarkeitsberichte und Messskripte je Modell | 00 |
| 03 | `AUFGABE-03-GPU-MANAGER.md` | GPU-Manager, Worker-Supervisor, Registry | 01 |
| 04 | `AUFGABE-04-AUDIO-CORE.md` | AudioWorklet-Kern, Uhr, PCM-Transport, Sidecar | 01 |
| 05 | `AUFGABE-05-LAB-SHELL.md` | Bereich „RTX Neural Lab“, GPU-Anzeige | 01 |
| 06 | `AUFGABE-06-MOCK-E2E.md` | Durchstich mit Mock, Gate G2 | 03, 04, 05 |
| 07 | `AUFGABE-07-DEMON.md` | DEMON Neural Remix Deck | 02 (Gate DEMON), 06 |
| 08 | `AUFGABE-08-STEM-STUDIO.md` | RoFormer/DrumSep neben Demucs | 02 (Gate Separation), 03 |
| 09 | `AUFGABE-09-DSP-RACK.md` | Spektral, Granular, Faltung | 02, 04 |
| 10 | `AUFGABE-10-BEATGRID.md` | BeatGrid, Tonart, MIDI | 01 |
| 11 | `AUFGABE-11-NEURAL-MUTATION.md` | RAVE / AFTER | 02 (Gate), 06 |
| 12 | `AUFGABE-12-PERFORMANCE-PADS.md` | Generative Pads | 02 (Gate), 06, 10 |
| 13 | `AUFGABE-13-SEMANTIC-STEM.md` | SAM Audio | 02 (Gate), 03 |
| 14 | `AUFGABE-14-PERFORMANCE-TOOLS.md` | Drum Architect, Stem Crossover, Acid | 06, 08, 09, 10 |
| 15 | `AUFGABE-15-COMPANION.md` | Magenta-Begleitspur (optional) | 02 (Gate), 06, 10 |
| 16 | `AUFGABE-16-RECORDER.md` | Aufnahme, Session, Export | 04, 06 |
| 17 | `AUFGABE-17-INTEGRATION.md` | Produktintegration und UX | 08, 09, 14, 16 |
| 18 | `AUFGABE-18-INFINITE-MUTATION.md` | Automatisierte Performance (optional) | 10, 14, 16 |
| 19 | `AUFGABE-19-SYSTEMABNAHME.md` | Regression, Soak-Skripte, Gate G4 | 17 |
| 20 | `AUFGABE-20-ROLLOUT.md` | Installer, Runbook, Release Candidate | 19 |
| 21 | `AUFGABE-21-SPIKES-MESSPFADE.md` | Rest von WP02: Pins, Gewichte, lauffähige Messpfade | 02 |
| 22 | `AUFGABE-22-MESSPFAD-DEMON.md` | Messpfad DEMON | 21 |
| 23 | `AUFGABE-23-MESSPFAD-RAVE-AFTER.md` | Messpfad RAVE und AFTER | 21 |
| 24 | `AUFGABE-24-MESSPFAD-MAGENTA.md` | Messpfad Magenta RealTime | 21 |
| 25 | `AUFGABE-25-STEM-STUDIO-2.md` | Rest von WP08: Dateijob, RoFormer im Produkt | 08 |
| 26 | `AUFGABE-26-INTEGRATION-2.md` | Rest von WP17 | 17 |
| 27 | `AUFGABE-27-PADS-2.md` | Rest von WP12: Verdrahtung der Pads | 12 |
| 28 | `AUFGABE-28-HOOKS-EINBAU.md` | Alle offenen Hooks in die Oberfläche | 17, 26 |
| 29 | `AUFGABE-29-GPU-REGEL.md` | GPU-Regel, Profile, dauerhafter Supervisor | 03, 26 |

## 4. Feste Bedingungen (nicht ändern)

1. **Zielzweig ist `integration/sirens-rt`.** Wo ein Text „main“ sagt, ist dieser Zweig gemeint. Branch von
   `origin/integration/sirens-rt`, PR gegen `integration/sirens-rt`. Nichts geht direkt nach `main`.
2. **Bestand bleibt heil.** Auftragsverwaltung, Claude-Starter, Katalog, Mastering, Auto-DJ, Kick-Tausch und
   Stem Studio funktionieren weiter. Bestehende HTTP-Adressen und ihr Verhalten bleiben gleich. Originaldateien
   im Musikordner werden nie überschrieben; neue Ergebnisse liegen in eigenen Cache- und Sitzungsordnern.
3. **Hauptprozess bleibt schlank.** Das Paket `sirens/` importiert nur die Standardbibliothek. Kein `torch`,
   kein `numpy`, keine Modellbibliothek. Modelle laufen in getrennten Worker-Prozessen unter `workers/` mit
   eigener Umgebung und eigenem Lockfile.
4. **Nichts lädt von selbst.** Kein Modell-Download beim Start, beim Öffnen einer Seite oder in Tests. Keine
   Modellgewichte, keine Musikdateien, keine großen Binärdateien im Repo. Audiomaterial verlässt den Rechner
   nicht.
5. **Ehrliche Fähigkeiten.** Was nicht installiert, nicht gemessen oder nicht freigegeben ist, ist in der
   Oberfläche abgeschaltet und so benannt. Ein Mock heißt Mock. Kein „Streaming“, „Live“ oder „Echtzeit“ ohne
   Messung auf dem Zielrechner.
6. **Messungen auf dem Zielrechner macht der Koordinator.** Der Bearbeiter hat keine RTX 5080. Für jede
   Abnahme, die die Zielhardware, einen Browser mit Tonausgabe oder ein echtes Modell braucht, liefert er ein
   Skript mit genauem Aufruf und Ergebnisformat (unter `benchmarks/`), dazu Tests mit Mock oder CPU. In der
   Ergebnisdatei steht dann „nicht gemessen“, nie eine geschätzte oder fremde Zahl als Ergebnis.
7. **Gemeinsame Dateien.** `sirens/server.py`, `sirens/config.py`, `.env.example`, `README.md`,
   `.github/workflows/tests.yml`, `web/js/live_lab.js`, `web/js/main.js`, `web/index.html` und die
   bestehenden CSS-Dateien ändert nur die Aufgabe, die es ausdrücklich erlaubt. Alle anderen liefern eigene
   Module und beschreiben den nötigen Einbau in `docs/realtime/hooks/WPnn.md` (Datei, Stelle, Code).
8. **Verträge sind eingefroren**, sobald Aufgabe 01 gemergt ist (`docs/realtime/`,
   `sirens/realtime/contracts.py`, Schemas). Wer eine Änderung braucht, schreibt eine ADR nach
   `docs/realtime/adr/` und nennt sie in der Ergebnisdatei; die Verträge selbst ändert er nicht.
9. **Sicherheit.** Der Dienst hört nur auf Loopback. Die Host-, Origin- und JSON-Prüfungen in
   `sirens/server.py` und die Pfadprüfung `safe_audio_path` in `sirens/contracts.py` gelten für alle neuen
   Adressen. Keine frei wählbaren Befehle oder Worker-Pfade aus Anfragen, kein Pickle aus fremden Quellen,
   kein offenes CORS. Keine Secrets im Repo.
10. Aufgehoben sind nur zwei frühere Regeln: höchstens 400 Zeilen je Datei und keine externen
    Frontend-Quellen. Alle anderen Tests bleiben und bleiben grün. Neue Frameworks oder ein Build-System nur
    mit ADR und belegtem Nutzen.

## 5. Regeln für die Umsetzung

- Qualitätsprüfung: `python -m unittest discover -s tests -v` (Python 3.11, Node 22 im Pfad). Maßgeblich ist
  die CI des PR, die genau diesen Befehl ausführt: früh pushen, Draft-PR sofort öffnen, Fehler anhand der
  CI-Ausgabe beheben. Lokal ausführen, soweit die eigene Umgebung es erlaubt; fehlt sie, hält das nichts auf. Neue Python-Tests müssen davon erfasst werden (Unterordner von
  `tests/` brauchen `__init__.py`); neue Node-Tests heißen `*.test.mjs` und liegen unter `tests/` (ab
  Aufgabe 00 sammelt `tests/test_web.py` sie rekursiv ein).
- Tests laufen ohne Netz, ohne GPU und ohne Modellgewichte.
- Sprache: Oberfläche, Meldungen, Doku und Kommentare auf Deutsch wie im Bestand; Bezeichner dürfen im neuen
  Echtzeit-Teil englisch sein.
- Fehler nach dem Muster `Ablehnung` aus `sirens/contracts.py`.
- Jede Aufgabe nennt in ihrer Ergebnisdatei: verwendete Versionen und Commit-Pins fremder Projekte, Lizenz von
  Code und Gewichten, Hardwarebedarf, bekannte Grenzen und die Befehle zum Nachstellen.

## 6. Begriffe

| Begriff | Bedeutung |
|---|---|
| WP | Arbeitspaket des Plans; `WPnn` = `AUFGABE-nn` |
| Koordinator | Claude; vergibt, prüft, misst auf dem Zielrechner, merged (im Plan „A0“) |
| Zielrechner | Windows 11, NVIDIA RTX 5080 mit 16 GB VRAM |
| Gate | Messschranke des Plans (Kapitel 7): G1 je Modell, G2 Kern, G3 je Funktion, G4 Release |
| grün / amber / rot | Gate-Ergebnis: geplanter Modus belegt / nur kleiner, Lookahead oder Offline / nicht nutzbar |
| Dry / Wet | unbearbeitetes Signal / bearbeitetes Signal |
| Lookahead | Ergebnis wird vorab berechnet und taktgenau eingesetzt, statt fortlaufend gestreamt |
| Control plane | Steuer-API unter `/api/rt/v1/` im Hauptdienst |
| Data plane | binärer PCM-Transport über einen lokalen Sidecar-Prozess |
| Hook | beschriebener Einbau in eine gemeinsame Datei, den eine berechtigte Aufgabe ausführt |

## 7. Abnahme über alle Aufgaben

1. Mit `SIRENS_RT_ENABLED` aus verhält sich Sirens wie vor dem Vorhaben; alle bisherigen Tests sind grün.
2. Jede freigegebene Funktion hat ein bestandenes Gate mit Messdatei unter `benchmarks/results/`.
3. Nicht freigegebene Funktionen sind abgeschaltet und benannt; nichts täuscht KI vor.
4. Keine Originaldatei wurde verändert, kein Worker bleibt nach dem Beenden zurück.
