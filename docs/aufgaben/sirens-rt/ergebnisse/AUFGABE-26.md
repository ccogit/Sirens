# AUFGABE-26 – Produktintegration Teil 2 (WP17) – ÜBERGABE

Depends-on: WP03/04/05/06/09/10/14/16/17 (KETTE-41 gemergt). WP08-Dateijob und WP12-Pads
laufen parallel und wurden nicht verändert. Basis nach zwei echten Zweieltern-Merges:
30999fa53095a75480c7785fc872c7aee9485183. Ziel integration/sirens-rt; kein Force-Push.

## Umgesetzt

- Panic/Verlassen: Generationsprüfung vor und nach HTTP-Befehlen, sodass eine verspätete
  Play-Antwort keine lokale Audiowiedergabe startet und wartende Befehle verworfen werden.
  Aufnahmestart und Export prüfen die Generation; eine während des Stopps angelegte
  Aufnahme wird geschlossen. Bereits ausgeführte HTTP-Befehle können nicht rückgängig
  gemacht werden; die Sitzung wird anschließend geschlossen.
- HTTP-Referenzablauf: synthetischer WAV-Cache im temporären Testverzeichnis über den
  bestehenden StemDienst, Mock-Play, Gain-Pad (keine KI), Bypass, Aufnahmeblock,
  Sitzungs-JSON-Export, Close, Beendigung von Worker und Sidecar und unveränderter
  Originalhash. Aufnahme-PCM ist eine Testfixture und kein Browser-Hörnachweis.
- GPU-Profile: die vorhandenen Registry-Profile Eco/Performance/Neural/Training/Render
  begrenzen im GPUManager zusätzlich zum Supervisor-Limit die gleichzeitig vergebenen
  Leases (0/1/2/1). VRAM-Reserve, gemessene Peak-Anforderung und Telemetrieprüfung bleiben
  bestehen. Downgrade bei zu vielen aktiven Leases wird mit busy_gpu abgelehnt, statt
  Audio ungefragt zu unterbrechen. Standard Performance. Profil im Dienstspeicher,
  keine Persistenz über Neustart. Supervisor-Queue-Limits sind nicht dynamisch umgestellt.
- Separate Integrationsadresse GET/POST /api/rt/v1/profile, POST ausschließlich
  {"profile":"Neural"} bzw. anderer erlaubter Name. Host-/Origin-/JSON-/Feature-Flag-
  Prüfung; GET ohne Initialisierung. Bestehende Vertragsantworten, routes.py und
  WorkerSupervisor unverändert. Lab Shell lädt und setzt das Profil; Mock bleibt CPU,
  Modellfreigaben ändern sich nicht. Das vorhandene Live-Lab-Visual erhält für Neural,
  Eco und Training/Render die vorhandene Auflösungs-/Bildraten-Drosselung.
  Profil wird beim Mount/Statuspoll der RTX-Shell synchronisiert; eine frisch geöffnete
  Legacy-Pult-Ansicht ohne vorherigen RTX-Mount übernimmt es noch nicht automatisch.

## Abnahme

| Punkt | Beleg | Stand |
|---|---|---|
| 26.1 / 17.2 Claude-Konkurrenz | tests/realtime/test_integration_26.py: Bestands-CUDA-Sperre mit Flag an und aus; tests/realtime/test_gpu_profile_26.py: keine Lease ohne Telemetrie. | Teilweise; alte Sperre bewusst nicht gelockert. Claude-Peak, gemeinsam verwaltete Legacy-Jobs, Start in beiden Richtungen und automatische Claude-Folgeläufe offen. |
| 26.2 Profil und Panic | tests/realtime/test_gpu_profile_26.py: Limits, Downgrade, Supervisor-Zusatzlimit, unbekannte GPU; test_integration_26.py: HTTP-Profile/Origin/Flag; integration_26.test.mjs: Drosselungsprädikat, API und verzögerte Play-Antwort. | Teilweise; keine Browser-Messung, Panic für noch nicht integrierte Werkzeuge nicht belegbar. Profil-Commit 33810a3 zum letzten Abruf CI in_progress. |
| 26.3 / 17.1 Ablauf | tests/realtime/test_integration_26.py und integration_26.test.mjs: Cache-Stem, Gain-Pad, Aufnahme/Export über HTTP; Mock-Controller und Core-Double, Panic und Cleanup. | Teilweise; kombinierter HTTP-Test grün im Lauf 45461319761 und 45461459966; kein durchgehender echter Browser-/AudioWorklet-Test und kein DSP-/Performance-Tool in diesem Ablauf. |
| 17.3 Negativ | Bestehende Capability-Gates unverändert; Test Flag, Origin, konservative CUDA-Sperre. | Nicht freigegebene Modelle bleiben gesperrt; keine neue Freigabe. |
| 17.4 Hardware | Bestehende Messpfade WP09/WP14 und benchmarks/integration/report.py aus WP17. | Nicht gemessen. Keine neuen Hardware- oder Hörwerte. |
| 26.4 / 17.5 CI | Lauf 45461319761 (1411c91) success; 45461459966 (8fd963a) success. Profil-Commit 33810a3: Lauf 45461650301 beim letzten Abruf in_progress. | Kein bestätigtes Grün des abschließenden Gesamtstands zum Schreibzeitpunkt. |

Nachstellen: `python -m unittest discover -s tests -v` (Python 3.11, Node 22).
Node einzeln: `node --test tests/realtime/integration_26.test.mjs`.
Sicht-/Hörprotokoll: `python -m benchmarks.integration.report <baseline.json> <beobachtungen.json> <ergebnis.json>`;
`python -m benchmarks.result <ergebnis.json>`. WP14:
`node benchmarks/performance/render.mjs <neues externes Verzeichnis>`, Hörprüfung und
`python benchmarks/performance/report.py <baseline.json> <render.json> <neue Ergebnisdatei.json> --note "drum-double: ..."`.
Keine Audiodateien einchecken. G3 je Funktion separat durch den Koordinator messen.

## Abweichungen, Versionen und Risiken

- Keine neuen Fremdprojekte, Pins, Gewichte oder Lizenzen. Python 3.11 Standardbibliothek,
  ES-Module, Node 22 für Tests. Zielhardware RTX 5080/16 GiB, Windows 11, Browser mit
  AudioWorklet. Tatsächliche Latenz, VRAM, Bildrate und Klang: nicht gemessen.
- Das globale Profil deckelt Leases, aber Supervisor-Profile/Queue-Konfiguration bleiben
  zusätzlich wirksam (Neural erlaubt höchstens zwei, garantiert nicht zwei). Alte
  CUDA-Sperre bleibt bis zu einer belastbaren globalen Admission-Policy unverändert.
- Kein Einbau ungeprüfter DSP-/Performance-Prototypen. WP09/WP14-Hooks, Parameter-
  Automation, gemeinsame Presets und durchgehende UI-Aufnahme/Export bleiben offen.
- Die bestehende Referenzintegration ist kein vollständiges Replay. Der neue HTTP-Test
  benutzt synthetisches Aufnahme-PCM und bestätigt keine Tonausgabe. Panic kann einen
  laufenden HTTP-Request nicht abbrechen; er verhindert dessen lokale Wiedergabefolge.
- Profile/Transport/Panic: die relevanten bereits gemergten Dateien GPUManager, Lab
  Shell und deren API wurden aufgrund des ausdrücklichen Umfangs von AUFGABE-26
  angepasst; keine Dateien der parallel bearbeiteten Ketten, Katalog-API, Register
  oder Board absichtlich geändert. Upstream-Registeränderungen nur gemergt.

## Übergabe

**Fertig:** Mock-HTTP-Referenzablauf, Panic-Race-Regressionen, globale Profilobergrenze,
Profil-HTTP-Adresse/Bedienung, Drosselungsanbindung und Tests. Zwei CI-Läufe vor dem
Profil-Commit grün.

**Offen:** Claude-Konkurrenz vollständig und konservativ über GPUManager regeln;
gemessene Peak-Budgets und Lebenszyklus für Legacy-CUDA/Claude (einschließlich
automatischer Folgeläufe) abgleichen; Profile mit Supervisor-Queues und allen
Visualisierungen verbinden; WP09/WP14-Hooks unter Gate-Bedingungen bedienen;
Automation und Presets über alle Module; vollständiger Browser-E2E inklusive
echtem Recorder, Panic und Lifecycle, G3 je Funktion. Keine vollständige
WP17-Abnahme oder Freigabe behauptet.

**Nächster Schritt:** CI des letzten Commits abrufen und ggf. beheben. Die GPU-Policy
mit Koordinator und den parallelen Worker-Ketten abstimmen: keine unbekannten
VRAM-Peaks erfinden, keine fremden Prozesse beenden. Danach WP09/WP14-Steuerung
unter bestehenden Gates und automatisierte UI-/Hardware-Prüfung abschließen.

**Fehlerausgabe/Blockade:** Lokaler vollständiger Checkout scheitert mit
`fatal: unable to access 'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com`.
GitHub-API-Commits/Push/PR funktionieren; lokale Gesamtprüfung nicht ausgeführt.
CI 45461319761 und 45461459966 erfolgreich. Kein bestätigter CI-Fehler des letzten
Stands zum Schreibzeitpunkt; CI 45461650301 noch in_progress. Der Restumfang
konnte in der verfügbaren Bearbeitung nicht vollständig umgesetzt werden.

**Rollback:** PR nicht mergen oder ausschließlich die AUFGABE-26-Änderungen revertieren;
kein Force-Push. SIRENS_RT_ENABLED=0 erhält den Bestand. Getrennte Aufnahmen und
Exports nicht automatisch löschen. Keine Änderungen an parallelen Branches/PRs.
