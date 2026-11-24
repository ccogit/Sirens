# WP06 – Messharness für Gate G2

Nicht gemessen. Keine Kundendaten, Modelle oder Musikdateien im Repo.

1. Sirens mit SIRENS_RT_ENABLED=1 und SIRENS_RT_MOCK=1 lokal starten. Andere Audioquellen beenden. Chrome/Edge auf der lokalen Sirens-Seite öffnen; 48-kHz-Gerät, niedriger Pegel.
2. In DevTools unter Sources → Snippets ein neues Snippet anlegen und den Inhalt von `benchmarks/g2/soak.js` einfügen. Starten (Nutzerinteraktion); falls der AudioContext suspendiert bleibt, Gerät/Browserfreigabe prüfen. Tab 30 Minuten im Vordergrund belassen. Der Harness nutzt den realen Mock-Worker, Sidecar, binäre PCM-Blöcke und AudioCore; keine Browser-Mock-API.
3. Nach Abschluss der 30 Minuten meldet die Konsole den separaten Fehlerabschnitt. Im Prozessmanager ausschließlich den zu diesem Test gestarteten Mock-Worker (Kommando unter workers/mock, Startzeit und Elternprozess prüfen) beenden, nicht den Hauptdienst oder fremde Prozesse. Den Dry-Rückfall anhören; das Skript überprüft zusätzlich den digitalen Master-Abgriff. Das Ergebnis wird als `wp06-g2-roh.json` gespeichert. Keine Tokens oder Audiodaten werden gespeichert.
4. `python -m benchmarks.g2.report wp06-g2-roh.json --out benchmarks/results/wp06-g2.json` (optional `--ci-green` ausschließlich nach belegter grüner PR-CI).
5. `python -m benchmarks.result benchmarks/results/wp06-g2.json` validiert das Ergebnisformat.

Erfolg: 1800 Sekunden ohne unerwarteten Underrun, keine verlorenen/ungültigen Blöcke, digitale Fixture-Deckung <= 1 Sample, Worker-Zustand error und Dry-Rückfall, CPU-CI grün. Dieser Harness prüft die digitale PCM-Deckung; analoger Geräte-Loopback bleibt eine separate Messung (WP04-Anleitung). Der kontinuierliche Loop isoliert den Transport; zusätzliche UI-Loop-/Seek-Wechsel und Master-Ausrichtung sind getrennt auf dem Zielrechner zu prüfen. Keine Freigabe allein aus einer deklarativen Capability.
