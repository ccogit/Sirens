# K10 – Begriffe richtigstellen: Ketten bestehen aus Aufgaben

Nur Dokumentation, kein Code. Lies KETTEN.md (Abschnitt „Begriffe“ oben), README.md, PLAN.md, CONTRACT.md,
REUSE-AMM.md, alle `AUFGABE-K*.md` und `ergebnisse/*.md` in `docs/aufgaben/sirens-production/`.

## Begriffe (verbindlich, so auch im Werkzeug `ketten`)

- **Aufgabe:** kleinste Arbeitseinheit mit eigener Datei `AUFGABE-nn-KURZTITEL.md` (Ziel, Umfang, Abnahme).
  Aufgaben können voneinander abhängen oder unabhängig sein.
- **Kette:** eine oder mehrere Aufgaben in fester Reihenfolge; ein Branch, ein PR. Abhängigkeiten zwischen
  Aufgaben derselben Kette erledigt die Reihenfolge.
- **Abhängigkeit zwischen Ketten:** Spalte „Voraussetzung“ im Register.
- **Schnitt:** hohe Kohäsion innerhalb einer Kette (gleiche Dateien, eng aufeinander aufbauend), geringe
  Kopplung zwischen Ketten – maximal parallel, minimale Merge-Konflikte.

## Befund

Die Dateien `AUFGABE-K00-…` bis `AUFGABE-K08-…` beschreiben jeweils eine **Kette**; ihre nummerierten
Umfangspunkte („1. …“, „2. …“, bei K07 die Abschnitte „## 1.“/„## 2.“) sind die eigentlichen **Aufgaben**.
Das Register führt bisher jede Datei als eine einzige Aufgabe „K0x“. PLAN.md und die übrigen Dokumente nennen
K0–K9 abwechselnd „Kette“, „Auftrag“ oder „Team“.

## Umfang

1. Je bisheriger Datei `AUFGABE-K00` … `AUFGABE-K08` die Umfangspunkte in eigene Aufgabendateien
   `AUFGABE-nn-KURZTITEL.md` aufteilen, fortlaufend nummeriert ab `01` in Kettenreihenfolge (K00 → 01, 02 …).
   Regel: eine Aufgabe ist eine einzeln prüfbare Einheit mit eigener Abnahme; reine Unterschritte bleiben
   zusammen. K00 Umfang 3 ist bereits als K08 abgetrennt: in K00 nur 1–2 aufteilen. Je neuer Datei:
   Ziel, Umfang, Abnahme (aus der alten Datei übernommen und passend zugeordnet), Kopfzeile „Kette KETTE-Pnn“,
   Verweis auf die Abhängigkeit zur vorigen Aufgabe der Kette, falls vorhanden. Inhalt nicht neu erfinden,
   nur zuordnen; gemeinsame Abschnitte („Ableton“, „Verbindliche Wiederverwendung“) bei der passenden Aufgabe
   oder bei allen betroffenen.
2. Die alten Dateien `AUFGABE-K00` … `AUFGABE-K08` per `git mv`/Löschen entfernen. **`AUFGABE-K09-…` und
   `AUFGABE-K10-…` (diese Datei) bleiben unverändert** (K09 läuft gerade als eigene Kette).
3. Register in KETTEN.md (nur die Spalte „Aufgaben“ und die Titel der Zeilen KETTE-P00 … KETTE-P08):
   je Kette die neuen Aufgabennummern in Reihenfolge, z. B. `01 → 02`. Titel ohne „(K00 Umfang 3)“ u. ä.
   Spalten „Stand“ und „Voraussetzung“ nicht ändern.
4. `.ketten.json`: `task_token` auf `\d\d|K\d\d` und `task_file` auf `AUFGABE-(\d\d|K\d\d)-.*\.md$` setzen
   (K09/K10 bleiben bis zum Merge der laufenden Kette gültig).
5. Prosa in PLAN.md, CONTRACT.md, REUSE-AMM.md, README.md, KETTEN.md (Text unterhalb des Registers) und
   `ergebnisse/K00.md` … `K08.md`: jedes Kürzel K0–K9 so ersetzen, dass klar ist, ob die Kette (`KETTE-Pnn`)
   oder eine Aufgabe (`Aufgabe nn`) gemeint ist. Ergebnisdateien nach `ergebnisse/KETTE-Pnn.md` umbenennen.
6. Tabelle „Alt → Neu“ (K0x Umfang n → Aufgabe nn, Kette) in `ergebnisse/KETTE-P10.md`.

## Nicht im Umfang

Kein Code, keine Tests, keine inhaltliche Änderung an Zielen oder Abnahmen, kein Ändern der Stände.

## Abnahme

- `ketten check` (Werkzeug `ketten`, im Checkout) meldet keine FEHLER; jede Aufgabennummer des Registers hat eine
  Datei; keine Nummer doppelt.
- Kein Kürzel `K0`–`K9` mehr ohne klare Zuordnung (Prüfung: Suche nach `\bK\d\b|\bK0\d\b` liefert nur K09/K10 und
  die Tabelle „Alt → Neu“).
- Alle Inhalte der alten Dateien finden sich in den neuen wieder (Tabelle „Alt → Neu“ belegt das).
