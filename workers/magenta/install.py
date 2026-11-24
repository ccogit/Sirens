"""Expliziter, hashgeprüfter Modellbezug in isolierter Linux-Umgebung."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv

HERE = Path(__file__).resolve().parent
ENV = Path.home() / ".venv-worker-magenta"
MODEL = ENV / "magenta-rt-v2"


def manifest():
    return json.loads((HERE / "weights.json").read_text(encoding="utf-8"))["models"]


def verify(path, item):
    if not path.is_file() or path.stat().st_size != item["size_bytes"]:
        raise ValueError("Datei fehlt oder Größe stimmt nicht: " + str(path))
    with path.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != item["sha256"]:
            raise ValueError("SHA-256 stimmt nicht: " + str(path))
    return path


def verify_all(directory):
    for item in manifest():
        verify(directory / item["filename"], item)


def obtain(item, directory):
    path = directory / item["filename"]
    if path.exists():
        return verify(path, item)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        partial = Path(tmp.name)
    try:
        with urllib.request.urlopen(item["url"], timeout=120) as response, partial.open("wb") as f:
            remaining = item["size_bytes"]
            while True:
                chunk = response.read(min(1024 * 1024, remaining + 1))
                if not chunk:
                    break
                remaining -= len(chunk)
                if remaining < 0:
                    raise ValueError("Download größer als erwartet")
                f.write(chunk)
        verify(partial, item)
        partial.replace(path)
        return path
    finally:
        partial.unlink(missing_ok=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--modelle-laden", action="store_true")
    mode.add_argument("--entfernen", action="store_true")
    args = p.parse_args(argv)
    if args.entfernen:
        if ENV.exists():
            shutil.rmtree(ENV)
        return 0
    if not args.modelle_laden:
        print("Kein Netzbezug. Mit --modelle-laden nach Bestätigung installieren.")
        return 0
    if sys.platform != "linux" or sys.version_info[:2] != (3, 12):
        p.error("Linux/WSL2 mit Python 3.12 erforderlich")
    print("Code: Apache-2.0; https://github.com/magenta/magenta-realtime")
    print("Gewichte/Nutzungsbedingungen: https://huggingface.co/google/magenta-realtime-2")
    for item in manifest():
        print(item["url"], item["size_bytes"], "Bytes", item["license"], item["sha256"])
    if input("Quellen und Lizenzen geprüft; Pakete und Gewichte beziehen? (ja/nein) ").strip() != "ja":
        return 1
    if not (ENV / "bin/python").exists():
        venv.EnvBuilder(with_pip=True).create(ENV)
    python = ENV / "bin/python"
    subprocess.run([str(python), "-m", "pip", "install", "--only-binary=:all:",
                    "-c", str(HERE / "requirements.lock"), "magenta-rt[jax]==2.0.3",
                    "jax[cuda12]==0.10.1"], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    for item in manifest():
        obtain(item, MODEL)
    verify_all(MODEL)
    print("Gewichte geprüft:", MODEL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
