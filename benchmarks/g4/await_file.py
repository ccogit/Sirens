"""Auf frische, lokal erzeugte Browser-Rohmessung warten (kein Download)."""
import argparse
import json
import time
from pathlib import Path


def wait(path, seconds):
    if path.exists():
        raise ValueError("Rohmessung existiert bereits; neuen Pfad wählen")
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise TimeoutError("Keine vollständige Rohmessung")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--seconds", type=int, default=14400)
    args = parser.parse_args()
    wait(args.path, args.seconds)


if __name__ == "__main__":
    main()
