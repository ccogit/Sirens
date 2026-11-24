# AUFGABE-01 – Verträge und Architektur (WP01)

WP00 gemergt; Branch extern/KETTE-11, [PR #8](https://github.com/ccogit/Sirens/pull/8) gegen integration/sirens-rt. Erster Commit 88ec4416 direkt gepusht, dann Draft-PR eröffnet. Integrationsstand 9e1ae563 per Merge 1cf7989f übernommen; Registeränderungen stammen vom Koordinator.

## Umsetzung

Architektur, Protokoll, Adapter, Sicherheit und fünf ADRs in docs/realtime; 13 JSON-Schemas mit Beispielen für neun API-Adressen, zwei PCM-Hex-Referenzen; Python-Zustandsautomaten, Befehls- und Schema-Prüfung, Pfade, PCM-Codec, Gain/Delay-Mock; JS-PCM und UI-Mock. Schalter SIRENS_RT_ENABLED standardmäßig aus, optional SIRENS_RT_DIR und SIRENS_RT_MOCK. Einzige neue Weiche im bestehenden Server, nur GET capabilities implementiert, übrige RT-Adressen unavailable. Die zunächst bearbeitete WP01-Board-Zeile ist nach der zwischenzeitlich gemergten Koordinatorregel (Board nur A0) auf den Integrationsstand zurückgesetzt. Keine echten Worker, kein Sidecar, keine Oberfläche.

## Abnahme

| Nr. | Beleg | Stand |
|---|---|---|
| 1 | realtime.test_rt_contracts.Schemas: alle 13 Schemas, positive/negative Beispiele, 9 HTTP-Paare, Capability-Parität | CI grün |
| 2 | PCM.test_fixtures_and_roundtrip, PCM.test_invalid und rt_contracts.test.mjs: beidseitig identische Hex-Referenzen, BigInt, Fehlerfälle | CI grün |
| 3 | Contracts.test_transitions, test_commands: alle Zustandspaare, alte Epoch und ungültige Befehle | CI grün |
| 4 | HTTP.test_switch_and_security sowie unveränderte Bestandstests: 503/200, Schema, Origin/Host | CI grün |
| 5 | Contracts.test_stdlib_imports_recursively: AST rekursiv, keine neuen Fremdimporte; Alt-Worker-Ausnahmen siehe unten | CI grün; wörtliche Abnahme mit dokumentierter Altbestandsausnahme |
| 6 | Mock.test_gain_delay: samplegenauer Gain/Delay über Blockgrenzen, Lifecycle und Determinismus | CI grün |
| 7 | python -m unittest discover -s tests -v | CI grün |

Erster Code-CI-Lauf [45452123740](https://github.com/ccogit/Sirens/actions/runs/45452123740), Head da8f1362: 101 Tests, 1 Fehler, 4 bestehende Skips. Fehler: test_stdlib_imports_recursively, AssertionError: numpy not found … sirens/kick_dsp.py. Kein neuer RT-Test außer diesem Importinventar fehlgeschlagen. Zweiter Code-CI-Lauf [45452333368](https://github.com/ccogit/Sirens/actions/runs/45452333368), Head 05592a62: 101 Tests, 1 Fehler, 4 bestehende Skips. Fehler: AssertionError: basic_pitch not found … sirens/stem_transcribe.py. Korrektur: zwei unveränderte Bestands-CLIs: kick_dsp.py (numpy, scipy, soundfile) via kicktausch.py und stem_transcribe.py (basic_pitch) via stem_notes.py; beide werden ausschließlich als Unterprozess gestartet. Nur diese konkreten Altimporte sind zugelassen; alle übrigen Fremdimporte und Paketimporte dieser CLIs bleiben verboten. Das strikte wörtliche Kriterium „kein Modul unter sirens/“ ist wegen des Altbestands nicht vollständig erfüllt; Verschiebung der Bestands-CLIs wäre außerhalb WP01 und potenziell regressiv.

## Entscheidungen, Grenzen, Risiken

- PCM-Header 32 Byte, reservierte Flags 0, Rate 8–192 kHz, Payload bitgetreu (Audio-Empfänger muss nicht-endliche Samples stummschalten); Frame uint64 im Binärtransport, JSON-Zahlen bis 2^53−1. ID 32 Hexzeichen, Sequenz uint32. Sicherheitslimits und Heartbeat sind initiale Vertragswerte, keine gemessenen Leistungswerte.
- JSON-Schema-Validator unterstützt nur das eingesetzte Schlüsselwortprofil, kein allgemeiner Draft-2020-12-Validator. UI-Mock simuliert sofortige Jobfertigstellung, keinen echten Scheduler, keine Zeit/Audio. Capability Mock offline, keine GPU-Freigabe.
- Zielhardware **nicht gemessen**: WP01 liefert nur CPU-Verträge, kein Leistungs-Gate; spätere WP03/04/06 und Koordinator messen. Keine fremden Projekte, Gewichte, zusätzlichen Lizenzen oder Pins. Python 3.11 Standardbibliothek und Node 22, keine GPU nötig.
- Lokaler vollständiger Checkout und Tests nicht durchgeführt; Änderungen über GitHub Git-Objekte, CI maßgeblich.
- Rückbau: WP01-Aufgabencommits revertieren bzw. PR nicht mergen; Merge der Koordinatoränderungen nicht rückgängig machen. Schalter aus deaktiviert RT, keine persistierten Daten durch WP01.

Nachstellen: python -m unittest discover -s tests -v; node --test tests/realtime/rt_contracts.test.mjs; Beispiele unter docs/realtime/examples.

## Übergabe

Fertig: WP01-Verträge, Mock, Schalter, Beispiele und Tests. Offen: A0 muss entscheiden, ob die unveränderten Bestands-CLIs als Unterprozess-Ausnahme zu Abnahme 5 akzeptiert oder separat aus sirens/ verschoben werden. Die Fehlerausgaben der beiden bisherigen CI-Läufe stehen oben. Nächster Schritt: die Alt-Worker-Ausnahme beurteilen; keine Änderung am Bestand ohne Freigabe. Keine Hardwaremessung erforderlich.

Maßgeblicher Code-CI-Lauf: [Tests 45452535991](https://github.com/ccogit/Sirens/actions/runs/45452535991), [Job 138653205523](https://github.com/ccogit/Sirens/actions/runs/45452535991/job/138653205523), Head 62886571, Python 3.11/Node 22 (CI-Konfiguration). Tests und Job abgeschlossen mit success:

```
python -m unittest discover -s tests -v
Ran 101 tests in 15.292s
OK (skipped=4)
```
Die vier Skips sind die aus WP00 bekannten optionalen Bestandstests. Die abschließende reine Dokumentations-/Integrationsänderung wird erneut von derselben PR-CI geprüft. Der PR bleibt wegen der ausdrücklich dokumentierten Abweichung von Abnahmepunkt 5 eine Übergabe an A0, nicht ein Draft.
