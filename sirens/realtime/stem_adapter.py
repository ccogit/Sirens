"""Offline-Stem-Cache: keine Modellimporte im Hauptprozess."""
import hashlib
import json
import tempfile
import threading
import wave
from pathlib import Path

from ..contracts import Ablehnung, safe_audio_path
from .contracts import invalid, error

MODELS = {
    "htdemucs": ("demucs-4.0.0", ("vocals", "drums", "bass", "other"), True),
    "htdemucs_6s": ("demucs-4.0.0", ("vocals", "drums", "bass", "other", "piano", "guitar"), True),
    "roformer": ("1523206d12a521bdb20673726562524cf0f9635b:87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e",
                 ("vocals", "instrumental"), True),
    "drumsep": ("unapproved", (), False),
}


def model(name):
    if not isinstance(name, str) or name not in MODELS:
        raise invalid("model")
    return MODELS[name]


def source_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_key(digest, name, revision, params):
    try:
        raw = json.dumps([digest, name, revision, params], sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise invalid("params") from None
    return hashlib.sha256(raw.encode()).hexdigest()


def wav_shape(path):
    with wave.open(str(path), "rb") as stream:
        shape = (stream.getframerate(), stream.getnchannels(), stream.getnframes())
        if not all(shape):
            raise ValueError("Unvollständige WAV-Datei")
        remaining = shape[2]
        width = shape[1] * stream.getsampwidth()
        while remaining:
            count = min(remaining, 65536)
            if len(stream.readframes(count)) != count * width:
                raise ValueError("Unvollständige WAV-Datei")
            remaining -= count
        return shape


class StemAdapter:
    """Trenner erhält Quelle, privaten Ausgabeordner und Parameter; kein HTTP-Pfad."""
    def __init__(self, music_root, cache_root, runners):
        self.music_root = Path(music_root).resolve()
        self.cache_root = Path(cache_root).resolve()
        if self.cache_root == self.music_root or self.music_root in self.cache_root.parents:
            raise ValueError("Cache darf nicht im Originalordner liegen")
        self.runners = dict(runners)
        self.lock = threading.Lock()

    def capabilities(self):
        return [{"id": name, "revision": revision, "stems": list(stems),
                 "available": enabled and name in self.runners, "mode": "offline"}
                for name, (revision, stems, enabled) in MODELS.items()]

    def separate(self, relative, name, params=None, *, fallback=True):
        model(name)
        params = {} if params is None else params
        if not isinstance(params, dict):
            raise invalid("params")
        source = safe_audio_path(self.music_root, relative)
        if not source.is_file():
            raise error("not_found")
        with self.lock:
            try:
                return self._run(source, name, params)
            except (OSError, RuntimeError, ValueError, EOFError, wave.Error, Ablehnung):
                if not fallback or name != "roformer" or "htdemucs" not in self.runners:
                    raise
                return {**self._run(source, "htdemucs", {}), "fallback_from": name}

    def _run(self, source, name, params):
        revision, stems, enabled = model(name)
        if not enabled or name not in self.runners:
            raise error("unavailable")
        digest = source_hash(source)
        key = cache_key(digest, name, revision, params)
        target = self.cache_root / key
        expected = wav_shape(source)
        def valid(directory):
            return (directory.is_dir() and not directory.is_symlink()
                    and all((directory / (stem + ".wav")).is_file()
                            and not (directory / (stem + ".wav")).is_symlink()
                            and wav_shape(directory / (stem + ".wav")) == expected
                            for stem in stems))
        try:
            hit = valid(target)
        except (OSError, ValueError, EOFError, wave.Error):
            hit = False
        if target.exists() and not hit:
            raise ValueError("Ungültiger Cache; manuelle Bereinigung erforderlich")
        if not hit:
            self.cache_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".stem-", dir=self.cache_root) as temp:
                staging = Path(temp) / "result"
                staging.mkdir()
                self.runners[name](source, staging, params)
                if not valid(staging) or source_hash(source) != digest:
                    raise ValueError("Stem-Format oder Quelle geändert")
                staging.rename(target)
        return {"model": name, "revision": revision, "key": key,
                "stems": list(stems), "cache_hit": hit}
