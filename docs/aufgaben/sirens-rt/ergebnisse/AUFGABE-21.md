# AUFGABE-21 – SPIKES-MESSPFADE (KETTE-13)

Status: **Teilstand / Übergabe, nicht abgenommen**. Alle Gates unverändert `nicht_gemessen`. PR #17 gegen integration/sirens-rt, keine Änderung an Register oder Board.

## Umsetzung und Belege

| Abnahmepunkt | Ergebnis / Beleg |
|---|---|
| RoFormer / DrumSep | RoFormer: Projektpin, direkte Paketpins inkl. Torch/Torchaudio 2.7.1+cu128, Gewichtsmanifest mit exakten Bytes, SHA-256 und MIT-Quellen; expliziter Installer mit Bestätigung, isoliertem venv und atomarer Prüfung; experimenteller MSST-Fixture-Messpfad mit sicherem State-Dict-Loader und gemeinsamem Runner. DrumSep: Quellen und Sperre dokumentiert, keine vollständige Gewichtsfreigabe. |
| SAM Audio | Projekt- und Git-Abhängigkeitspins recherchiert; offizieller Gewichts- und Lizenznachweis, T5-Safetensors-Hash. Manifest enthält offene Werte statt erfundener Daten. Bestehender experimenteller Messpfad unverändert, Installer gesperrt. |
| Stable Audio 3 | Offizielle Modell- und Encoderdateiliste, Größenordnungen, Community- und Gemma-Lizenznachweise, Manifest mit offenen Hashes; bestehender experimenteller Messpfad unverändert, Installer gesperrt. |
| Übrige Kandidaten | Nicht bearbeitet, da Pflichtreihenfolge und Pflichtkandidaten noch nicht abgeschlossen. |
| Offline-Tests | Neuer AST-Test gegen explizit unsichere Loader, Mock-Tests für Hashabweichung, Download/Re-use, Sperre und fehlenden Schalter. Bestehende Dry-Run-Suite erfasst RoFormer. [CI auf e2e119e](https://github.com/ccogit/Sirens/actions/runs/45453968306) erfolgreich; dieser Stand enthält RoFormer und die neuen Tests. Finaler PR-Head separat prüfen. |
| Kopierbare Befehle / Runner | benchmarks/spikes/README.md mit RoFormer-Installations-, Dry-Run- und Messbefehlen. Ausgabe gemäß vorhandenem Runner; RTF auf Ebene der gesamten Inferenz, noch kein interner Block-RTF. |
| Tatsächliche Modellmessung | Nicht geprüft: kein lokaler vollständiger Checkout mit Python 3.11/CUDA-Zielhardware, keine Modellgewichte oder Zugangsdaten. Keine behaupteten Messwerte. |
| Umfang / Sicherheit | Ausschließlich eigene Spike-Dateien, Test und Ergebnisdatei. Keine Gewichte, Musik, Secrets oder Änderungen im Hauptprozess. |

## Übergabe

**Fertig:** RoFormer-Versuchspfad mit verifiziertem Gewichts-Pin und sicheren Offline-Tests, Quellenberichte und Gewichtsmanifeste für alle drei Pflichtkandidaten. Branch gepusht, ein PR #17.

**Offen:** Reproduzierbarer transitiver Paketlock (RoFormer aktuell nur direkte Pins), tatsächliche MSST-Kompatibilität inklusive Modellkonfiguration und State-Dict, DrumSep-Gewichtsfreigabe, alle internen Blockmesswerte. SAM und SA3 benötigen vollständige, authentifiziert gelesene Gewichts-/Konfigurationsrevisionen, Hashes, Größen, Paketlocks, freigegebene Installer und abgesicherte Inferenz. Für SAM optionale Ranker/Span-Prädiktoren deaktivieren und lokalen T5-Encoder explizit konfigurieren; für SA3 zusätzlich T5Gemma-Encoder und Tokenizer prüfen. Restliche Kandidaten nach den ersten drei. Kein Gate setzen.

**Nächster Schritt:** 1. RoFormer im isolierten Windows-venv gemäß Spike-README installieren; transitive Abhängigkeiten einfrieren und CPU/CUDA-Inferenz verifizieren; interne Blöcke instrumentieren. DrumSep-Lizenz und SHA/Bytes vom Gewichtsinhaber bestätigen. 2. SAM-Hub-Zugang durch berechtigte Person mit akzeptierter Lizenz; vollständige Hashliste und kompatible torchcodec-/CUDA-Versionen erstellen. 3. Stable Audio 3 gleichermaßen inkl. Gemma-Lizenz und Encoder; Offline-Loader verifizieren. Danach verbleibende Modelle. Keine pauschale Freigabe aufgrund des Dry-Runs.

**Fehlerausgabe / Blockaden:** Offizielle SAM-Checkpoint- und Config-Blob-Abfragen: HTTP 401 Unauthorized; offizieller Stable-Audio-3-Blob model.safetensors: HTTP 401 Unauthorized. DrumSep-Release-Datei: Metadatenabruf ohne verifizierbaren SHA/Größe; separate Gewichtslizenz nicht eindeutig belegt. Kein reproduzierbarer Voll-Lock oder Hardwarelauf innerhalb dieses Durchlaufs; kein CI-Fehler im zuletzt nachgewiesenen RoFormer-Lauf. Keine Zugangssperren umgehen.

**Risiken:** Ungetestete transitive Abhängigkeiten bzw. Windows/CUDA-Kompatibilität, zusätzliche implizite Fremdmodellbezüge in upstream SAM/SA3, nicht gemessene Blocklatenzen und VRAM, Lizenzbedingungen für konkrete Nutzung. RoFormer-Installer ist ausdrücklich nur ein lokaler Versuch; kein vollständig abgenommener Messpfad. Die verbliebenen Installer bleiben gesperrt.
