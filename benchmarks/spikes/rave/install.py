"""Expliziter Bezug des gepinnten IIL-RAVE-Exports."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent


def manifest():
    return json.loads((HERE / "weights.json").read_text(encoding="utf-8"))["models"][0]


def verify(path, item):
    if not path.is_file() or path.stat().st_size != item["size_bytes"]:
        raise ValueError("Modellgröße stimmt nicht")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != item["sha256"]:
            raise ValueError("Modellhash stimmt nicht")


def obtain_weight(item, directory):
    if not item["approved"] or not item["size_bytes"] or not item["sha256"]:
        raise ValueError("Gewicht nicht freigegeben")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / item["filename"]
    if target.exists():
        verify(target, item)
        return target
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as tmp:
        partial = Path(tmp.name)
    try:
        with urllib.request.urlopen(item["url"], timeout=60) as response, partial.open("wb") as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > item["size_bytes"]:
                    raise ValueError("Download größer als erwartet")
                out.write(chunk)
        verify(partial, item)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelle-laden", action="store_true")
    args = p.parse_args(argv)
    if not args.modelle_laden:
        print("Kein Netzbezug ohne --modelle-laden")
        return 0
    venv = Path(sys.prefix)
    if sys.prefix == sys.base_prefix or venv.name != ".venv-spike-rave":
        p.error("Eigene RAVE-Umgebung erforderlich")
    item = manifest()
    print(json.dumps(item, ensure_ascii=False, indent=2))
    print("TorchScript kann Code ausführen; nur bei Vertrauen in den Urheber verwenden.")
    print("Paketquelle: https://download.pytorch.org/whl/cu128")
    if input("Nichtkommerzielle Nutzung, Quelle und ausführbaren Export bestätigen (ja/nein): ").strip() != "ja":
        return 1
    pin = (HERE / "requirements.lock").read_text(encoding="utf-8")
    pins = [line for line in pin.splitlines() if line and not line.startswith("#")]
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:",
                    "--index-url", "https://download.pytorch.org/whl/cu128", *pins], check=True)
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    (venv / "installed.lock").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")
    print("Geprüftes Modell:", obtain_weight(item, venv / "weights"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
