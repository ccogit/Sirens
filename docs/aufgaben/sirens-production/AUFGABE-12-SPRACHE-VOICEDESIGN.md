# Aufgabe 12 – Kette KETTE-P11, Aufgabe 2 von 2 (nach Aufgabe 11). Spoken Word mit Qwen3-TTS VoiceDesign im Worker

Folgeaufgabe aus dem ersten echten Clear-Head-Lauf am Zielrechner (Windows 11, RTX 5080, py -3.11), 24.11.2026. Lies PLAN.md, CONTRACT.md, KETTEN.md (Begriffe, Regeln) und die genannte Ergebnisdatei. Kein Test braucht Netz, GPU, Plugins oder Live; Tests müssen unter Linux UND Windows laufen.

Dateien: `sirens/production/assets.py`, `workers/production_assets/`, Tests `tests/production/test_assets*`.

## Befund
Der Sprach-Worker erwartet das CustomVoice-Modell. Installiert und lizenzgeprüft ist `Qwen3-TTS-12Hz-1.7B-VoiceDesign` (Apache-2.0, Stimme aus Beschreibung, keine Stimmkopie); die Sprache musste außerhalb der Pipeline erzeugt werden. Gemessen: Laden 5 s, ~1,9x Echtzeit warm, 4,4 GB VRAM, 24 kHz.

## Umfang
1. Worker unterstützt VoiceDesign (`generate_voice_design(text, instruct, language)`), Modellpfad aus Konfiguration (`tts_model`), Stimmbeschreibung aus dem Asset-Request (`prompt`).
2. Resampling auf 48 kHz PCM24 im Worker, Messung der Dauer, Provenienz (Modell, Revision, Seed, Lizenz) in assets.json.
3. Ein Modell-Laden je Run (nicht je Cue).

## Abnahme
Mock-Worker-Tests (kein Modell im Test), Konfigurationsfehler klar gemeldet; lokaler Befehl für einen Cue in `ergebnisse/AUFGABE-12.md`.
