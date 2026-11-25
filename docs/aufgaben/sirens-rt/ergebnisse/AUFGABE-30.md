# AUFGABE-30 – Nahtloser Loop- und Epoch-Wechsel

Ausgangslage: Der Worklet leert beim Loop-Sprung den Wet-Ring; der Produzent erfährt die neue Epoch erst über die Statusabfrage. G4 ist laut Aufgabenbeschreibung nicht bestanden. Ziel: vorbereitete Puffergenerationen, getrennte Seek-/Loop-Underruns, Mock mit Geräteabtastrate, G4-Bericht.

Prüfplan: Node-Taktmodell mit 100 Wechseln und 50 ms Produzentenlatenz; Seek und alte Epoch; Mock 44100/48000 Hz; vollständige Regression; G4-Nachlauf durch Koordinator. Noch nicht geprüft.

## Übergabe

Stand: Aufgabenbeschreibung und Ausgangscode gelesen; Implementierung und Tests offen. Nächster Schritt: Transport und Produzent auf vorangekündigte Epochs umstellen. Keine Messwerte erhoben.
