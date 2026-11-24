"""Expliziter Bezug des geprüften RoFormer-Gewichts und der MSST-Umgebung."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

PIN = "1523206d12a521bdb20673726562524cf0f9635b"
UPSTREAM = "https://github.com/ZFTurbo/Music-Source-Separation-Training.git"
HERE = Path(__file__).resolve().parent


def valid_weight(path, item):
    if not path.is_file() or path.stat().st_size != item["size_bytes"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]


def obtain_weight(item, directory):
    if not item["approved"] or not item["sha256"] or not item["size_bytes"]:
        raise ValueError("Gewicht nicht freigegeben")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / item["filename"]
    if target.exists():
        if not valid_weight(target, item):
            raise ValueError("Vorhandenes Gewicht hat falsche Größe oder SHA-256")
        return target
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as f:
        temporary = Path(f.name)
    try:
        total = 0
        with urllib.request.urlopen(item["url"], timeout=60) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > item["size_bytes"]:
                    raise ValueError("Download größer als erwartet")
                output.write(block)
        if not valid_weight(temporary, item):
            raise ValueError("Download hat falsche Größe oder SHA-256")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelle-laden", action="store_true")
    args = p.parse_args(argv)
    if not args.modelle_laden:
        print("Kein Netzbezug ohne --modelle-laden")
        return 0
    venv = Path(sys.prefix)
    if sys.prefix == sys.base_prefix or venv.name != ".venv-spike-roformer-drumsep":
        p.error("Eigene Spike-Umgebung erforderlich")
    item = json.loads((HERE / "weights.json").read_text(encoding="utf-8"))["models"][0]
    print(json.dumps(item, indent=2, ensure_ascii=False))
    print("Code: " + UPSTREAM + " @ " + PIN + " (MIT)")
    print("Pakete: PyPI und https://download.pytorch.org/whl/cu128; direkte Pins:")
    print((HERE / "requirements.lock").read_text(encoding="utf-8"))
    print("Transitive Paketversionen noch nicht eingefroren; DrumSep bleibt gesperrt.")
    if input("Bezug für lokalen Versuch bestätigen (ja/nein): ").strip() != "ja":
        return 1
    def command(*args):
        subprocess.run(args, check=True)
    source = venv / "msst"
    if not source.exists():
        command("git", "init", str(source))
        command("git", "-C", str(source), "fetch", "--depth=1", UPSTREAM, PIN)
        command("git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD")
    if subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                               text=True).strip() != PIN:
        raise ValueError("Falscher MSST-Commit")
    pins = [line for line in (HERE / "requirements.lock").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    command(sys.executable, "-m", "pip", "install", "--index-url",
            "https://download.pytorch.org/whl/cu128", *pins[:2])
    command(sys.executable, "-m", "pip", "install", "--index-url",
            "https://pypi.org/simple", *pins[2:])
    command(sys.executable, "-m", "pip", "check")
    (venv / "installed.lock").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")
    target = obtain_weight(item, venv / "weights")
    print("Geprüftes Gewicht: " + str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
