# K01 – Persönliches Referenzwissen

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Inventarisiere lokal Katalog, Store, Rohbewertungen, Kommentare, Favoriten, Ästhetik-Achsen, Sidecars und vorhandene Prompts/Lyrics. Kein Nutzerfragebogen. Katalog-Maximalwert und Rohwerte auseinanderhalten; unbewertet != 0. Original/eMastered und Songfamilien korrekt gruppieren. Fehlende Prompts/Lyrics nicht rekonstruieren.
2. Liefere references.json gemäß Vertrag, mit automatisch gewählten Stil-/Tempo-nahen +1/+2-Beispielen, negativen Kontrasten und gruppenbasiertem Holdout. Erst Mix-Merkmale mit bestehenden Beat-/Dramaturgie-/Analyse-Tools, selektive Trennung/Notenerkennung bei Bedarf. Cache nach Hash, Messmethode und Konfidenz. Produktionsreferenzen getrennt von Musikbewertung; kein Audio-Reuse.
3. Liefere kompaktes lesbares Profil für Produzenten und Abdeckung/Fehlstellen; local-only. Keine unkontrollierte Datenbank-Anbindung.
Abnahme: Fixtures mit widersprüchlichen Bewertungen, Dubletten, fehlenden Metadaten, unbewerteten Songs, Holdout ohne Familienleak; lokaler Inventurbericht ohne private Daten in Git. Echte Lieblingssongs automatisch gefunden oder fehlende Verfügbarkeit explizit.

Ergebnisbericht: ergebnisse/K01.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

Ableton: Eigene vorhandene, bereits im Katalog registrierte Ableton-Fassungen als Referenz berücksichtigen, sofern Herkunft erkennbar; kein automatisches Scannen beliebiger Live-Projekte oder Templates. Manuelle Returns sind neue Versionen derselben Songfamilie; keine Holdout-Leaks.
