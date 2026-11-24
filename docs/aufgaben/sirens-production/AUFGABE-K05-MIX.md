# K05 – Mixing und Mastering

Lies PLAN.md, CONTRACT.md, KETTEN.md. Branch/Datei-Ownership laut Register; PR auf integration/sirens-production. Start sofort mit Mocks.

1. Lies ausgerichtete Stems und Plan, implementiere reproduzierbaren Multitrack-Mix mit Gain/Pan/EQ, Kick/Sub-Sidechain, sanften Übergängen, Hall/Delay auf Sends und ausreichendem Headroom. Referenzmerkmale als Zielbereiche, nicht Kopiervorlage. Keine alles plattmachende Kompression.
2. Reuse bestehende Mastering-Funktionen/ffmpeg/Matchering soweit verfügbar; isolierte Run-Kopien. Export Premaster und 24-bit Master; messe EBU R128 LUFS, True Peak, LRA, Clipping, Sub-Mono und Bandspektrum. Ziel-Lautheit optional, ceiling −1 dBTP, Warnung bei übermäßiger Gain-Reduction. Referenzangleichung separat abhörbar.
3. Vergleich von Dry/Mix/Master und gezielte Parameterrevision. Stems unverändert; dokumentierte Einstellungen und Abhängigkeiten.
Abnahme: künstliche Impuls-/Sinus-Stems, Länge/Alignment, keine NaN/Clipping, Mono-Sub und Peak-Test, realer 30–60-s-Groove und Vollsong; lautheitsangepasster Vergleich mit Referenz, tatsächlicher Hörbericht.

Ergebnisbericht: ergebnisse/K05.md, tatsächliche Tests, Messungen, offene Punkte. Keine Daten/Modelle im Git.

Ableton: vorhandene verifizierte Rack-/Effektketten optional via K07 nutzen, sofern automatisierbar. Premaster, Master und trockene bzw. tatsächlich verarbeitete Spuren klar unterscheiden; kein doppeltes Mastering bei Ableton-Return. Stereo-Return als neue Variante analysieren, keine erfundenen Stems. Benutzer muss keine Effekte wählen.
