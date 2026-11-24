# AUFGABE-02 – Modell-Spikes (WP02)

**Status: Teilstand / Übergabe, nicht abgenommen.** Basis: AUFGABE-00 gemergt; KETTE-12, PR #9 gegen integration/sirens-rt. Alle Gates bleiben `nicht_gemessen`. Keine Zielhardware verfügbar; keine eigene Leistungszahl oder Freigabe.

## Umsetzung

- Zehn Quellenberichte unter `benchmarks/spikes/<kandidat>/BERICHT.md`, mit Links und geprüften Quell-Commits, getrennten Lizenzangaben und Risiken, Betriebsmodus-Hypothesen, Ausweichvarianten und Messplänen. MSST und pymss sind gemeinsam erfasst.
- Übersicht mit Messreihenfolge und Abhängigkeiten der Folgeketten; nur eigene WP02-Zeilen im Board bearbeitet.
- Standardbibliothek-Messhilfe `common.py`, gemeinsamer Runner `runner.py` und Tests; drei experimentelle Inferenzpfade (RAVE, Stable Audio 3, SAM Audio). Synthetische Fixtures, CPU/GPU-Auswahl, kalte/warm wiederholte Aufrufe, Seeds, RTF/Perzentile, Prozess-/Gesamt-GPU-Sampling, lokales Ergebnis und Hörprobe. Keine Modellimporte in sirens/.
- Zehn isolierte Installations-/Rückbau-Skripte. Der Bezug ist bewusst noch gesperrt, auch mit -ModelleLaden, bis konkrete Abhängigkeits- und Gewichtspins, Größen und Lizenzen geklärt sind. Kein unkontrollierter Download.
- Integrationsstand wurde per Merge übernommen; keine eigenen Änderungen am Register.

## Abnahmebelege

| Punkt | Stand | Beleg / Rest |
|---|---|---|
| 1 | Teilweise | Zehn Berichte vorhanden; Quell-Commits verlinkt. Einzelne Gewichtslizenzen, Dateigrößen, Hashes, OS-/Blackwell-Nachweise, genaue Abhängigkeiten und Latenzparameter offen. |
| 2 | Teilweise | Tests für Perzentile, RTF, Ergebnisvalidierung, Dry-Run und fehlende venv der vorhandenen Messpfade. CI [45452119064](https://github.com/ccogit/Sirens/actions/runs/45452119064) erfolgreich auf cc4962ca273ad74f2f8ad0fdce187550d9e4914f. Ergebnisvalidator aus WP00 benutzt; unabhängige JSON-Schema-Prüfung, echte Inferenz und vier fehlende Modellpfade offen. |
| 3 | Teilweise | Texttests der zehn install.ps1 auf Schutzschalter und keine unisolierten Installationen; kein Download enthalten. Vollständige gepinnte Installation und erfolgreicher Modellbezug fehlen. |
| 4 | Erfüllt im gelieferten Stand | Board, Übersicht und Ergebnisobjekte: `nicht_gemessen`; Angaben Dritter in Berichten gekennzeichnet. Keine Messresultate erfunden. |
| 5 | Zwischenstand grün | CI [45451823282](https://github.com/ccogit/Sirens/actions/runs/45451823282) und [45452119064](https://github.com/ccogit/Sirens/actions/runs/45452119064) erfolgreich. Maßgeblich ist die CI des jeweiligen PR-Heads; keine lokale Gesamtsuite durchgeführt. |

## Übergabe

**Fertig:** Quellenrecherche und zehn Berichte im Teilstand, gemeinsame Messbasis, drei experimentelle Skripte, Schutz-/Rückbaugerüste, Board und Übersicht. Alles gepusht. Keine Gewichte, Musikdateien, Secrets oder Fremdquelltexte eingecheckt.

**Offen:** DEMON, Magenta, AFTER und RoFormer/DrumSep benötigen echte Inferenzskripte. Alle zehn Installationswege brauchen geprüfte feste Paketversionen; für Modellkandidaten Gewichtslizenzen, Größe und Hash sowie einen explizit bestätigten Bezug. Für die vorhandenen Pfade sind echte Modell-/API-Kompatibilität und Offline-Verhalten noch zu verifizieren; HF-Offline-Flags ersetzen keine Netzsperre auf Betriebssystemebene. RTF wird aktuell pro Inferenzaufruf und nicht pro internem Audioblock gemessen; Streaming-10-Minuten-Lauf, Dropouts, Steuerlatenz, optionale lokale Tracks und vollständige unabhängige Schema-Prüfung fehlen. VRAM-Sampling kann kurze Spitzen verpassen. Zielrechner, CPU/GPU-Vergleich und Hörproben nicht geprüft. Keine Gate-Freigabe.

**Nächster Schritt:** Zuerst RoFormer/DrumSep und SAM als Voraussetzung für KETTE-26/27; MSST nutzt im Original unsicheres `torch.load(weights_only=False)`, daher nur geprüfte sichere Gewichtsformate einsetzen. DEMON: gepinnte Session-/Stream-API aus docs/ACESTEP.md, keine Web-Demo mit implizitem Download. AFTER: gepinntes Audio-to-Audio-Notebook und lokaler vertrauenswürdiger Export. Magenta: JAX-CLI aus docs/inference.md separat prüfen (kein Torch-Pfad). Danach die bestehenden Pfade gegen die gepinnten realen APIs absichern, Gewichtsbezug mit expliziter Bestätigung implementieren, Tests erweitern und die aktuelle PR-CI auswerten. Erst anschließend den Koordinator auf Zielhardware messen lassen.

**Fehlerausgabe / Blockade:** Kein bekannter roter CI-Lauf auf dem geprüften Zwischenstand. Ein konkreter Upstream-Pfad `magenta_rt/cli.py` lieferte GitHub HTTP 404; dokumentierte JAX-CLI und Paket-Entrypoint vorhanden, tatsächliche Modulstruktur noch zu prüfen. Die Installer verweigern absichtlich den Modellbezug solange Pins und Rechte offen sind. Die Aufgabe ist im verfügbaren Bearbeitungsumfang nicht vollständig fertig geworden; dies ist keine Meldung eines erfolgreichen G1-Tests.

**Rückbau:** Je Spike `install.ps1 -Entfernen`; lokale Messausgaben unter benchmarks/results/local/ bei Bedarf separat löschen. PR nicht mergen, bevor offene Abnahmepunkte erledigt sind.
