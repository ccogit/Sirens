# AUFGABE-16 – Laufzeiten je Stufe (KETTE-P13)

Stand: 24.11.2026. Implementiert; Ausführung der Tests und Windows-Abnahme offen.
[PR #69](https://github.com/ccogit/Sirens/pull/69) auf `integration/sirens-production`.
Ausgangsstand `ce1a74052e33fbbe88db02e0cd65028ca994f8aa`.
Kein Registereingriff, keine Änderungen an anderen Ketten, kein Selbst-Merge.

## Umsetzung und Abnahmebelege

| Anforderung | Umsetzung / Prüfbeleg |
|---|---|
| Atomarer, abwärtskompatibler Jobstatus | `jobs.py`: bestehendes `write_json_atomic` und `validate_status` unverändert weiterverwendet. Schema-Version 1, vorhandene Felder bleiben erhalten, `stages` und `total_seconds` ergänzend. Altstatus ohne Zusatzfelder bleibt lesbar. Test `test_progress_and_stage_changes`, `test_legacy_status_and_queued_cancel`. |
| Laufzeiten je Stufe | `RunStore.status` startet ausschließlich tatsächlich betretene running-Stufen, schließt die vorherige Stufe beim Wechsel, lässt Fortschrittsupdates derselben Stufe ohne Neustart. UTC-Zeitstempel ISO 8601 mit Mikrosekunden, Dauer in Sekunden; offene Stufe: finished/seconds null. Runner misst prepare, assets, stems (Instrumente), mix, report, ggf. vorangestellten preview aus bestehendem Service. Kein künstlicher complete-Eintrag. |
| Gesamtzeit | `total_seconds` seit erstem running, nicht seit queued; queued ohne Start: null, terminal ohne Start: 0.0. Erster running-Zeitstempel wird nicht überschrieben. Tests mit Fake-Uhr einschließlich 5,5 s Gesamtzeit und nicht mitgerechneter Wartezeit. |
| Report | `runner.py`: finale Zeitwerte einschließlich abgeschlossener report-Stufe als gleichnamige Top-Level-Felder in report.json; vor Veröffentlichung des terminalen Status atomar geschrieben und validiert. `test_success_report_matches_terminal_status`, `test_technical_failure_report_contains_closed_stage`. |
| Abbruch und Fehler schließen laufende Stufe | Terminalübergang schließt die tatsächlich laufende Stufe, auch wenn angegebener Zielname abweicht. Checkpoint prüft Cancel vor Wechsel. Recovery schließt persistierte aktive Stufe. `test_cancel_and_failure_close_active_stage_not_requested_stage`, `test_recovery_with_new_store_instance`, `test_error_and_cancellation_inside_stage`, `test_cancel_between_stages`. |

Alle neun neuen Testmethoden (fünf RunStore, vier Runner) sind geschrieben, **nicht ausgeführt**. Runner-Tests verwenden Fake-Backend und isolieren fremde Audio-/Planvalidatoren; echte Status-/Reportvalidatoren und atomare JSON-Dateien werden benutzt. Keine Netz-, GPU-, Plugin- oder Live-Zugriffe in diesen Tests. Temporäre Ordner, pathlib und UTF-8-Dateizugriffe.

## Reuse

| Funktion | Quelle / tatsächlich geprüfte Schnittstelle | Entscheidung | Lücke / Test |
|---|---|---|---|
| Status und Report | Sirens K00/K08, `RunStore.status`, `write_json_atomic`, `validate_status`, `validate_report`, `Runner.render` am Ausgangsstand | ADAPT / REUSE | Fehlende persistierte Stufenzeiten; Fake-Uhr-Tests oben. |
| AMM / SecondRoom / Producer Pal | REUSE-AMM.md gelesen; bestehende Adapter in Runner/Integration geprüft | REUSE unverändert | Keine Änderung an Produktions-, Audio- oder Live-Schnittstellen nötig, da ausschließlich Sirens-eigener Status gemessen wird. |

PLAN, CONTRACT, KETTEN, README, REUSE-AMM und K08/K09-Ergebnisberichte gelesen. AUFGABE-16 nennt keine konkrete weitere Ergebnisdatei des ersten Clear-Head-Laufs.

## Prüfung, Abweichungen und Risiken

- GitHub-Commits: `e2edc1c609f8f530300533262e699835862fe47a` (Status), `f8f884f93a9bd793e89205ec8e01e2b29ebb35f0` (Runner), `85e762440dc863333473299f6dc0374c44d57600` (RunStore-Tests), `f572091f8a61e8e1e06a6926be99176d62a848cb` (Runner-Tests).
- Git-Checkout nicht möglich: `git ls-remote https://github.com/ccogit/Sirens.git refs/heads/integration/sirens-production` → `fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`. Dateien direkt über GitHub gelesen und geschrieben. Kein lokaler Python-Testlauf, kein CI (Actions abgeschaltet).
- Koordinator: aus dem Kettencheckout `py -3.11 -m unittest discover -s tests/production -p "*stage_times.py" -v`, anschließend `py -3.11 -m unittest discover -s tests -v`. Erwartung: neun neue Testmethoden erfolgreich, gesamte Suite ohne neue Fehler. Linux entsprechend mit python3.11. Tatsächlicher Clear-Head-Lauf nicht gemessen.
- Entscheidungen: persistierte UTC-Zeit dient auch der Recovery; keine monotone Uhr über Prozessneustarts hinweg. Rückwärtskorrekturen werden auf 0 s begrenzt; größere Wanduhrkorrekturen können Zeiten verzerren. Alte laufende Jobs haben keine rekonstruierbaren historischen Stufen; alte abgeschlossene Status werden nicht umgeschrieben. Laufzeit enthält Cache- und Orchestrierungsarbeit, nicht nur Modellrechenzeit.
- Report und Status sind jeweils atomar, nicht gemeinsam transaktional. Bei I/O-Fehler/Crash kann ein Zwischenstand des Reports zurückbleiben; ein fehlgeschlagener/abgebrochener Lauf ohne erzeugten Report erhält weiterhin vollständige Statuszeiten. Report-Übernahme gilt für Runner-Produktion; eigenständiger Ableton-Return in integration.py bleibt außerhalb des Owner-Umfangs.
- Keine neuen Abhängigkeiten, Modellimporte, Audiodaten, Secrets oder Kundendaten.

Status: Ready zur Windows-Prüfung durch den Koordinator; keine grüne CI oder bereits bestandene Abnahme behauptet.
