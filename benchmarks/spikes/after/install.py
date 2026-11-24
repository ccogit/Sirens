"""AFTER: kein Netzbezug unbekannter Gewichte; geprüften lokalen Export übernehmen."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def register(source, expected, license_text, directory):
    if not source.is_file() or source.suffix != ".ts" or not license_text.strip():
        raise ValueError("Lokaler .ts-Export und konkrete Gewichtslizenz erforderlich")
    if len(expected) != 64 or digest(source) != expected.lower():
        raise ValueError("SHA-256 des lokalen Exports stimmt nicht")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "after-audio-to-audio.ts"
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as temp:
        partial = Path(temp.name)
    try:
        shutil.copyfile(source, partial)
        if digest(partial) != expected.lower():
            raise ValueError("SHA-256 der Kopie stimmt nicht")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    receipt = dict(filename=target.name, size_bytes=target.stat().st_size,
                   sha256=expected.lower(), license=license_text,
                   source=str(source.resolve()), trusted_local_export=True)
    (directory / "local-weight.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelle-laden", action="store_true")
    p.add_argument("--lokaler-export", type=Path)
    p.add_argument("--sha256")
    p.add_argument("--gewichtslizenz")
    args = p.parse_args(argv)
    if not args.modelle_laden:
        print("Kein Netzbezug ohne --modelle-laden")
        return 0
    venv = Path(sys.prefix)
    if sys.prefix == sys.base_prefix or venv.name != ".venv-spike-after":
        p.error("Eigene AFTER-Umgebung erforderlich")
    print((HERE / "weights.json").read_text(encoding="utf-8"))
    if not (args.lokaler_export and args.sha256 and args.gewichtslizenz):
        p.error("Share manuell prüfen; vertrauenswürdiger vollständiger v2-Export, Hash und Gewichtslizenz fehlen")
    if input("Herkunft, Lizenz und ausführbaren lokalen Export bestätigen (ja/nein): ").strip() != "ja":
        return 1
    print("Geprüftes Modell:", register(args.lokaler_export, args.sha256,
                                            args.gewichtslizenz, venv / "weights"))
    pins = [line for line in (HERE / "requirements.lock").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:",
                    "--index-url", "https://download.pytorch.org/whl/cu128", *pins], check=True)
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    (venv / "installed.lock").write_text(subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
