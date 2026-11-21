"""Optionale KI-Notentranskription isolierter Stems mit Spotify Basic Pitch.

Eine Transkription läuft als separater CPU-Prozess, nie automatisch. Für die
Klangerzeugung im Browser werden nur sichere numerische Noten übertragen.
"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from .contracts import Ablehnung


class StemNoten:
    def __init__(self, stems):
        self.stems = stems
        self._sperre = threading.Lock()
        self._aktiv = None
        self._jobs = {}

    def _dateien(self, pfad, modell, stem):
        wav = self.stems.audiodatei(pfad, modell, stem)
        ziel = wav.with_suffix(".notes.json")
        return wav, ziel

    def zustand(self, pfad, modell, stem):
        wav, ziel = self._dateien(pfad, modell, stem)
        basis = {"stem": stem, "modell": modell}
        if ziel.is_file():
            try:
                noten = json.loads(ziel.read_text(encoding="utf-8"))
                if isinstance(noten, list):
                    return {**basis, "zustand": "bereit", "meldung": f"{len(noten)} Noten erkannt.",
                            "noten": noten[:12000]}
            except (OSError, ValueError):
                pass
        with self._sperre:
            job = self._jobs.get(str(ziel))
            if job:
                return {**basis, **job}
        return {**basis, "zustand": "offen", "meldung": "KI-Notenerkennung noch nicht gestartet."}

    def starten(self, pfad, modell, stem):
        wav, ziel = self._dateien(pfad, modell, stem)
        if ziel.is_file():
            return self.zustand(pfad, modell, stem)
        with self._sperre:
            if self._aktiv is not None and self._aktiv != str(ziel):
                raise Ablehnung("busy", "Eine KI-Notenerkennung läuft bereits.", status=409)
            if self._aktiv != str(ziel):
                self._aktiv = str(ziel)
                self._jobs[str(ziel)] = {"zustand": "laeuft", "meldung": "Basic Pitch erkennt Noten auf der CPU …"}
                threading.Thread(target=self._arbeiten, args=(wav, ziel), daemon=True).start()
        return self.zustand(pfad, modell, stem)

    def _arbeiten(self, wav, ziel):
        fehler = None
        try:
            python = (os.environ.get("SIRENS_STEMS_PITCH_PYTHON") or
                      os.environ.get("SIRENS_STEMS_PYTHON") or sys.executable)
            programm = Path(__file__).with_name("stem_transcribe.py")
            logpfad = wav.with_suffix(".notes.log")
            with logpfad.open("w", encoding="utf-8") as log:
                result = subprocess.run([python, str(programm), str(wav), str(ziel)],
                                        stdout=log, stderr=subprocess.STDOUT,
                                        timeout=900, check=False)
            if result.returncode:
                raise RuntimeError("Basic Pitch endete mit Code " + str(result.returncode) +
                                   ". Details in " + logpfad.name + ".")
            if not ziel.is_file():
                raise RuntimeError("Basic Pitch lieferte keine Notendatei.")
        except FileNotFoundError:
            fehler = "Python oder Basic Pitch fehlt. Siehe README."
        except subprocess.TimeoutExpired:
            fehler = "KI-Notenerkennung überschritt 15 Minuten."
        except (OSError, RuntimeError) as exc:
            fehler = str(exc)
        except Exception:
            fehler = "KI-Notenerkennung fehlgeschlagen; bitte Protokolldatei prüfen."
        finally:
            with self._sperre:
                if self._aktiv == str(ziel):
                    self._aktiv = None
                self._jobs[str(ziel)] = {
                    "zustand": "fehler" if fehler else "bereit",
                    "meldung": fehler or "Noten erkannt.",
                }
