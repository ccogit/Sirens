"""Datensparsame Rechnerbeschreibung ohne Modell- oder Netzaufrufe."""
import argparse
import csv
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect(root: Path = ROOT) -> dict:
    notes = []

    def run(*args):
        try:
            result = subprocess.run(args, cwd=root, capture_output=True, timeout=10)
            if result.returncode == 0:
                raw = result.stdout
                if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                    return raw.decode("utf-16", errors="replace")
                if b"\x00" in raw:
                    return raw.decode("utf-16-le", errors="replace")
                return raw.decode("utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            pass
        notes.append(f"{args[0]}: nicht verfügbar oder Aufruf fehlgeschlagen")
        return None

    def version(output, pattern, label):
        if output is None:
            return None
        match = re.search(pattern, output)
        if match is None:
            notes.append(f"{label}: Version nicht erkennbar")
        return match.group(1) if match else None

    gpu_output = run("nvidia-smi", "--query-gpu=driver_version,name,memory.total,memory.free",
                     "--format=csv,noheader,nounits")
    gpus = None
    if gpu_output is not None:
        gpus = []
        for row in csv.reader(gpu_output.splitlines(), skipinitialspace=True):
            if not row:
                continue
            try:
                driver, name, total, free = (part.strip() for part in row)
                # Nur Produktbezeichnungen, keine frei formatierten Pfade oder Hostnamen.
                if not re.fullmatch(r"(?:NVIDIA|GeForce|Quadro|Tesla|RTX) [A-Za-z0-9 ._()+-]+", name):
                    raise ValueError
                if not re.fullmatch(r"[0-9.]+", driver):
                    raise ValueError
                total, free = int(total), int(free)
                if not 0 <= free <= total:
                    raise ValueError
                gpus.append({"driver": driver, "name": name, "vram_total_mib": total, "vram_free_mib": free})
            except ValueError:
                notes.append("nvidia-smi: GPU-Zeile nicht auswertbar")
        if not gpus:
            gpus = None
    git_sha = version(run("git", "rev-parse", "HEAD"), r"\A([0-9a-f]{40})(?:\s|$)", "git")
    status = run("git", "status", "--porcelain")
    # Nie den Inhalt des Status oder die Namen von WSL-Distributionen speichern.
    wsl = run("wsl", "--list", "--quiet")
    try:
        free_bytes = shutil.disk_usage(root).free
    except OSError:
        free_bytes = None
        notes.append("Plattenplatz nicht ermittelbar")
    # Kein platform.platform()/uname(): enthält u. U. Rechnernamen oder Build-Pfade.
    os_name = platform.system()
    release = platform.release()
    safe_release = re.match(r"[0-9]+(?:\.[0-9]+)*", release)
    if not safe_release:
        notes.append("OS-Release nicht numerisch")
    drive = root.resolve().drive
    # UNC-Freigaben können personenbezogene Namen enthalten.
    drive = drive if re.fullmatch(r"[A-Za-z]:", drive) else None
    return {
        "os": {"system": os_name if os_name in ("Windows", "Linux", "Darwin", "FreeBSD") else None,
               "release": safe_release.group() if safe_release else None},
        "python": platform.python_version(),
        "node": version(run("node", "--version"), r"\Av?([0-9]+\.[0-9]+\.[0-9]+)", "Node"),
        "ffmpeg": version(run("ffmpeg", "-version"), r"\Affmpeg version n?([0-9]+(?:\.[0-9]+)*)", "ffmpeg"),
        "gpus": gpus,
        "wsl": True if wsl is not None else None,
        "disk": {"drive": drive, "free_bytes": free_bytes},
        "git": {"sha": git_sha, "clean": not bool(status.strip()) if status is not None else None},
        "audio_device": None,
        "notes": notes + ["Audio-Gerät und Treiber separat am Zielrechner erfassen (nicht gemessen)"]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = collect()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
