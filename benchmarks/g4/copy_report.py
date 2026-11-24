"""Validiertes vorhandenes Ergebnis ohne Audio in den Suite-Bericht übernehmen."""
import argparse
from pathlib import Path
from benchmarks.result import read, write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    if a.out.exists():
        p.error("Ausgabe existiert bereits")
    write(a.out, read(a.source))


if __name__ == "__main__":
    main()
