# RTX Neural Lab – vorläufiges Nutzerhandbuch

**G4: nicht gemessen.** Die folgenden Zahlen beschreiben ausschließlich
G1-Messungen aus benchmarks/results/g1 am Zielrechner. Sie sind keine
garantierten hörbaren End-to-End-Latenzen oder Produktfreigaben.

| Funktion / G1 | Tatsächlich gemessene Grenzen | Beleg |
|---|---|---|
| DEMON: Streaming, TensorRT-Decoder, Tiefe 1 | 92 ms (10 s Song) bzw. 121 ms (30 s Song) bis neues Latent; Fensterdecode p95 8,3 bzw. 8,6 ms; eager 333 ms, kein gleichwertiger Modus | [demon.md](../../benchmarks/results/g1/demon.md) |
| RAVE: Streaming, kausaler Gitarrenexport | Block 2048 Samples bei 48 kHz; p95 11,7 ms und RTF p95 0,27 über 120 s Audio; Geräte-/Underrun-Test nicht gemessen | [rave.md](../../benchmarks/results/g1/rave.md) |
| RoFormer: Offline | 30 s Testsignal, kalt 23,8 s inklusive Laden, warm 1,15 s; Peak-VRAM nicht gemessen | [roformer.md](../../benchmarks/results/g1/roformer.md) |
| Stable Audio 3 small-music: Lookahead | warm 8 s Audio in 0,35–0,40 s; kalt erster Lauf 21,2 s, kein Streaming; Prompt-Treue offen | [stable-audio-3.md](../../benchmarks/results/g1/stable-audio-3.md) |
| AFTER, SAM Audio, Magenta, DrumSep | nicht gemessen / gesperrt | kein G1-Freigabebeleg |
| DSP, Aufnahme, AudioCore, Geräte-Latenz, G4 | nicht gemessen | keine entsprechende Ergebnisdatei unter benchmarks/results |

Nach lokaler Freigabe im Live Lab das RTX Neural Lab wählen. GPU-Panel und
Profil kontrollieren; Eco sperrt GPU-Worker. Performance für den stabilen
Durchlauf verwenden, Neural und Training/Render nur gemäß verfügbarer
Ressourcen. Nicht gleichzeitig ungemessene Modelle erzwingen. Dry/Wet
zunächst bei kleinem Pegel prüfen. DEMON vorladen, TensorRT-Engine passend
zur lokalen GPU und Version prüfen; RAVE nur nichtkommerziell.
Für Stems RoFormer als Vorbereitung auswählen; keine Live-Separation
erwarten. Pads vor dem gewünschten Takt berechnen lassen, verspätete
Ergebnisse nicht als Echtzeit ausgeben. DSP, BeatGrid und Aufnahme mit
synthetischen Quellen erproben. Export in Sitzungsordner; Originale
bleiben unberührt. Mock ist ausdrücklich keine KI.
Bei Störungen Dry/Bypass, Stop/Panic, Sitzung schließen; keine
ungeprüfte Capability erzwingen. Siehe [Runbook](runbook.md).
