# AUFGABE-20 – Rollout / WP20 / KETTE-52

## Umsetzung und Abnahme

| Punkt | Beleg / Status |
|---|---|
| 1 | scripts/rt-install.ps1: DryRun vor Programmausführung, ausdrücklicher Schalter und Zustimmung, feste Zielordner mit Markierung, ReparsePoint-Schutz. tests/realtime/test_rollout.py prüft Textvertrag und bei vorhandenem PowerShell DryRun. Zusätzlich temporärer Besitztest (DryRun erhält Markierung, unmarkierter Ordner bleibt erhalten, markierter Ordner wird entfernt). Native Windows-Prüfung noch offen. |
| 2 | Produktcode unverändert; vorhandene Legacy-Tests und test_integration_26.py (Flag, CUDA-Sperre) laufen in PR-CI. Manueller Bestandsstart ohne Worker nicht gemessen. |
| 3 | benchmarks/rollout.py und docs/realtime/runbook.md: reproduzierbarer Aufruf, Exitcode/Baseline und validiertes Benchmark-Format, Messwerte null. Frische Zielinstallation nicht gemessen. G4 nicht gemessen (Koordinator). |
| 4 | Zwischenstand 33d419b8: PR-CI Run 45486937159 erfolgreich. Endstand bei Niederschrift nicht bestätigt. Board unverändert gemäß KETTEN.md. |

Installationsanleitung, Lizenzmatrix, Handbuch, Runbook und RC-Changelog
unter docs/realtime/. Keine neue Fremdabhängigkeit im Hauptprozess, keine
neuen Modell-Pins, keine Gewichte. Versions-/Lizenzmatrix in lizenzen.md;
Ziel Windows 11, RTX 5080, Python 3.11, Node 22, Magenta separat WSL2.
Nachstellen: python -m unittest discover -s tests -v,
scripts/rt-install.ps1 -DryRun; Hardwareaufruf in runbook.md.

## Abweichungen / Risiken

- Kein vollständiger transitiver Paket-Hash-Lock für die meisten Worker im
  Bestand. DEMON-G1 dokumentiert fehlendes Upstream uv.lock; automatischer
  Rollout verweigert. Andere unvollständige Locks standardmäßig gesperrt;
  ausdrücklich akzeptierter Entwicklungsversuch ist keine RC-Installation.
  SAM benötigt externes geprüftes Wheelhouse, Lock und Receipt.
- Magenta-Installation und Entfernung separat in WSL; eigener zentraler
  WSL-Eigentums-/Plattenplatzcheck fehlt. Ressourcen-Mindestwerte vom
  Betreiber anhand geprüfter Größen zu setzen; GPU 0 wird geprüft.
- Lokaler Checkout nicht möglich: fatal: unable to access
  'https://github.com/ccogit/Sirens.git/': Could not resolve host: github.com.
  Keine lokale Vollsuite oder native Windows-Ausführung.
- Markierung verhindert Übernahme fremder Ordner; lokaler gleichzeitiger
  Dateisystemumbau während Prüfung/Löschung nicht unterstützt.
- G4 ist Merge-Bedingung, keine Freigabe durch WP20. Kein Tag/Release/Merge.

## Rückbau

Dienst stoppen, RT-Flag aus, eigene markierte Umgebungen gezielt entfernen;
Musik, Sitzungsdaten, Bestandsumgebungen und fremde Caches behalten.
Nur WP20-Commits revertieren.

## Übergabe

**Fertig:** Rollout-Einstieg, CPU-Textvertrag und bedingter DryRun-/Besitztest,
Installationsbericht, Handbuch mit G1-Belegen, Lizenzmatrix, Runbook,
Changelog; ein Draft-PR #53, Zwischenstand-CI grün.

**Offen:** vollständige verifizierte Wheel-Hash-Locks und DEMON-Installationspfad,
WSL-Eigentums-/Ressourcenprüfung, tatsächliche Windows-DryRun-/Löschprüfung,
frische Installation, Bestands-Sichtprüfung ohne Worker, Endstand-CI und G4.

**Nächster Schritt:** Koordinator prüft Locks/Quellen, führt Windows-Tests
und frischen Installationsversuch nach Runbook aus, behebt etwaige CI-Fehler,
ergänzt G4-Messung. RC erst nach vollständiger Abnahme.

**Fehlerausgabe:** lokaler Git-Checkout: Could not resolve host: github.com.
DEMON: Upstream uv.lock fehlt am Pin (G1-Bericht). Kein bekannter
CI-Fehler im bestätigten Zwischenstand. Endstand bei Niederschrift nicht geprüft.
