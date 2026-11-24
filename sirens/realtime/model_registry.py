"""Vertrauenswürdige lokale Manifeste, keine Pfade aus HTTP-Anfragen."""
import copy
import json
import re
import sys
from pathlib import Path

from ..config import umgebung
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
        self.env = umgebung(env, self.root / ".env")
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
                python = self.env.get(key, sys.executable if cap["mock"] else "")
                interpreter = Path(python).expanduser()
                installed = bool(python and interpreter.is_absolute() and interpreter.is_file())
                entry["capability"]["available"] = bool(cap["available"] and installed)
                entry["command"] = (str(interpreter), "-u", str(script), *args)
                self.entries[name] = entry
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                continue
            except Exception as exc:
                # Nur Vertragsfehler aus fehlerhaften lokalen Manifesten überspringen.
                from ..contracts import Ablehnung
                if not isinstance(exc, Ablehnung):
                    raise

    def capabilities(self):
        return [copy.deepcopy(e["capability"]) for e in self.entries.values()]

    def resolve(self, name):
        if not isinstance(name, str) or name not in self.entries:
            raise invalid("worker")
        entry = self.entries[name]
        if not entry["capability"]["available"]:
            raise error("unavailable")
        return copy.deepcopy(entry)
