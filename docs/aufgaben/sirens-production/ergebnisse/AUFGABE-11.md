# AUFGABE-11 – PCM24-Extensible

Implementiert auf extern/KETTE-P11; PR #65. Keine Änderungen am Register.

| Abnahmepunkt | Beleg |
|---|---|
| PCM24 klassisch und extensible PCM, Mono/Stereo | `test_contracts_pcm24.PCM24Tests.test_formats_and_channels`: selbst erzeugte RIFF-Bytes mit fmt, ungeradem JUNK und data, Header/Frames, Assetmessung |
| Float ablehnen, kaputte Header abfangen | `test_float_and_malformed`: beide Format-Tags bzw. Subformat-GUID, falscher Container, abgeschnittene und überlange Chunks |
| Alle Prüfstellen in contracts.py und assets.py | `open_pcm_wav`, `validate_wav`, `inspect_wav` nutzen denselben begrenzten Frame-Leser; klassische wave-Ausgaben mit ungeradem letzten data-Chunk bleiben lesbar |

Reuse: vorhandene Sirens-Validatoren und AMM-/SecondRoom-Assetpfade (ADAPT); keine Änderung an Lieferdiensten (REUSE-AMM.md). NEW nur RIFF-Header-Leser, weil Python 3.11 wave extensible PCM ablehnt.

Prüfung: Tests geschrieben, nicht ausgeführt. Vollständiger Checkout im lokalen Container nicht möglich: `git ls-remote https://github.com/ccogit/Sirens.git` → `Could not resolve host: github.com`. GitHub Actions ist abgeschaltet. Koordinator: `py -3.11 -m unittest discover -s tests -v` (Windows).

Offene Risiken: andere WAV-Leser außerhalb der Owner-Dateien sind nicht Teil dieser Aufgabe; RF64 und PCM mit abweichender Container-/Valid-Bittiefe werden nicht unterstützt. Kein realer ffmpeg-WAV-Hörtest.
