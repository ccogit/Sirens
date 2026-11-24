"""Expliziter lokaler Bezug; keine Fremdimporte im Dry-Run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
PIN = "96acc905204d54bfd3055084ca8e9df8a6d9a33f"
UPSTREAM = "https://github.com/daydreamlive/DEMON.git"


def manifest():
    return json.loads((HERE / "weights.json").read_text(encoding="utf-8"))


def metadata(path):
    with path.open("rb") as f:
        return {"size_bytes": path.stat().st_size,
                "sha256": hashlib.file_digest(f, "sha256").hexdigest()}


def checked(path, item, recorded=None):
    actual = metadata(path)
    if item["sha256"] and actual["sha256"] != item["sha256"]:
        raise ValueError("SHA-256 falsch: " + item["filename"])
    if item["size_bytes"] is not None and actual["size_bytes"] != item["size_bytes"]:
        raise ValueError("Größe falsch: " + item["filename"])
    if actual["size_bytes"] <= 0 or recorded is not None and actual != recorded:
        raise ValueError("Lokale Prüfdaten stimmen nicht: " + item["filename"])
    return actual


def verify_snapshot(directory):
    info = manifest()
    records = json.loads((directory / "verified.json").read_text(encoding="utf-8"))
    if records["revision"] != info["revision"]:
        raise ValueError("Falsche Modellrevision")
    for item in info["models"]:
        checked(directory / item["filename"], item, records["files"][item["filename"]])
    allowed = {item["filename"] for item in info["models"]} | {"verified.json"}
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    if actual != allowed:
        raise ValueError("Unerwartete Dateien im Snapshot")


def obtain(item, directory):
    target = directory / item["filename"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return checked(target, item)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with urllib.request.urlopen(item["url"], timeout=60) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        record = checked(temporary, item)
        temporary.replace(target)
        return record
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelle-laden", action="store_true")
    args = parser.parse_args(argv)
    if not args.modelle_laden:
        print("Kein Netzbezug ohne --modelle-laden")
        return 0
    venv = Path(sys.prefix)
    if sys.prefix == sys.base_prefix or venv.name != ".venv-spike-demon":
        parser.error("Eigene Spike-Umgebung erforderlich")
    info = manifest()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("DEMON-Code: AGPL-3.0-or-later / MIT-Anteile:", UPSTREAM, PIN)
    print("Paketinstallation noch nicht vollständig gepinnt; siehe BERICHT.md.")
    if input("Quellen und Lizenzen geprüft, Bezug bestätigen (ja/nein): ").strip() != "ja":
        return 1
    vendor = venv / "demon-src"
    if not vendor.exists():
        subprocess.run(["git", "init", str(vendor)], check=True)
        subprocess.run(["git", "-C", str(vendor), "fetch", "--depth=1", UPSTREAM, PIN], check=True)
        subprocess.run(["git", "-C", str(vendor), "checkout", "--detach", "FETCH_HEAD"], check=True)
    if subprocess.check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"], text=True).strip() != PIN:
        raise ValueError("Falscher DEMON-Commit")
    directory = venv / "weights" / "checkpoints"
    if (directory / "verified.json").exists():
        verify_snapshot(directory)
    else:
        records = {item["filename"]: obtain(item, directory) for item in info["models"]}
        (directory / "verified.json").write_text(json.dumps({"revision": info["revision"], "files": records}, indent=2), encoding="utf-8")
        verify_snapshot(directory)
    print("Geprüfter Snapshot:", directory)
    # Upstream-Lock ist im festgelegten Stand nicht über die API lesbar.
    # Wenn vorhanden, ausschließlich dessen Wheels installieren; niemals neu auflösen.
    if not (vendor / "uv.lock").is_file():
        raise RuntimeError("Upstream uv.lock fehlt; Paketpins vervollständigen, siehe Bericht")
    import os
    env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(venv), UV_PYTHON_DOWNLOADS="never")
    subprocess.run(["uv", "sync", "--locked", "--no-dev", "--no-build",
                    "--no-install-project", "--project", str(vendor)], env=env, check=True)
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    (venv / "installed.lock").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
