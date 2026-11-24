# AUFGABE-17 – WP17 Produktintegration und UX (ÜBERGABE)

Depends-on: WP03, WP04, WP05, WP06, WP08, WP09, WP10, WP14, WP16.
Basis integration/sirens-rt 8623758c46a278645fea51db72543c859c558435.
KETTE-26 (f96e68e85d1e879142849392f319cd2591dd6dce) als echter Zweieltern-Merge
cb021716bcd3954676173450239cd08c844698ec eingebunden; deren Dateien nicht geändert.
Beide Upstream-Refs vor Abschluss erneut geprüft, unverändert. Kein Force-Push.

## Umgesetzt

- Katalogsuche im vorhandenen Lab, aktuelle Quelle bleibt bei Filterung wählbar; keine Änderung der Katalog-API.
- Bereits vorhandene Demucs-Cache-Stems einzeln im bestehenden Mock-Audiopfad: Auflösung ausschließlich durch
  StemDienst.audiodatei, erneute Auflösung beim Laden, kein Client-Cachepfad. PCM16-WAV mono/stereo mit
  44,1/48 kHz, maximal 120 Sekunden, lineare Offline-Interpolation auf 48 kHz bei Bedarf.
  Kein neuer Trennlauf, kein zusätzlicher AudioContext, keine Originaländerung.
- Explizites Mock-Pad stellt Gain 0,5 und Wet 100 % ein (kein generativer Klang). Panic und Stop
  bleiben bei vorhandenem Controller auch im API-Fehlerzustand erreichbar.
- Aufnahme-Assets werden für den Sitzungsexport übernommen; sitzungsgebundener Quellhash über
  GET sessions/{id}/export-source (kein neuer Pfadparameter). Expliziter JSON-Export über vorhandene
  Export-Route, mit begrenztem Befehlsverlauf, Preset-/Modellkennzeichnung, Quelle und Aufnahme-IDs.
  Aufnahme zuvor stoppen, Export vor Session-Stop. Kein vollständiges Replay.
- Nicht freigegebene Modelle und DSP-/Performance-Prototypen ausdrücklich benannt, nicht aktivierbar;
  RoFormer als G1-offline-freigegeben, aber nicht produktiv angebunden gekennzeichnet.
- Sicht-/Hörprotokoll unter benchmarks/integration/ mit Konverter in gemeinsames Ergebnisformat.
  Keine automatisch behauptete G3-Freigabe.

## Abnahme

| Punkt | Beleg | Stand |
|---|---|---|
| 1 | tests/realtime/product_integration.test.mjs: Suche, Exportstruktur, sitzungsgebundene Anfrage. tests/realtime/test_product_integration.py: HTTP Flag/Origin/Quellhash und begrenzte Cache-Stem-Auflösung mit PCM-Fixture. Bestehende lab_shell.test.mjs prüft Mount/Pause/Destroy, Panic und Listener/Timer; Mock-Pad und Recorder-/Export-UI im echten Browser noch nicht durchgehend geprüft. | Teilweise. Durchgängiger HTTP-/Node-E2E mit allen WP17-Schritten und realem AudioCore fehlt. |
| 2 | Bestands-CUDA-Sperre unverändert. Kein unbekannter Claude-VRAM-Peak als Messwert angenommen. | Offen: globale Policy, beide Startrichtungen (auch automatisch), GPU-Profile, Visual-Drosselung und Tests. |
| 3 | Capability-Hinweise, deaktivierte Optionen, bestehende Flag-/Origin-Tests; neuer HTTP-Flag-Test. Keine neuen Modell-Downloads oder Modellimporte. | Teilweise; vollständige Negativ-/Legacy-Sichtprüfung offen. |
| 4 | benchmarks/integration/README.md und report.py; tests/realtime/test_product_report.py. Vorhandene Messpfade für WP04/06/08/09/14/16 weiterverwenden. | **Nicht gemessen**; G2 und G3 nicht freigegeben. |
| 5 | CI-Läufe 45458000502 (Merge), 45458278201 (Suche/Export), 45458458134 (Pad/Protokoll) success. Lauf 45458621149 (Cache-Stems, Commit ad54ecab349ba819f6c71adea3468a74b82c5f30) zum letzten Abruf in_progress. | Kein grüner Nachweis für letzten Gesamtstand. Board gemäß KETTEN.md nicht geändert. |

Nachstellen: `python -m unittest discover -s tests -v` (Python 3.11, Node 22).
Sicht-/Hörprüfung: `python -m benchmarks.integration.report <baseline.json> <beobachtungen.json> <ergebnis.json>`;
`python -m benchmarks.result <ergebnis.json>`. Alle Beobachtungen nach README erfassen. Der Konverter setzt
Gate nicht_gemessen und keine erfundenen Zahlen. G3 je Funktion separat messen.

## Abweichungen, Versionen und Risiken

- WP08: Die Registry-/Dateijob-Anbindung für RoFormer fehlt; WP08 meldet fehlenden kompatiblen Transport
  (Supervisor-IPC nur PCM bis 1 MiB, keine frei wählbaren Dateijob-Parameter). Erforderlich sind
  fester Offline-Runner, Installations-/Probeprüfung, GPU-Lease mit belastbarem Peak, Prozessbaum-Abbruch
  und sichere Ausgabe. workers/separation/ und stem_adapter.py nicht ändern. RoFormer bleibt gesperrt.
- WP09: bestehender DSP-Core-Hook bleibt standardmäßig aus; vollständige Steueroberfläche und G3 offen.
  WP14: Scheduler, Drum-/Crossover-/Acid-Controller und manuelle Klassifikation nicht produktiv eingebaut.
  Nicht freigegebene Prototypen dürfen nicht aktiviert werden. WP10-Quantisierung und Parameter-Automation
  sowie MIDI optional offen. Kein generatives Pad.
- WP16: Export enthält Befehlsverlauf und aktuelle Wet/Bypass-Metadaten, nicht samplegenaue
  Client-Automation; serverseitige automatisch ausgelöste Befehle sind nicht vollständig protokolliert.
  Aufnahme-/Export-Ablauf und tatsächliche Quelle/Cache-Ausrichtung mit Browser prüfen. Der begrenzte
  lineare Stem-Resampler ist Referenz, kein Qualitätsnachweis; kein gleichzeitiger Multi-Stem-Mix.
- Keine neuen Fremdkomponenten, Pins, Code- oder Gewichtslizenzen; WP08 erbt MSST
  1523206d12a521bdb20673726562524cf0f9635b (MIT), Gewicht SHA-256
  87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e (MIT laut WP08).
  Demucs-Bestand 4.0.0, Gewichte separat prüfen. RTX 5080/16 GiB und Browser mit AudioWorklet
  sind Zielhardware; tatsächlicher Peak, Klang, Latenz und Lifecycle nicht gemessen.
- Neue, separate Integrationsadressen export-source und cached-stem; v1-Vertrag/Schemas unverändert.
  Sicherheits-/Hashprüfung beim Replay weiterhin offen. Bestehende Katalogdateien und Katalog-API unangetastet.

## Übergabe

**Fertig:** Abhängigkeit integriert, vier gepushte Implementierungs-/Merge-Commits; Suche,
Mock-Pad, Cache-Stem-Referenzpfad, Exportanbindung, Sicherheits-/Hilfstests, Sichtprüfungsprotokoll.
Drei frühere CI-Läufe grün.

**Offen:** WP17 nicht abgenommen. Insbesondere RoFormer-Registry/Dateijob, GPU-Policy und
Claude-Konkurrenz, GPU-Profile und Visual-Drosselung, WP09/WP14-Bedienung, Automation,
vollständige E2E- und Zielhardwareprüfung. Keine vollständige Produktintegration behauptet.

**Nächster Schritt:** CI des aktuellen PR prüfen; Cache-Stem-/Export-Pfad korrigieren, falls nötig.
Dann GPU-Policy und RoFormer-Dateijob mit gemessenem Budget und sicherer Prozesslebensdauer
integrieren, WP09/WP14-Hooks unter Gate-Grenzen abschließen. Durchgehende Mock-HTTP-/Node-Tests
und G3-Sicht-/Hörprüfung ausführen. Erst nach vollständiger Abnahme freigeben.

**Fehlerausgabe/Blockade:** lokaler Git-Zugriff scheitert mit
`fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
Pushing über GitHub-API erfolgreich. Lokale Gesamtprüfung nicht durchgeführt. Kein CI-Fehler
in den drei abgeschlossenen Läufen; jüngster Lauf zum letzten Abruf noch nicht abgeschlossen.
Die Aufgabe ist im verfügbaren Bearbeitungsumfang nicht vollständig umgesetzt.

**Rollback:** PR nicht mergen bzw. nur WP17-Commits revertieren, kein Force-Push.
KETTE-26 unabhängig durch Koordinator prüfen/mergen. SIRENS_RT_ENABLED=0;
getrennte RT-Aufnahmen/Exports nicht automatisch löschen. Register und Board unverändert.
