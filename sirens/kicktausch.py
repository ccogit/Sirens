"""Kick-Tausch (Spielzeug im Live Lab): die Kick eines Songs durch die eines anderen ersetzen.

Ablauf im Hintergrund, ein Tausch nach dem anderen: Spuren trennen (Schlagzeug und Rest; je Song einmal, danach aus dem
Zwischenspeicher), dann rechnet `kick_dsp.py` den Tausch. Alles liegt in der Ablage unter `spielzeug/`, nie im Musikordner.
Die Trennung macht ein fremdes Werkzeug: `SIRENS_STEMS_CMD` (JSON-Liste) oder ein installiertes demucs.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .contracts import Ablehnung, safe_audio_path

DSP = Path(__file__).with_name("kick_dsp.py")
ENDUNGEN = (".flac", ".wav")


def stems_befehl(env):
    """Befehl zur Stem-Trennung als Liste mit den Platzhaltern {ein}, {ein_ordner}, {ein_name} und {aus}; None, wenn keiner da ist.

    Er muss im Ordner {aus} (beliebig tief) `drums` und `no_drums` als FLAC oder WAV ablegen – so wie `demucs --two-stems drums`.
    """
    if env.get("SIRENS_STEMS_CMD"):
        try:
            befehl = json.loads(env["SIRENS_STEMS_CMD"])
        except ValueError:
            return None
        return befehl if isinstance(befehl, list) and befehl and all(isinstance(t, str) for t in befehl) else None
    if importlib.util.find_spec("demucs"):
        return [sys.executable, "-m", "demucs", "--two-stems", "drums", "--flac", "-o", "{aus}", "{ein}"]
    return None


def _spur(ordner, name):
    return next((p for p in sorted(ordner.rglob(f"{name}.*")) if p.suffix.lower() in ENDUNGEN), None)


class KickTausch:
    def __init__(self, cfg, env):
        self.cfg, self.env = cfg, env
        self.sperre = threading.Lock()
        self.jobs, self.schlange, self.faden = {}, [], None

    @property
    def ordner(self):
        return self.cfg.data_dir / "spielzeug"

    def bereit(self):
        return stems_befehl(self.env) is not None and all(
            importlib.util.find_spec(m) is not None for m in ("numpy", "scipy", "soundfile"))

    def _kennung(self, *pfade):
        """Kurzer Name aus Pfad, Größe und Änderungszeit: ändert sich eine Datei, wird neu gerechnet."""
        h = hashlib.sha1()
        for pfad in pfade:
            stand = self.cfg.music_root.joinpath(*pfad.split("/")).stat()
            h.update(f"{pfad}|{stand.st_size}|{int(stand.st_mtime)}\n".encode("utf-8"))
        return h.hexdigest()[:16]

    def start(self, data):
        ziel, spender = (data or {}).get("ziel"), (data or {}).get("spender")
        for feld, pfad in (("ziel", ziel), ("spender", spender)):
            if not safe_audio_path(self.cfg.music_root, pfad, feld).is_file():
                raise Ablehnung("missing_file", "Die Datei gibt es nicht.", feld)
        if ziel == spender:
            raise Ablehnung("invalid", "Bitte zwei verschiedene Songs wählen.", "spender")
        if not self.bereit():
            raise Ablehnung("not_configured", "Die Stem-Trennung ist auf diesem Rechner nicht eingerichtet.", status=409)
        kennung = self._kennung(ziel, spender)
        with self.sperre:
            job = self.jobs.get(kennung)
            if not job or job["stand"] == "fehler":
                job = {"id": kennung, "ziel": ziel, "spender": spender, "stand": "wartet", "schritt": "Wartet", "bericht": None, "fehler": ""}
                fertig = self.ordner / "kicktausch" / f"{kennung}.json"
                if fertig.is_file() and fertig.with_suffix(".wav").is_file():  # schon einmal gerechnet
                    job.update(stand="fertig", schritt="Fertig", bericht=json.loads(fertig.read_text(encoding="utf-8")))
                else:
                    self.schlange.append(job)
                    if not (self.faden and self.faden.is_alive()):
                        self.faden = threading.Thread(target=self._arbeiten, daemon=True)
                        self.faden.start()
                self.jobs[kennung] = job
            return dict(job)

    def zustand(self, kennung):
        with self.sperre:
            job = self.jobs.get(kennung)
            if not job:
                raise Ablehnung("not_found", "Diesen Tausch gibt es nicht.", "id", 404)
            return dict(job)

    def datei(self, kennung):
        if self.zustand(kennung)["stand"] != "fertig":
            raise Ablehnung("not_found", "Der Tausch ist noch nicht fertig.", "id", 404)
        return self.ordner / "kicktausch" / f"{kennung}.wav"

    def _setzen(self, job, **werte):
        with self.sperre:
            job.update(werte)

    def _arbeiten(self):
        while True:
            with self.sperre:
                if not self.schlange:
                    return
                job = self.schlange.pop(0)
            try:
                self._lauf(job)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self._setzen(job, stand="fehler", schritt="Gescheitert", fehler=str(exc)[-400:])

    def _lauf(self, job):
        self._setzen(job, stand="laeuft", schritt="Spuren des Zielsongs trennen (etwa eine Minute)")
        ziel = self._spuren(job["ziel"])
        self._setzen(job, schritt="Spuren des Spendersongs trennen (etwa eine Minute)")
        spender = self._spuren(job["spender"])
        self._setzen(job, schritt="Kick tauschen")
        aus = self.ordner / "kicktausch"
        aus.mkdir(parents=True, exist_ok=True)
        teil = aus / f"{job['id']}.teil.wav"
        lauf = subprocess.run([sys.executable, str(DSP), str(_spur(ziel, "drums")), str(_spur(ziel, "no_drums")),
                               str(_spur(spender, "drums")), str(teil)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            bericht = json.loads(lauf.stdout[lauf.stdout.index("{"):])
        except ValueError:
            raise ValueError((lauf.stderr or lauf.stdout or "Die Klangrechnung hat nicht geantwortet.").strip()) from None
        if lauf.returncode != 0 or bericht.get("error"):
            teil.unlink(missing_ok=True)
            raise ValueError(bericht.get("error") or "Die Klangrechnung ist gescheitert.")
        teil.replace(aus / f"{job['id']}.wav")
        (aus / f"{job['id']}.json").write_text(json.dumps(bericht, ensure_ascii=False), encoding="utf-8")
        self._setzen(job, stand="fertig", schritt="Fertig", bericht=bericht)

    def _spuren(self, pfad):
        """Ordner mit den getrennten Spuren eines Songs; trennt beim ersten Mal und merkt sich das Ergebnis."""
        fertig = self.ordner / "stems" / self._kennung(pfad)
        if fertig.is_dir() and _spur(fertig, "drums") and _spur(fertig, "no_drums"):
            return fertig
        datei = self.cfg.music_root.joinpath(*pfad.split("/"))
        teil = fertig.with_name(fertig.name + ".teil")
        shutil.rmtree(teil, ignore_errors=True)  # Rest eines abgebrochenen eigenen Laufs
        teil.mkdir(parents=True)
        ersetzen = {"{ein}": str(datei), "{ein_ordner}": datei.parent.as_posix(), "{ein_name}": datei.name, "{aus}": teil.as_posix()}
        befehl = stems_befehl(self.env)
        for platz, wert in ersetzen.items():
            befehl = [teil_.replace(platz, wert) for teil_ in befehl]
        lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if lauf.returncode != 0 or not (_spur(teil, "drums") and _spur(teil, "no_drums")):
            shutil.rmtree(teil, ignore_errors=True)
            raise ValueError("Die Stem-Trennung ist gescheitert: " + (lauf.stderr or lauf.stdout or "keine Ausgabe").strip()[-300:])
        teil.replace(fertig)
        return fertig
