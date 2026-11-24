# Ketten: Vergabe und Zusammenarbeit

Die Aufgaben dieses Verzeichnisses werden als **Ketten** an externe Bearbeiter vergeben. Eine Kette ist eine
feste Folge von Aufgaben, die ein Bearbeiter in **einem** Branch und **einem** PR liefert. Der Koordinator
vergibt, prüft und merged.

Die Ketten bilden die Wellen aus `PLAN.md`, Kapitel 6, ab: Die erste Ziffer der Kettennummer ist die Welle.
Ketten derselben Welle laufen nebeneinander, sobald ihre Voraussetzungen gemergt sind.

## Register

| Kette | Titel | Aufgaben | Voraussetzung | Stand |
|---|---|---|---|---|
| KETTE-00 | Welle 0: Baseline und Testgerüst | 00 | – | offen |
| KETTE-11 | Welle 1: Verträge und Architektur | 01 | KETTE-00 gemergt | offen |
| KETTE-12 | Welle 1: Modell-Spikes (Berichte und Messskripte) | 02 | KETTE-00 gemergt | offen |
| KETTE-21 | Welle 2: GPU-Manager und Worker-Supervisor | 03 | KETTE-11 gemergt | offen |
| KETTE-22 | Welle 2: Audio Core und Data Plane | 04 | KETTE-11 gemergt | offen |
| KETTE-23 | Welle 2: Live Lab Shell und GPU-Anzeige | 05 | KETTE-11 gemergt | offen |
| KETTE-24 | Welle 2: BeatGrid, Tonart, MIDI | 10 | KETTE-11 gemergt | offen |
| KETTE-25 | Welle 2: DSP Rack | 09 | KETTE-12 gemergt, KETTE-22 gemergt | offen |
| KETTE-26 | Welle 2: Advanced Stem Studio | 08 | KETTE-12 gemergt, KETTE-21 gemergt, Gate G1 Separation gemessen | gesperrt (wartet auf G1-Messung am Zielrechner) |
| KETTE-27 | Welle 2: Semantic Stem Extractor | 13 | KETTE-12 gemergt, KETTE-21 gemergt, Gate G1 SAM Audio gemessen | gesperrt (wartet auf G1-Messung am Zielrechner) |
| KETTE-31 | Welle 3: Mock-Durchstich, Gate G2 | 06 | KETTE-21 gemergt, KETTE-22 gemergt, KETTE-23 gemergt | offen |
| KETTE-32 | Welle 3: Recorder, Session, Export | 16 | KETTE-31 gemergt | offen |
| KETTE-33 | Welle 3: DEMON Neural Remix Deck | 07 | KETTE-31 gemergt, Gate G1 DEMON gemessen | gesperrt (wartet auf G1-Messung am Zielrechner) |
| KETTE-34 | Welle 3: Neural Mutation (RAVE, AFTER) | 11 | KETTE-31 gemergt, Gate G1 RAVE/AFTER gemessen | gesperrt (wartet auf G1-Messung am Zielrechner) |
| KETTE-35 | Welle 3: Generative Performance Pads | 12 | KETTE-31 gemergt, KETTE-24 gemergt, Gate G1 Stable Audio gemessen | gesperrt (wartet auf G1-Messung am Zielrechner) |
| KETTE-36 | Welle 3: Generative Companion (optional) | 15 | KETTE-31 gemergt, KETTE-24 gemergt, Gate G1 Magenta gemessen | gesperrt (optional, wartet auf G1-Messung und Freigabe) |
| KETTE-37 | Welle 3: Performance-Tools | 14 | KETTE-31 gemergt, KETTE-26 gemergt, KETTE-25 gemergt, KETTE-24 gemergt | offen |
| KETTE-41 | Welle 4: Produktintegration und UX | 17 | KETTE-26 gemergt, KETTE-25 gemergt, KETTE-37 gemergt, KETTE-32 gemergt | offen |
| KETTE-42 | Welle 4: Infinite Mutation (optional) | 18 | KETTE-24 gemergt, KETTE-37 gemergt, KETTE-32 gemergt, ein neuronaler Pfad freigegeben | gesperrt (optional, wartet auf neuronalen Pfad und Freigabe) |
| KETTE-51 | Welle 5: Systemabnahme, Gate G4 | 19 | KETTE-41 gemergt | offen |
| KETTE-52 | Welle 5: Rollout und Release Candidate | 20 | KETTE-51 gemergt, Gate G4 bestanden, Freigabe des Repo-Eigentümers | gesperrt (wartet auf G4 und Freigabe) |

Den Stand ändert nur der Koordinator (`offen`, `vergeben (TT.MM.JJJJ)`, `gemergt`, `gesperrt`). Bearbeiter
reservieren nichts und ändern diese Datei nicht.

## Regeln für Bearbeiter

1. **Ein Branch, ein PR, Zielzweig `integration/sirens-rt`.** Branch `extern/KETTE-nn` vom aktuellen
   `origin/integration/sirens-rt`. Früh genau einen Draft-PR `extern/KETTE-nn` → `integration/sirens-rt`
   öffnen (Basis im PR ausdrücklich auf `integration/sirens-rt` stellen, nicht `main`). Keine Einzel-Branches
   oder Einzel-PRs je Aufgabe.
2. **Reihenfolge.** Die Aufgaben der Kette in der Reihenfolge des Registers. Commits je Aufgabe mit Präfix
   `AUFGABE-nn: …`. Umfang und Abnahme stehen verbindlich in `AUFGABE-nn-….md` und im Abschnitt „WPnn“ von
   `PLAN.md`; gemeinsame Bedingungen in `README.md` dieses Verzeichnisses.
3. **Ergebnis je Aufgabe.** Eine Datei `docs/aufgaben/sirens-rt/ergebnisse/AUFGABE-nn.md`: was umgesetzt
   wurde, je Abnahmepunkt der Beleg (Test, Befehl, Ausgabe), was nicht geprüft werden konnte („nicht
   gemessen“ samt Skript und Aufruf für den Koordinator), Abweichungen von der Aufgabe mit Grund, Versionen,
   Pins und Lizenzen fremder Projekte, offene Risiken, Rückbau.
4. **Qualität.** `python -m unittest discover -s tests -v` ist vor jedem Push grün. Die CI des PR ist grün.
   Tests zu jeder Änderung, ohne Netz, ohne GPU, ohne Modellgewichte.
5. **Aktuell bleiben.** Regelmäßig `origin/integration/sirens-rt` in den Branch mergen (kein Force-Push, kein
   Rebase nach dem ersten Push), Konflikte selbst lösen.
6. **Grenzen.** Kein Torch- oder Modell-Import im Paket `sirens/`. Keine Modellgewichte, Musikdateien oder
   Downloads im Repo. Gemeinsame Dateien (README, Abschnitt 4, Punkt 7) nur ändern, wenn die Aufgabe es
   ausdrücklich erlaubt; sonst den Einbau als Hook in `docs/realtime/hooks/WPnn.md` beschreiben. Keine
   Secrets. Nichts außerhalb des Umfangs der Aufgaben ändern; Auffälliges außerhalb des Umfangs steht in der
   Ergebnisdatei unter „Beobachtungen“.
7. **Keine erfundenen Messwerte.** Was die Zielhardware, einen Browser mit Tonausgabe oder ein echtes Modell
   braucht, wird als Skript geliefert und als „nicht gemessen“ ausgewiesen. Der Koordinator misst.
8. **Durcharbeiten.** Ohne Rückfrage Aufgabe für Aufgabe weiter. Bei einer echten Blockade die Annahme in der
   Ergebnisdatei festhalten und mit der sinnvollsten Auslegung weiterarbeiten.
9. **Abschluss.** Sind alle Aufgaben der Kette fertig und die CI grün: PR auf „Ready for review“ setzen, im
   PR-Text je Aufgabe: WP, Depends-on, Änderungen, Tests, Hardwaremessung oder ausdrücklich „nicht gemessen“,
   Risiken, Rollback. Der Koordinator prüft und merged den Ketten-PR als Ganzes. Nacharbeit kommt als
   Nachricht im Chat der Kette; der PR ist dann nicht abgeschlossen.
