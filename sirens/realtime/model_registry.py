"""Vertrauenswürdige lokale Manifeste, keine Pfade aus HTTP-Anfragen."""
import copy
import json
import re
import sys
from pathlib import Path

from ..config import umgebung
from ..contracts import Ablehnung
from .contracts import error, invalid
from .schemas import validate

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "Eco": {"max_gpu_workers": 0, "max_pending": 2},
    "Performance": {"max_gpu_workers": 1, "max_pending": 4},
    "Neural": {"max_gpu_workers": 2, "max_pending": 8},
    "Training/Render": {"max_gpu_workers": 1, "max_pending": 2},
}


class ModelRegistry:
    def __init__(self, root=ROOT, env=None, *, mock_enabled=False):
        self.root = Path(root).resolve()
        explizit = env is not None
        self.env = umgebung(env, self.root / ".env")
        # Automatische Suche nach installierten Umgebungen: im Betrieb an; bei ausdrücklich übergebener Umgebung
        # (Tests) nur, wenn sie es verlangt. SIRENS_RT_AUTODETECT=aus schaltet sie immer ab.
        schalter = str(self.env.get("SIRENS_RT_AUTODETECT", "" if explizit else "an")).strip().lower()
        self.autodetect = schalter in ("an", "1", "ja", "on", "true")
        self.entries = {}
        for path in sorted((self.root / "workers").glob("*/manifest.json")):
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
                name = path.parent.name
                if (not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", name)
                        or path.resolve().parent.parent != self.root / "workers"
                        or entry["version"] != 1 or entry["name"] != name):
                    continue
                cap = validate("capability", entry["capability"])
                if cap["id"] != name or (cap["mock"] and not mock_enabled):
                    continue
                key = entry["interpreter_env"]
                if not re.fullmatch(r"SIRENS_RT_[A-Z0-9_]+_PYTHON", key):
                    continue
                script = (path.parent / entry["script"]).resolve()
                if script.parent != path.parent.resolve() or not script.is_file():
                    continue
                args = entry["args"]
                if not isinstance(args, list) or any(not isinstance(a, str) or "\x00" in a for a in args):
                    continue
                python = self.env.get(key) or (sys.executable if cap["mock"] else self._gefunden(entry))
                interpreter = Path(python).expanduser()
                installed = bool(python and interpreter.is_absolute() and interpreter.is_file())
                entry["capability"]["available"] = bool(cap["available"] and installed)
                entry["command"] = (str(interpreter), "-u", str(script), *args)
                self.entries[name] = entry
            except (OSError, ValueError, TypeError, KeyError, AttributeError, Ablehnung):
                continue

    def _gefunden(self, entry):
        """Interpreter einer installierten Umgebung ohne .env-Eintrag finden.

        Das Manifest nennt unter `python_dirs` Ordner im Sirens-Ordner (nur `.venv…`, keine Pfade), in der
        Reihenfolge, in der sie gesucht werden; die erste vorhandene Umgebung gilt.
        """
        dirs = entry.get("python_dirs", [])
        if not self.autodetect or not isinstance(dirs, list):
            return ""
        for name in dirs:
            if not isinstance(name, str) or not re.fullmatch(r"\.venv[-a-z0-9_.]{1,64}", name):
                continue
            for teil in (("Scripts", "python.exe"), ("bin", "python")):
                kandidat = self.root.joinpath(name, *teil)
                if kandidat.is_file() and kandidat.resolve().is_relative_to(self.root):
                    return str(kandidat)
        return ""

    def capabilities(self):
        return [copy.deepcopy(e["capability"]) for e in self.entries.values()]

    def resolve(self, name):
        if not isinstance(name, str) or name not in self.entries:
            raise invalid("worker")
        entry = self.entries[name]
        if not entry["capability"]["available"]:
            raise error("unavailable")
        return copy.deepcopy(entry)
