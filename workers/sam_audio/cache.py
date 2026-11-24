"""Serverseitig nutzbarer Cache ohne Modellimporte; keine HTTP-Pfade."""
import hashlib
import json
import wave
from pathlib import Path

from .adapter import FILES, decode, prompt_value, shape


def source_hash(source):
    with Path(source).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def key_for(digest, revision, params):
    if not isinstance(revision, str) or not revision or "unverified" in revision:
        raise ValueError("Bestätigte Modellrevision erforderlich")
    raw = json.dumps(["sam_audio", "pcm16-mono-15s-v1", digest, revision,
                      prompt_value(params)], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_assets(source, directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        return False
    if {p.name for p in directory.iterdir()} != set(FILES):
        return False
    paths = [directory / name for name in FILES]
    if any(p.is_symlink() or not p.is_file() for p in paths):
        return False
    try:
        expected = shape(source)
        if any(shape(p) != expected for p in paths):
            return False
        with wave.open(str(source), "rb") as orig, wave.open(str(paths[0]), "rb") as target, wave.open(str(paths[1]), "rb") as residual:
            remaining = expected[1]
            while remaining:
                n = min(remaining, 65536)
                a, b, c = (decode(w.readframes(n)) for w in (orig, target, residual))
                if any(len(x) != n*2 for x in (a, b, c)):
                    return False
                if any(x != y+z for x, y, z in zip(a, b, c)):
                    return False
                remaining -= n
        return True
    except (OSError, ValueError, EOFError, wave.Error):
        return False


class SemanticCache:
    """Cache nur nach erfolgreichem Supervisor-Dateijob atomar publizieren."""
    def __init__(self, root, music_root):
        self.root = Path(root).resolve()
        music = Path(music_root).resolve()
        if self.root == music or music in self.root.parents:
            raise ValueError("Cache außerhalb des Musikordners erforderlich")

    def lookup(self, source, revision, params):
        digest = source_hash(source)
        key = key_for(digest, revision, params)
        directory = self.root / key
        if directory.exists() or directory.is_symlink():
            if not validate_assets(source, directory):
                raise ValueError("Beschädigter Cache")
            return digest, key, directory
        return digest, key, None

    def publish(self, source, staging, digest, revision, params, cancelled):
        staging = Path(staging)
        if cancelled.is_set():
            raise ValueError("Job abgebrochen")
        if source_hash(source) != digest or not validate_assets(source, staging):
            raise ValueError("Quelle geändert oder fehlerhafte Assets")
        directory = self.root / key_for(digest, revision, params)
        self.root.mkdir(parents=True, exist_ok=True)
        if cancelled.is_set():
            raise ValueError("Job abgebrochen")
        # Aufrufer serialisiert Publish und Cancel (Job-Lock).
        try:
            staging.rename(directory)
        except OSError:
            if not validate_assets(source, directory):
                raise
        return directory
