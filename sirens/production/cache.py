"""Content-addressed cache; published entries are immutable and verified on read."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .contracts import ContractError, read_manifest, safe_path, sha256_file
from ..store import write_json_atomic


def cache_key(stage, inputs, backend, revision, seed):
    data = json.dumps(dict(stage=stage, inputs=inputs, backend=backend, revision=revision,
                           seed=seed), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class HashCache:
    def __init__(self, production_root):
        self.root = safe_path(production_root, "cache")
        self.root.mkdir(exist_ok=True)

    def entry(self, key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ContractError("cache key")
        return safe_path(self.root, key)

    def publish(self, key, source, files):
        target = self.entry(key)
        if target.exists():
            return
        temp = Path(tempfile.mkdtemp(prefix=".pending-", dir=self.root))
        try:
            hashes = {}
            for relative in files:
                if relative == "cache.json" or relative in hashes:
                    raise ContractError("invalid cache files")
                src = safe_path(source, relative)
                dst = safe_path(temp, relative)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                hashes[relative] = sha256_file(dst)
            write_json_atomic(temp / "cache.json", {"schema_version": 1, "key": key, "files": hashes})
            try:
                temp.rename(target)
            except OSError:
                if not target.is_dir():
                    raise
        finally:
            if temp.exists():
                shutil.rmtree(temp)

    def restore(self, key, destination):
        entry = self.entry(key)
        if not entry.exists():
            return False
        meta = read_manifest(safe_path(entry, "cache.json"))
        if meta.get("schema_version") != 1 or meta.get("key") != key or not isinstance(meta.get("files"), dict):
            raise ContractError("invalid cache entry")
        pairs = []
        for relative, digest in meta["files"].items():
            src = safe_path(entry, relative)
            dst = safe_path(destination, relative)
            if relative == "cache.json" or dst.exists() or sha256_file(src) != digest:
                raise ContractError("cache integrity or destination conflict")
            pairs.append((src, dst))
        for src, dst in pairs:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open("xb") as out, src.open("rb") as inp:
                shutil.copyfileobj(inp, out)
        return True
