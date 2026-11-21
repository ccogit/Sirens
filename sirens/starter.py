"""Startet Claude Code im Hintergrund, sobald der Nutzer auf der Seite etwas an Claude übergibt.

Es läuft immer höchstens eine Sitzung. Kommt währenddessen etwas Neues dazu, startet danach
genau eine weitere. Die Ausgabe jeder Sitzung liegt als Protokoll in der Ablage.
"""
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

from .store import jetzt

SATZ = "Bearbeite die Songaufträge"
PROJEKT = Path(__file__).resolve().parents[2]


def befehl(env=None):
    """Der Aufruf von Claude Code. `SIRENS_CLAUDE_CMD` (JSON-Liste) ersetzt ihn, z. B. für Tests."""
    env = os.environ if env is None else env
    if env.get("SIRENS_CLAUDE_CMD"):
        return json.loads(env["SIRENS_CLAUDE_CMD"])
    programm = shutil.which("claude")
    if not programm:
        return None
    cmd = [programm, "-p", "--permission-mode", env.get("SIRENS_CLAUDE_MODE", "auto")]
    if env.get("SIRENS_CLAUDE_MODEL"):
        cmd += ["--model", env["SIRENS_CLAUDE_MODEL"]]
    return cmd


class ClaudeStarter:
    def __init__(self, cfg, cmd=None, cwd=PROJEKT):
        self.cfg, self.cmd, self.cwd = cfg, cmd, cwd
        self.sperre = threading.Lock()
        self.prozess = None
        self.gestartet_am = None
        self.nochmal = False
        self.letzter = None

    @property
    def protokolle(self):
        return self.cfg.data_dir / "claude-laeufe"

    def zustand(self):
        with self.sperre:
            return {"aktiv": bool(self.cfg.claude_start), "laeuft": self.prozess is not None,
                    "gestartet_am": self.gestartet_am, "letzter": self.letzter}

    def starten(self, grund=""):
        """Startet eine Sitzung oder merkt eine weitere vor. Gibt den Zustand zurück."""
        if not self.cfg.claude_start:
            return self.zustand()
        with self.sperre:
            if self.prozess is not None:
                self.nochmal = True
            else:
                self._los(grund)
        return self.zustand()

    def _los(self, grund):
        cmd = self.cmd or befehl()
        zeit = jetzt()
        if not cmd:
            self.letzter = {"beendet_am": zeit, "exit_code": None, "protokoll": "",
                            "fehler": "Claude Code (claude) wurde auf diesem Rechner nicht gefunden."}
            return
        self.protokolle.mkdir(parents=True, exist_ok=True)
        datei = self.protokolle / (zeit.replace(":", "").replace("-", "") + ".log")
        try:
            with open(datei, "wb") as aus:
                aus.write(f"# {zeit} {grund}\n".encode("utf-8"))
                aus.flush()
                prozess = subprocess.Popen(cmd, cwd=str(self.cwd), stdin=subprocess.PIPE, stdout=aus,
                                           stderr=subprocess.STDOUT,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            prozess.stdin.write(SATZ.encode("utf-8"))
            prozess.stdin.close()
        except OSError as fehler:
            self.letzter = {"beendet_am": zeit, "exit_code": None, "protokoll": str(datei), "fehler": str(fehler)}
            return
        self.prozess, self.gestartet_am, self.nochmal = prozess, zeit, False
        threading.Thread(target=self._warten, args=(prozess, datei), daemon=True).start()

    def _warten(self, prozess, datei):
        code = prozess.wait()
        with self.sperre:
            self.prozess, self.gestartet_am = None, None
            self.letzter = {"beendet_am": jetzt(), "exit_code": code, "protokoll": str(datei),
                            "fehler": "" if code == 0 else f"Claude Code endete mit Code {code}."}
            if self.nochmal and code == 0:
                self._los("Neues kam während der letzten Sitzung dazu.")
            self.nochmal = False

    def warten(self, timeout=20):
        """Für Tests: wartet, bis keine Sitzung mehr läuft."""
        import time
        ende = time.monotonic() + timeout
        while time.monotonic() < ende:
            with self.sperre:
                if self.prozess is None:
                    return True
            time.sleep(0.05)
        return False
