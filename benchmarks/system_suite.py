"""WP19: sequenzielle Abnahme, keine automatische Gate-Freigabe."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from benchmarks.result import METRICS, read, write
from sirens.realtime.model_registry import ModelRegistry, PROFILES

ROOT = Path(__file__).resolve().parents[1]
# Zuordnung nur für historisch abweichende Namen; neue gleichnamige Gates
# werden ohne Änderung der Suite entdeckt.
ALIASES = {"separation": ("roformer", "roformer-drumsep"),
           "stable_audio": ("stable-audio-3",),
           "magenta": ("magenta-realtime",)}
CORE = {"core": "unbekannt", "mock-e2e": "offline", "dsp": "unbekannt", "beatgrid": "offline",
        "performance-tools": "offline", "recorder": "offline",
        "integration": "unbekannt", "performance-soak": "streaming"}


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def gate_evidence(root, capability):
    """Nur explizite Freigaben, passend zum deklarierten Modus."""
    cid, mode = capability["id"], capability["mode"]
    names = {normalize(n) for n in (cid, *ALIASES.get(cid, ()))}
    folder = root / "benchmarks/results/g1"
    for path in sorted(folder.glob("*")):
        if normalize(path.stem) not in names:
            continue
        if path.suffix == ".json":
            try:
                data = read(path)
                if data["gate"] in ("green", "amber") and data["modus"] == mode:
                    return path.name
            except (OSError, ValueError, KeyError):
                continue
        if path.suffix == ".md":
            # Koordinatorentscheidung in den vorhandenen G1-Berichten.
            for line in path.read_text(encoding="utf-8").splitlines():
                if (not re.search(r"\b(?:nicht|kein|keine|rot|red)\b", line, re.I)
                        and re.search(r"(?:gate|g1).*?\b(?:grün|amber|green)\b", line, re.I) and re.search(
                        r"(?:modus[: ]+|mode[: ]+)[` ]*" + re.escape(mode) + r"\b", line, re.I)):
                    return path.name
    return None


def inventory(root=ROOT, registry=None):
    registry = registry if registry is not None else ModelRegistry(root)
    rows = [{"id": name, "modus": mode, "freigegeben": True, "g1": None}
            for name, mode in CORE.items()]
    for cap in registry.capabilities():
        if cap["mock"]:
            continue
        gate = gate_evidence(root, cap)
        rows.append({"id": cap["id"], "modus": cap["mode"],
                     "freigegeben": bool(cap["available"] and gate), "g1": gate,
                     "registry_available": cap["available"]})
    return rows


def hashes(root):
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Musikordner fehlt")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink im Prüfbestand: " + str(path.relative_to(root)))
        if path.is_file():
            with path.open("rb") as f:
                result[path.relative_to(root).as_posix()] = hashlib.file_digest(f, "sha256").hexdigest()
    return result


def process_snapshot():
    # Nur lesender Zugriff; niemals fremde Prozesse automatisch beenden.
    if os.name != "nt":
        raise RuntimeError("Hardware-Suite benötigt Windows-Prozessinventar")
    command = ("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
               "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,ParentProcessId,"
               "CreationDate,CommandLine | ConvertTo-Json -Compress")
    for attempt in range(5):
        try:
            raw = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", command],
                                          encoding="utf-8", timeout=60)
            data = json.loads(raw.lstrip("\ufeff"))
            rows = data if isinstance(data, list) else [data]
            if not rows or any(not isinstance(row, dict)
                               or type(row.get("ProcessId")) is not int
                               or type(row.get("ParentProcessId")) is not int
                               for row in rows):
                raise ValueError("Ungültiges Prozessinventar")
            return rows
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            if attempt == 4:
                raise RuntimeError(f"Prozessinventar nach 5 Versuchen fehlgeschlagen: {exc}") from exc
            time.sleep(.5)


def worker_processes(rows, root=ROOT, known=()):
    prefix = str(root).lower().replace("\\", "/").rstrip("/") + "/"
    seeds = {r["ProcessId"] for r in rows
             if (r["ProcessId"], str(r.get("CreationDate"))) in known}
    for row in rows:
        cmd = (row.get("CommandLine") or "").lower().replace("\\", "/")
        if prefix + "workers/" in cmd or prefix + "sirens/realtime/sidecar.py" in cmd:
            seeds.add(row["ProcessId"])
        elif "sirens.realtime.sidecar" in cmd:
            seeds.add(row["ProcessId"])
    # Auch die Kindprozesse der identifizierten Worker erfassen.
    while True:
        extended = seeds | {r["ProcessId"] for r in rows if r.get("ParentProcessId") in seeds}
        if extended == seeds:
            break
        seeds = extended
    return {(r["ProcessId"], str(r.get("CreationDate"))) for r in rows if r["ProcessId"] in seeds}


def verify(before_hash, after_hash, before_workers, after_workers):
    errors = []
    if before_hash != after_hash:
        errors.append("Originalbestand verändert")
    if after_workers - before_workers:
        errors.append("Verwaiste oder noch laufende neue Worker: " +
                      str(sorted(after_workers - before_workers)))
    return errors


def report(path, rows, errors, dry):
    machine = dict(os=platform.system() + " " + platform.release(), python=sys.version, node=None, ffmpeg=None,
                   gpus=None, wsl=None, disk=None, git=None, notes=[])
    if not dry and os.name == "nt":
        from benchmarks.baseline import collect
        try:
            machine = collect()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            errors.append("Rechnerdaten: " + str(exc))
    write(path, dict(wp="WP19", kandidat="Systemabnahme G4",
                     zeitpunkt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     befehl="benchmarks/suite.ps1" + (" -DryRun" if dry else ""),
                     gate="nicht_gemessen", modus="unbekannt", rechner=machine,
                     messwerte={phase: dict.fromkeys(METRICS) for phase in ("kalt", "warm")},
                     notizen=errors + ["Keine automatische Gate-Entscheidung."],
                     funktionen=rows, profile=list(PROFILES), dry_run=dry))


def run(out, music, plan, dry=False, snapshot=process_snapshot):
    out = out.resolve()
    if ROOT == out or ROOT in out.parents:
        raise ValueError("Ausgabe außerhalb des Repositorys erforderlich")
    if music is not None:
        music = music.resolve(strict=True)
        if out == music or music in out.parents or out in music.parents:
            raise ValueError("Ausgabe und Musikbestand müssen getrennt sein")
    out.mkdir(parents=True, exist_ok=False)
    print("Suite-Ausgabeordner: " + str(out), flush=True)
    rows = inventory()
    errors = []
    before_hash = hashes(music) if music else {}
    before_workers = set() if dry else None
    initial_failure = None
    if not dry:
        try:
            before_workers = worker_processes(snapshot())
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            initial_failure = exc
    known_workers = set(before_workers or ())
    try:
        for row in rows:
            cid = row["id"]
            row["status"] = "nicht_gemessen"
            row["minimum_seconds"] = (7200 if cid == "performance-soak" else
                                      1800 if row["modus"] == "streaming" and cid not in CORE else None)
            if dry:
                continue
            if row.get("registry_available") and not row["g1"]:
                errors.append("Registry meldet Verfügbarkeit ohne passendes G1: " + cid)
            if not row["freigegeben"]:
                continue
            # Bewusst lokale, explizit bereitgestellte argv-Liste; keine Shell.
            job = plan.get(cid)
            if not job:
                errors.append("Messpfad fehlt: " + cid)
                continue
            try:
                if initial_failure is not None:
                    exc, initial_failure = initial_failure, None
                    raise RuntimeError("Prozessinventar vor Messstart: " + str(exc)) from exc
                if before_workers is None:
                    before_workers = worker_processes(snapshot())
                    known_workers.update(before_workers)
                if job.get("instruction"):
                    print(job["instruction"], flush=True)
                steps = job.get("steps", [job.get("argv")])
                if not isinstance(steps, list) or not steps:
                    raise ValueError("steps muss eine nichtleere Liste sein")
                result_path = out / (cid + ".json")
                if result_path.exists():
                    raise ValueError("Messdatei existiert bereits")
                with (out / (cid + ".log")).open("wb") as log:
                    for argv in steps:
                        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
                            raise ValueError("argv muss eine nichtleere Textliste sein")
                        argv = [a.replace("{out}", str(result_path)).replace("{dir}", str(out))
                                .replace("{python}", sys.executable) for a in argv]
                        with subprocess.Popen(argv, cwd=ROOT,
                                              stdout=None if job.get("interactive") else log,
                                              stderr=None if job.get("interactive") else subprocess.STDOUT) as proc:
                            deadline = time.monotonic() + job.get("timeout", 14400)
                            try:
                                while proc.poll() is None:
                                    if time.monotonic() >= deadline:
                                        raise subprocess.TimeoutExpired(argv, job.get("timeout", 14400))
                                    known_workers.update(worker_processes(snapshot(), known=known_workers))
                                    try:
                                        proc.wait(timeout=2)
                                    except subprocess.TimeoutExpired:
                                        pass
                            finally:
                                if proc.poll() is None:
                                    proc.kill()
                                    proc.wait(timeout=10)
                            if proc.returncode:
                                raise subprocess.CalledProcessError(proc.returncode, argv)
                evidence = read(result_path)
                if evidence["modus"] != row["modus"] and row["modus"] != "unbekannt":
                    raise ValueError("Messmodus stimmt nicht überein")
                row["ergebnis"] = result_path.name
                if evidence["gate"] == "red":
                    raise ValueError("Messbericht meldet rot")
                if row["minimum_seconds"] is not None:
                    if evidence["messwerte"]["warm"]["underruns"] != 0:
                        raise ValueError("Soak: unerwartete Underruns oder fehlender Zähler")
                    elapsed = evidence.get("elapsed_seconds")
                    if type(elapsed) not in (int, float) or elapsed < row["minimum_seconds"]:
                        raise ValueError("Soak-Dauer nicht belegt")
                row["status"] = "messdatei_vorhanden"
            except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
                row["status"] = "fehler"
                row["fehler"] = str(exc)
                errors.append(cid + ": " + str(exc))
    finally:
        try:
            if before_workers is None:
                errors.append("Nachkontrolle: Kein ursprüngliches Prozessinventar verfügbar" +
                              (": " + str(initial_failure) if initial_failure else ""))
            after_workers = worker_processes(snapshot(), known=known_workers) if not dry else set()
            errors.extend(verify(before_hash, hashes(music) if music else {},
                                 before_workers if before_workers is not None else after_workers, after_workers))
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            errors.append("Nachkontrolle: " + str(exc))
        report(out / "suite.json", rows, errors, dry)
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--music-root", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and (not args.music_root or not args.plan):
        parser.error("Hardwarelauf benötigt --music-root und --plan")
    plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else {}
    if not isinstance(plan, dict):
        parser.error("Plan muss ein JSON-Objekt sein")
    if args.dry_run and args.music_root is None:
        with tempfile.TemporaryDirectory() as tmp:
            music = Path(tmp)
            (music / "fixture").write_bytes(b"synthetischer Originalbestand")
            status = run(args.out, music, plan, True)
    else:
        status = run(args.out, args.music_root, plan, args.dry_run)
    print(args.out / "suite.json")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
