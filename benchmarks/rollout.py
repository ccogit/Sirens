"""Installationsversuch am Zielrechner; keine Audio-/Modelllatenz messen."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from benchmarks.baseline import collect
from benchmarks.result import METRICS, validate
import json

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ("demon", "rave", "after", "magenta", "sam_audio", "separation", "stable_audio")


def result(worker, code, machine, dry_run):
    return validate({
        "wp": "WP20", "kandidat": worker, "zeitpunkt": datetime.now(timezone.utc).isoformat(),
        "befehl": "python -m benchmarks.rollout --worker " + worker + (" --dry-run" if dry_run else " --install"),
        "gate": "nicht_gemessen", "modus": "unbekannt", "rechner": machine,
        "messwerte": {phase: dict.fromkeys(METRICS) for phase in ("warm", "kalt")},
        "notizen": ["DryRun" if dry_run else "Expliziter Installationsversuch",
                     "Installer-Exitcode: " + str(code),
                     "Kein G4-Entscheid; Legacy-Sichtprüfung, Lizenz und Hörtest separat."]
    })


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", required=True, choices=WORKERS)
    p.add_argument("--out", required=True, type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--install", action="store_true")
    p.add_argument("--disk-bytes", type=int)
    p.add_argument("--vram-mib", type=int)
    p.add_argument("--accept-incomplete-locks", action="store_true")
    args = p.parse_args()
    dest = args.out.resolve()
    if dest.is_relative_to(ROOT) or dest.exists():
        p.error("Neue Ergebnisdatei außerhalb des Repositorys erforderlich")
    if args.install and (not args.disk_bytes or args.disk_bytes <= 0
                         or not args.vram_mib or args.vram_mib <= 0):
        p.error("Positive Mindestwerte für Speicherplatz und VRAM erforderlich")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        p.error("PowerShell fehlt")
    cmd = [shell, "-NoProfile", "-File", str(ROOT / "scripts" / "rt-install.ps1"),
           "-Worker", args.worker]
    if args.dry_run:
        cmd.append("-DryRun")
    else:
        cmd.extend(["-ModelleLaden", "-MinFreeDiskBytes", str(args.disk_bytes),
                    "-MinFreeVramMiB", str(args.vram_mib)])
        if args.accept_incomplete_locks:
            cmd.append("-UnvollstaendigeLocksAkzeptieren")
    code = subprocess.run(cmd, cwd=ROOT, check=False).returncode
    data = result(args.worker, code, collect(), args.dry_run)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    return int(code != 0)


if __name__ == "__main__":
    raise SystemExit(main())
