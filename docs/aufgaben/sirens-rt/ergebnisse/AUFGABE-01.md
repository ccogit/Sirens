# AUFGABE-01 – Verträge und Architektur (WP01)

WP00 gemergt; Branch extern/KETTE-11, [PR #8](https://github.com/ccogit/Sirens/pull/8) gegen integration/sirens-rt. Erster Commit 88ec4416 direkt gepusht, dann Draft-PR eröffnet. Integrationsstand 9e1ae563 per Merge 1cf7989f übernommen; Registeränderungen stammen vom Koordinator.

## Umsetzung

Architektur, Protokoll, Adapter, Sicherheit und fünf ADRs in docs/realtime; 13 JSON-Schemas mit Beispielen für neun API-Adressen, zwei PCM-Hex-Referenzen; Python-Zustandsautomaten, Befehls- und Schema-Prüfung, Pfade, PCM-Codec, Gain/Delay-Mock; JS-PCM und UI-Mock. Schalter SIRENS_RT_ENABLED standardmäßig aus, optional SIRENS_RT_DIR und SIRENS_RT_MOCK. Einzige neue Weiche im bestehenden Server, nur GET capabilities implementiert, übrige RT-Adressen unavailable. Board nur WP01-Zeile. Keine echten Worker, kein Sidecar, keine Oberfläche.

## Abnahme

| Nr. | Beleg | Stand |
|---|---|---|
| 1 | realtime.test_rt_contracts.Schemas: alle 13 Schemas, positive/negative Beispiele, 9 HTTP-Paare, Capability-Parität | erster Code-CI-Lauf bestanden |
| 2 | PCM.test_fixtures_and_roundtrip, PCM.test_invalid und rt_contracts.test.mjs: beidseitig identische Hex-Referenzen, BigInt, Fehlerfälle | erster Code-CI-Lauf bestanden |
| 3 | Contracts.test_transitions, test_commands: alle Zustandspaare, alte Epoch und ungültige Befehle | erster Code-CI-Lauf bestanden |
| 4 | HTTP.test_switch_and_security sowie unveränderte Bestandstests: 503/200, Schema, Origin/Host | erster Code-CI-Lauf bestanden |
| 5 | Contracts.test_stdlib_imports_recursively: AST rekursiv, keine neuen Fremdimporte; Alt-DSP-Ausnahme siehe unten | korrigiert, erneute CI ausstehend |
| 6 | Mock.test_gain_delay: samplegenauer Gain/Delay über Blockgrenzen, Lifecycle und Determinismus | erster Code-CI-Lauf bestanden |
| 7 | python -m unittest discover -s tests -v | erneute CI ausstehend |

Erster Code-CI-Lauf [45452123740](https://github.com/ccogit/Sirens/actions/runs/45452123740), Head da8f1362: 101 Tests, 1 Fehler, 4 bestehende Skips. Fehler: test_stdlib_imports_recursively, AssertionError: numpy not found … sirens/kick_dsp.py. Kein neuer RT-Test außer diesem Importinventar fehlgeschlagen. Korrektur: Der unveränderte Kick-DSP ist ein eigenes CLI, das kicktausch.py per subprocess.run startet. Die vorhandenen Imports numpy, scipy, soundfile ausschließlich in diesem Modul sind explizit zugelassen; alle übrigen Fremdimporte sowie Hauptprozess-Imports dieses CLI bleiben verboten. Das strikte wörtliche Kriterium „kein Modul unter sirens/“ ist wegen des Altbestands nicht vollständig erfüllt; Verschiebung des Bestands-CLI wäre außerhalb WP01 und potenziell regressiv.

## Entscheidungen, Grenzen, Risiken

- PCM-Header 32 Byte, reservierte Flags 0, Rate 8–192 kHz, Payload bitgetreu (Audio-Empfänger muss nicht-endliche Samples stummschalten); Frame uint64 im Binärtransport, JSON-Zahlen bis 2^53−1. ID 32 Hexzeichen, Sequenz uint32. Sicherheitslimits und Heartbeat sind initiale Vertragswerte, keine gemessenen Leistungswerte.
- JSON-Schema-Validator unterstützt nur das eingesetzte Schlüsselwortprofil, kein allgemeiner Draft-2020-12-Validator. UI-Mock simuliert sofortige Jobfertigstellung, keinen echten Scheduler, keine Zeit/Audio. Capability Mock offline, keine GPU-Freigabe.
- Zielhardware **nicht gemessen**: WP01 liefert nur CPU-Verträge, kein Leistungs-Gate; spätere WP03/04/06 und Koordinator messen. Keine fremden Projekte, Gewichte, zusätzlichen Lizenzen oder Pins. Python 3.11 Standardbibliothek und Node 22, keine GPU nötig.
- Lokaler vollständiger Checkout und Tests nicht durchgeführt; Änderungen über GitHub Git-Objekte, CI maßgeblich.
- Rückbau: WP01-Aufgabencommits revertieren bzw. PR nicht mergen; Merge der Koordinatoränderungen nicht rückgängig machen. Schalter aus deaktiviert RT, keine persistierten Daten durch WP01.

Nachstellen: python -m unittest discover -s tests -v; node --test tests/realtime/rt_contracts.test.mjs; Beispiele unter docs/realtime/examples.
