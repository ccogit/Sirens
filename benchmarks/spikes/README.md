# WP02 – Spike-Übersicht

Alle Gates `nicht_gemessen`. Lizenzampel ist nur Vorprüfung, keine Gate-Freigabe. Reihenfolge priorisiert gesperrte Folgeketten.

| Reihenfolge | Kandidat | Lizenzampel | Modus (Hypothese) | Gate |
|---|---|---|---|---|
| 1 | [RoFormer / DrumSep](roformer-drumsep/BERICHT.md) | gelb | README: Pre-trained models; https://github.com/pymss-project/pymss (README CLI inference). Modell-/Konfig-Paar und Lizenz einzeln prüfen; Größen und Hashes offen. | nicht_gemessen |
| 2 | [SAM Audio](sam-audio/BERICHT.md) | gelb | https://huggingface.co/facebook/sam-audio-small ; Zugang beantragen, Authentifizierung; keine Secrets im Repo. Größe und Gewichtslizenz vor Bezug prüfen. | nicht_gemessen |
| 3 | [DEMON](demon/BERICHT.md) | gelb | ACE-Step v1.5 (~18 GB laut Quickstart), LoRAs separat prüfen; keine Gewichtsfreigabe abgeleitet. | nicht_gemessen |
| 4 | [RAVE](rave/BERICHT.md) | gelb | README: pretrained models / Export; nur selbst exportiertes oder geprüftes lokales TorchScript, Größe und Gewichtslizenz offen. | nicht_gemessen |
| 5 | [AFTER](after/BERICHT.md) | gelb | README: Pretrained codecs und models; nubo.ircam.fr; Größe, Hash und separate Gewichtslizenz offen. | nicht_gemessen |
| 6 | [Stable Audio 3](stable-audio-3/BERICHT.md) | gelb | https://huggingface.co/stabilityai/stable-audio-3-small-music ; Community-Lizenz und konkrete Nutzungsbedingungen prüfen; Dateigröße und Hash noch offen. | nicht_gemessen |
| 7 | [Magenta RealTime 2](magenta-realtime/BERICHT.md) | gelb | README: Models & checkpoints, https://github.com/magenta/magenta-realtime/blob/main/docs/models.md ; Ressourcen und Gewichte separat, Größe/Lizenz nicht abschließend geprüft. | nicht_gemessen |
| 8 | [GPU Audio SDK](gpu-audio-sdk/BERICHT.md) | gelb | Keine Modellgewichte für Gain-Beispiel; SDK-Binaries und Lizenz vor Installation prüfen. | nicht_gemessen |
| 9 | [Beat This! Live](beat-this-live/BERICHT.md) | grün | README Evaluation: verlinkte Checkpoints auf cloud.cp.jku.at; Größe/Hash offen. | nicht_gemessen |
| 10 | [Signalsmith Stretch](signalsmith-stretch/BERICHT.md) | grün | Keine Modellgewichte. | nicht_gemessen |

1. Code-Commit, Abhängigkeiten, Gewichte (Quelle, Lizenz, Größe, Hash) vor Bezug festlegen; keinerlei automatische Downloads. Separate Umgebung außerhalb der produktiven venv.
2. Baseline: `python -m benchmarks.baseline --out benchmarks/results/local/baseline.json`.
3. Synthetische Fixtures: `python -m benchmarks.fixtures --out benchmarks/results/local/fixtures`.
4. Kandidaten einzeln CPU/GPU prüfen, keine parallelen Modelle, dann unter normaler Visualisierungslast wiederholen. Berichte enthalten den jeweiligen Messplan. Keine Freigabe allein durch RTF < 1.
5. Nur A0 entscheidet Gates; JSON und Hörproben lokal, keine Musik oder Gewichte committen. KETTE-26: Separation; 27: SAM; 33: DEMON; 34: RAVE/AFTER; 35: SA3; 36: Magenta.

Installations- und Inferenzskripte noch in Arbeit; Berichte sind Quellen-Vorprüfung, keine getestete Installation.
