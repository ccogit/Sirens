# K06 – Qualitätsbenchmark und schlanke Oberfläche

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Implementiere lokale Benchmark-CLI und Berichte aus CONTRACT.md; wiederverwendbare bestehende Messwerkzeuge, technische Gates, null statt erfundene Werte. Blindes A/B mit randomisierter persistenter Reihenfolge, Lautheitsabgleich ca. 0,5 LU, Originalmaster getrennt, keine Modellnamen bis Abstimmung. Nutzerurteile getrennt Musik/Produktion 1–5, Präferenz/Tie, Kommentar optional. Bestehende Bewertungen für Referenzen, neue Urteile nur zu neuen Kandidaten.
2. Mock-Fixtures und Messungen für Taktgenauigkeit, Dauer, Peak/Clipping, Fehlerfälle, Textvollständigkeit soweit maschinell prüfbar. G0–G3 exakt nach PLAN; keine Score-Manipulation. Aus Bericht nächste zwei gezielte Verbesserungen ableiten, keine automatischen nicht belegten ästhetischen Scores.
3. Eine kleine Signal-Room-Session mit minimalem Standardweg „Song erstellen“ → anhören → „Verbessern“/„Gefällt mir“, optional „In Ableton öffnen“ und „Ableton-Fassung übernehmen“ sowie bewusster Übernahme in den Katalog. Preview/Full, Referenzen, A/B, technische Berichte und Backend-Auswahl nur in Details. K07-Capabilities per Mock, kein eigener Ableton-Adapter; Lifecycle laut docs/signal-room.md. K0 bindet API/Register/Stylesheet ein. UI zeigt unavailable/mock/real klar an; kein Autoplay, keine Modellinstallation beim Mount. CLI hat Vorrang vor UI.
Abnahme: CPU-CI ohne Netzwerk/GPU, Blindtest-Fixture mit entblindeter Auswertung, reales B1/B2-Hörprotokoll lokal, keine falsche Qualitätsfreigabe, Browser-Lifecycle-Test.

Ergebnisbericht: ergebnisse/K06.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

UX-Abnahme: keine Pflichtauswahl von Modellen, Plugins, MIDI, GPU, Referenzen oder Mastering, keine Pflicht-Zwischenfreigabe. Ein Klick Produktion und ein Klick Abspielen. Ableton-Knopf zeigt tatsächliches Set oder ehrlichen Importpaket-Fallback, Return nur nach validiertem Eingang, klare Fehlermeldung. Test Standardweg ohne Live und optionalen Roundtrip; bestehende A/B-Gates sind Entwicklungsabnahme und keine Alltagshürde.
