"""Coordinator-only installation; never called by production or CI."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, default=Path(__file__).parent / ".venv")
    parser.add_argument("--wheelhouse", type=Path, required=True,
                        help="approved local wheel directory; no network")
    parser.add_argument("--install", action="store_true",
                        help="actually create venv and install; default prints plan")
    args = parser.parse_args()
    venv = args.venv.resolve()
    if not venv.is_relative_to(Path(__file__).resolve().parent):
        parser.error("venv must be under workers/production_assets")
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    commands = [[sys.executable, "-m", "venv", str(venv)],
                [str(python), "-m", "pip", "install", "--no-index", "--only-binary=:all:",
                 "--find-links", str(args.wheelhouse.resolve()), "qwen-tts==0.1.1",
                 "soundfile==0.13.1", "scipy==1.15.3"]]
    for command in commands:
        print(command)
        if args.install:
            subprocess.run(command, check=True, shell=False)


if __name__ == "__main__":
    main()
