"""Lokale KI-Stem-Trennung mit Demucs: vorbereiten, zwischenspeichern, später live mischen.

Die Inferenz startet ausschließlich auf ausdrücklichen Wunsch und verwendet standardmäßig die CPU,
damit Claude bzw. die Musikproduktion keinen GPU-Speicher verliert. Keine Uploads.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .contracts import Ablehnung, safe_audio_path

MODELLE = {
    "htdemucs": ("vocals", "drums", "bass", "other"),
    "htdemucs_6s": ("vocals", "drums", "bass", "other", "piano", "guitar"),
}
MAX_DATEI = 1024 * 1024 * 1024


class StemDienst:
    def __init__(self, cfg):
        self.cfg = cfg
        self._sperre = threading.Lock()
        self._laeuft = None
        self._jobs = {}

    def _eingabe(self, pfad, modell):
        if not isinstance(modell, str) or modell not in MODELLE:
            raise Ablehnung("invalid", "Unbekanntes Stem-Modell.", "modell")
        quell = safe_audio_path(self.cfg.music_root, pfad)
        if not quell.is_file():
            raise Ablehnung("not_found", "Der ausgewählte Song ist nicht vorhanden.", "pfad", 404)
        stat = quell.stat()
        if stat.st_size > MAX_DATEI:
            raise Ablehnung("too_large", "Die Audiodatei ist für die Stem-Trennung zu groß.", "pfad", 413)
        # Bei Änderungen der Quelle ist der frühere Cache absichtlich nicht mehr gültig.
        daten = json.dumps([str(quell), stat.st_size, stat.st_mtime_ns, modell], ensure_ascii=False)
        schluessel = hashlib.sha256(daten.encode("utf-8")).hexdigest()
        cache = self.cfg.data_dir / "stems" / schluessel
        return quell, cache

    @staticmethod
    def _bereit(cache, modell):
        return (cache / ".ready").is_file() and all(
            (cache / (name + ".wav")).is_file() for name in MODELLE[modell]
        )

    def zustand(self, pfad, modell="htdemucs"):
        _, cache = self._eingabe(pfad, modell)
        grund = {"modell": modell, "stems": list(MODELLE[modell])}
        if self._bereit(cache, modell):
            return {**grund, "zustand": "bereit", "meldung": "Instrumente stehen bereit."}
        with self._sperre:
            job = self._jobs.get(cache.name)
            if job:
                return {**grund, **job}
        return {**grund, "zustand": "offen", "meldung": "Noch nicht getrennt."}

    def starten(self, pfad, modell="htdemucs", device="cpu"):
        if device not in ("cpu", "cuda") or not isinstance(device, str):
            raise Ablehnung("invalid", "Für Stem-Trennung sind nur CPU oder CUDA erlaubt.", "device")
        quelle, cache = self._eingabe(pfad, modell)
        if self._bereit(cache, modell):
            return self.zustand(pfad, modell)
        with self._sperre:
            if self._laeuft is not None and self._laeuft != cache.name:
                raise Ablehnung("busy", "Es läuft bereits eine Stem-Trennung. Bitte danach erneut starten.", status=409)
            if self._laeuft != cache.name:
                self._laeuft = cache.name
                self._jobs[cache.name] = {
                    "zustand": "laeuft", "meldung": "KI trennt den Song lokal. Das kann einige Minuten dauern."
                }
                threading.Thread(target=self._trennen, args=(quelle, cache, modell, device), daemon=True).start()
        return self.zustand(pfad, modell)

    def _trennen(self, quelle, cache, modell, geraet):
        fehler = None
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.mkdir(parents=True, exist_ok=True)
            # Ein eigenes Python-Environment mit torch/demucs kann ausdrücklich vorgegeben werden.
            python = os.environ.get("SIRENS_STEMS_PYTHON") or sys.executable
            with tempfile.TemporaryDirectory(prefix="stem-", dir=cache.parent) as temp:
                ausgabe = Path(temp) / "output"
                befehl = [python, "-m", "demucs", "-n", modell, "--device", geraet, "-o",
                          str(ausgabe), str(quelle)]
                with (cache / "demucs.log").open("w", encoding="utf-8") as log:
                    ergebnis = subprocess.run(befehl, stdout=log, stderr=subprocess.STDOUT,
                                              timeout=3600, check=False)
                if ergebnis.returncode:
                    raise RuntimeError("Demucs endete mit Code " + str(ergebnis.returncode)
                                       + ". Einzelheiten in der Datei demucs.log.")
                ziel = ausgabe / modell / quelle.stem
                for name in MODELLE[modell]:
                    if not (ziel / (name + ".wav")).is_file():
                        raise RuntimeError("Demucs hat keine vollständigen Audiospuren erzeugt.")
                for name in MODELLE[modell]:
                    os.replace(ziel / (name + ".wav"), cache / (name + ".wav"))
                (cache / ".ready.tmp").write_text(modell, encoding="utf-8")
                os.replace(cache / ".ready.tmp", cache / ".ready")
        except FileNotFoundError:
            fehler = "Python oder Demucs wurde nicht gefunden. Siehe Einrichtung im README."
        except subprocess.TimeoutExpired:
            fehler = "Die Trennung hat das Zeitlimit (60 Minuten) überschritten."
        except (OSError, RuntimeError) as exc:
            fehler = str(exc)
        except Exception:
            fehler = "Die Stem-Trennung ist unerwartet fehlgeschlagen; siehe demucs.log."
        finally:
            with self._sperre:
                if self._laeuft == cache.name:
                    self._laeuft = None
                self._jobs[cache.name] = {
                    "zustand": "fehler" if fehler else "bereit",
                    "meldung": fehler or "Instrumente stehen bereit.",
                }

    def audiodatei(self, pfad, modell, stem):
        _, cache = self._eingabe(pfad, modell)
        if not isinstance(stem, str) or stem not in MODELLE[modell]:
            raise Ablehnung("invalid", "Unbekannte Audiospur.", "stem")
        if not self._bereit(cache, modell):
            raise Ablehnung("not_ready", "Die Instrumente sind noch nicht bereit.", status=409)
        datei = (cache / (stem + ".wav")).resolve()
        basis = self.cfg.data_dir.resolve()
        if basis not in datei.parents or not datei.is_file():
            raise Ablehnung("not_found", "Die Audiospur ist nicht mehr vorhanden.", status=404)
        return datei
