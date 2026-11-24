"""File-only Ableton exchange. Never controls Live or starts a writer in Live."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from contextlib import contextmanager
from uuid import uuid4

from .contracts import (
    ContractError, read_manifest, safe_path, sha256_file, validate_ableton,
    validate_plan, validate_return, validate_stems, validate_wav,
)

_CAPS = ("live_version", "edition", "max_for_live", "producer_pal",
         "secondroom", "wb", "live_writer", "guard_status", "capture",
         "saved_set", "open_set", "render", "reason")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


def _require(ok, reason):
    if not ok:
        raise ContractError(reason)


def _id(value):
    _require(isinstance(value, str) and _ID.fullmatch(value)
             and not value.endswith(".")
             and value.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL",
                 *("COM" + str(n) for n in range(1, 10)),
                 *("LPT" + str(n) for n in range(1, 10))}, "unsafe identifier")
    return value


def _json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def probe(observations=None):
    """Normalize coordinator evidence; file adapter itself has no Live backend."""
    data = dict.fromkeys(_CAPS)
    data.update(schema_version=1, open_set=False, render=False,
                reason="Live not verified; manual import/export and offline render",
                evidence=[])
    if observations is not None:
        _require(observations.get("schema_version") == 1, "capability schema")
        for key in _CAPS:
            if key in observations:
                data[key] = observations[key]
        for key in ("max_for_live", "open_set", "render", "capture", "saved_set"):
            _require(data[key] is None or type(data[key]) is bool, "capability " + key)
        evidence = observations.get("evidence", [])
        _require(isinstance(evidence, list), "capability evidence")
        for item in evidence:
            _require(isinstance(item, dict) and isinstance(item.get("operation"), str)
                     and (item.get("result") is None or type(item["result"]) is bool)
                     and "version" in item and "evidence" in item, "capability receipt")
        data["evidence"] = evidence
    # Even positive external observations do not enable a local Live writer.
    data["observed_open_set"] = data["open_set"]
    data["observed_render"] = data["render"]
    data.update(open_set=False, render=False, adapter="import_bundle",
                reason="No Live writer in Sirens; explicit manual import/export")
    return data


def wb_source(plan, track, run_id):
    """Translate contract ticks to the existing AMM wb-midi-source/1."""
    validate_plan(plan)
    _require(track["backend"] == "instrument", "not a MIDI instrument")
    tid = _id(track["id"])
    return dict(schema="wb-midi-source/1", id=run_id, revision=1, title=tid,
                tempo=plan["bpm"], time_sig=plan["meter"],
                markers=[dict(beat=s["start_bar"] * 4, name=s["id"])
                         for s in plan["sections"]],
                tracks=[dict(id=tid, name=tid, kind="midi",
                             drums=track["role"] in {"drums", "drum", "kick", "snare",
                                                     "hat", "hihat", "percussion", "clap"})],
                clips=[dict(track_id=tid, start_beats=0,
                            length_beats=plan["total_bars"] * 4,
                            notes=[dict(pitch=e["note"], start=e["tick"] / 960,
                                        duration=e["duration_ticks"] / 960,
                                        velocity=e["velocity"]) for e in track["events"]])])


def wb_writer(checkout):
    """Trusted local AMM checkout, explicit configuration, no install/network."""
    tools = Path(checkout).resolve(strict=True) / "music-workbench" / "tools"
    _require((tools / "music_sources" / "midi.py").is_file(), "AMM MIDI writer missing")
    bridge = Path(__file__).resolve().parents[2] / "workers" / "production_ableton" / "wb_midi.py"

    def write(document, destination):
        result = subprocess.run([sys.executable, "-I", str(bridge), str(tools),
                                 str(destination)], input=json.dumps(document),
                                text=True, capture_output=True, timeout=60, check=False,
                                env={k: os.environ[k] for k in ("PATH", "SYSTEMROOT",
                                     "TEMP", "TMP", "LANG") if k in os.environ})
        _require(result.returncode == 0, "AMM MIDI writer failed")
        return json.loads(result.stdout)
    return write


def _midi_header(path, *, instrument=True):
    with path.open("rb") as stream:
        header = stream.read(14)
        _require(len(header) == 14 and header[:4] == b"MThd", "invalid MIDI")
        length, kind, tracks, ppq = struct.unpack(">IHHH", header[4:])
        _require((length, kind, ppq) == (6, 1, 960) and tracks >= (2 if instrument else 1),
                 "MIDI must be type 1, 960 PPQ with instrument")
        for _ in range(tracks):
            chunk = stream.read(8)
            _require(len(chunk) == 8 and chunk[:4] == b"MTrk", "invalid MIDI chunk")
            size = struct.unpack(">I", chunk[4:])[0]
            _require(size <= path.stat().st_size - stream.tell(), "truncated MIDI")
            stream.seek(size, 1)
        _require(not stream.read(1), "trailing MIDI data")


@contextmanager
def _publish(root, identity):
    """Stage on same filesystem, serialize cooperating publishers, never replace."""
    root = Path(root)
    _require(not root.is_symlink(), "symlink root")
    root.mkdir(parents=True, exist_ok=True)
    identity = _id(identity)
    final = safe_path(root, identity)
    lock = safe_path(root, "." + identity + ".lock")
    try:
        lock.mkdir()
    except FileExistsError:
        raise ContractError("publication already in progress") from None
    try:
        _require(not final.exists(), "destination exists")
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=root) as tmp:
            stage = Path(tmp) / "payload"
            stage.mkdir()
            yield stage
            _require(not final.exists() and not final.is_symlink(), "destination exists")
            os.rename(stage, final)
    finally:
        lock.rmdir()


def _wav_info(path, frames=None, channels=None):
    validate_wav(path, frames=frames, channels=channels)
    with wave.open(str(path), "rb") as w:
        return dict(frames=w.getnframes(), channels=w.getnchannels(),
                    sample_rate=w.getframerate(), sha256=sha256_file(path))


def _copy(source, dest, digest=None):
    _require(source.is_file() and not source.is_symlink(), "missing or unsafe file")
    before = source.stat()
    with source.open("rb") as inp, dest.open("xb") as out:
        shutil.copyfileobj(inp, out)
    after = source.stat()
    _require((before.st_size, before.st_mtime_ns, before.st_ino) ==
             (after.st_size, after.st_mtime_ns, after.st_ino), "source changed")
    actual = sha256_file(dest)
    _require(actual == sha256_file(source) and (digest is None or actual == digest),
             "copy hash mismatch")
    return actual


def export_bundle(run_dir, exports_root, run_id, export_id=None, *,
                  midi_writer=None, observations=None):
    """Create an immutable import bundle, and isolated return/<id> inbox.

    MIDI instruments require the existing AMM writer (injected only in tests).
    Never silently downgrade an instrument to an audio-only package.
    """
    run_id, export_id = _id(run_id), _id(export_id or uuid4().hex)
    run = Path(run_dir)
    _require(not run.is_symlink() and run.name == run_id, "run binding")
    plan = validate_plan(read_manifest(safe_path(run, "plan.json")))
    stems = validate_stems(read_manifest(safe_path(run, "stems.json")), plan=plan, root=run)
    if any(t["backend"] == "instrument" for t in plan["tracks"]):
        _require(callable(midi_writer), "configure existing AMM MIDI writer")
    caps = probe(observations)
    sections = [dict(id=s["id"], start_bar=s["start_bar"], bars=s["bars"],
                     label=s["id"]) for s in plan["sections"]]
    manifest = dict(schema_version=1, run_id=run_id, export_id=export_id,
                    bpm=plan["bpm"], meter=plan["meter"], ppq=960, sample_rate=48000,
                    frames=stems["frames"], sections=sections, tracks=[],
                    reference_mix="reference_mix.wav", project_file=None,
                    mode="import_bundle", capabilities=caps,
                    warnings=["Manual Live import; Warp off; reference mix muted",
                              "Use audio OR MIDI per instrument, not both"])
    by_id = {s["track_id"]: s for s in stems["stems"]}
    root = Path(exports_root)
    _require(export_id.lower() != "return", "reserved export ID")
    with _publish(root, export_id) as stage:
        for folder in ("audio", "MIDI"):
            (stage / folder).mkdir()
        automation = {}
        names = set()
        for track in plan["tracks"]:
            tid = _id(track["id"])
            _require(tid.casefold() not in names, "case-insensitive track collision")
            names.add(tid.casefold())
            stem = by_id[tid]
            _require(stem["role"] == track["role"], "stem role mismatch")
            audio = "audio/" + tid + ".wav"
            _copy(safe_path(run, stem["file"]), stage / audio, stem["sha256"])
            midi = None
            if track["backend"] == "instrument":
                midi = "MIDI/" + tid + ".mid"
                receipt = midi_writer(wb_source(plan, track, run_id), stage / midi)
                _require(isinstance(receipt, dict) and
                         [t["track_id"] for t in receipt.get("tracks", [])] == [tid],
                         "MIDI receipt track mismatch")
                _midi_header(stage / midi)
            automation[tid] = track["automation"]
            manifest["tracks"].append(dict(track_id=tid, role=track["role"],
                                           audio_file=audio, midi_file=midi,
                                           patch=track["patch"],
                                           automation_file="automation.json",
                                           sha256=stem["sha256"], source=stem["source"],
                                           playback="audio", warp=False))
        mix = safe_path(run, "mix.wav")
        info = _wav_info(mix, frames=stems["frames"], channels=2)
        _copy(mix, stage / manifest["reference_mix"], info["sha256"])
        manifest["reference_mix_sha256"] = info["sha256"]
        _json(stage / "sections.json", dict(schema_version=1, sections=sections))
        with (stage / "sections.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", "start_bar", "bars", "label"])
            writer.writeheader()
            writer.writerows(sections)
        _json(stage / "automation.json", dict(schema_version=1, tracks=automation))
        (stage / "IMPORT.md").write_text(
            f"# Import {export_id}\nNew isolated Set; {plan['bpm']} BPM, 4/4. "
            "Import all audio from 1.1.1, disable and verify Warp. "
            "Add locators at start_bar + 1. Reference mix is muted. "
            "Use audio fallback by default. To edit MIDI, use the corresponding "
            "instrument/patch only when available, mute its audio fallback first. "
            "Automation is documented in automation.json; apply manually. "
            "Save/Collect All and Save in Live if desired. Export stereo PCM24 "
            "48 kHz WAV from 1.1.1 to the assigned return folder as master.wav; "
            "disable normalization and do not add another mastering pass.\n",
            encoding="utf-8")
        _json(stage / "ableton.json", manifest)
        validate_ableton(manifest, root=stage)
        inbox_parent = safe_path(root, "return")
        inbox_parent.mkdir(exist_ok=True)
        inbox = safe_path(inbox_parent, export_id)
        inbox.mkdir()
    return manifest


def _stable(paths, seconds):
    _require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
             "invalid stability interval")
    def snapshot():
        result = []
        for p in paths:
            _require(p.is_file() and not p.is_symlink(), "return file missing or symlink")
            s = p.stat()
            result.append((s.st_size, s.st_mtime_ns, s.st_ino, sha256_file(p)))
        return result
    old = snapshot()
    time.sleep(seconds)
    _require(old == snapshot(), "return still changing")
    return [entry[-1] for entry in old]


def import_return(exports_root, export_id, runs_root, *, confirm=False,
                  revision_id=None, stability_seconds=1.0):
    """Explicit confirmed import, no mutation of source or existing runs."""
    _require(confirm is True, "return confirmation required")
    export_id = _id(export_id)
    root = Path(exports_root)
    exported = safe_path(root, export_id)
    original = validate_ableton(read_manifest(safe_path(exported, "ableton.json")),
                               root=exported)
    _require(original["export_id"] == export_id, "export ID mismatch")
    reference = safe_path(exported, original["reference_mix"])
    _require(original.get("reference_mix_sha256") == sha256_file(reference),
             "reference mix hash mismatch")
    parent = _id(original["run_id"])
    runs = Path(runs_root)
    _require(safe_path(runs, parent).is_dir(), "parent run missing")
    inbox = safe_path(root, "return/" + export_id)
    manifest_path = safe_path(inbox, "return.json")
    manual = not manifest_path.exists()
    if not manual:
        data = read_manifest(manifest_path)
    else:
        _require({p.name for p in inbox.iterdir()} == {"master.wav"},
                 "ambiguous manual return; use master.wav or return.json")
        data = dict(schema_version=1, export_id=export_id, parent_run_id=parent,
                    master_file="master.wav", notes="")
    validate_return(data, root=inbox)
    _require(data["export_id"] == export_id and data["parent_run_id"] == parent,
             "return/export binding mismatch")
    bpm = data.get("bpm")
    _require(bpm is None or (type(bpm) in (int, float) and math.isfinite(bpm) and bpm > 0),
             "invalid return tempo")
    files = [("master", data["master_file"], data.get("master_sha256"))]
    metadata = {}
    for kind in ("stems", "midi"):
        for item in data.get(kind, []):
            if isinstance(item, dict) and item.get("track_id") is not None:
                metadata[item["file"]] = _id(item["track_id"])
            files.append((kind, item if isinstance(item, str) else item["file"],
                          None if isinstance(item, str) else item.get("sha256")))
    if data.get("project_file") is not None:
        files.append(("project", data["project_file"], None))
    _require(len({f[1].casefold() for f in files}) == len(files), "duplicate return path")
    paths = [safe_path(inbox, f[1]) for f in files]
    if manifest_path.exists():
        paths_for_check = paths + [manifest_path]
        manifest_digest = sha256_file(manifest_path)
        _require(data == read_manifest(manifest_path), "return manifest changed")
    else:
        paths_for_check = paths
        manifest_digest = None
    stable_digests = _stable(paths_for_check, stability_seconds)
    before = stable_digests[:len(paths)]
    _require(manifest_digest is None or manifest_digest == stable_digests[-1],
             "return manifest changed")
    if manual:
        data["master_sha256"] = before[0]
    revision_id = _id(revision_id or uuid4().hex)
    with _publish(runs, revision_id) as stage:
        info = _wav_info(paths[0], channels=2)
        records = []
        for i, ((kind, rel, claimed), path) in enumerate(zip(files, paths)):
            _require(claimed is None or claimed == before[i], "return hash mismatch")
            if kind == "master":
                dest = "master.wav"
            else:
                suffix = {"stems": ".wav", "midi": ".mid", "project": ".als"}[kind]
                _require(path.suffix.lower() == suffix, "return extension mismatch")
                dest = kind + "/" + str(i) + suffix
                (stage / kind).mkdir(exist_ok=True)
                if kind == "stems":
                    _wav_info(path, frames=info["frames"])
                elif kind == "midi":
                    _midi_header(path, instrument=False)
            digest = _copy(path, stage / dest, before[i])
            record = dict(kind=kind, file=dest, original_file=rel, sha256=digest)
            if rel in metadata:
                record["track_id"] = metadata[rel]
            records.append(record)
        _require(before == [sha256_file(p) for p in paths], "return changed during import")
        _require(manifest_digest is None or manifest_digest == sha256_file(manifest_path),
                 "return manifest changed during import")
        result = dict(schema_version=1, run_id=revision_id, parent_run_id=parent,
                      export_id=export_id, source="ableton_return", master_file="master.wav",
                      master_sha256=info["sha256"], frames=info["frames"], sample_rate=48000,
                      stereo_only=not any(f[0] == "stems" for f in files),
                      duration_changed=info["frames"] != original["frames"],
                      original_frames=original["frames"], original_bpm=original["bpm"],
                      bpm=bpm, tempo_changed=None if bpm is None else bpm != original["bpm"],
                      notes=data["notes"], files=records,
                      mastering_required=False, published=False)
        _json(stage / "return.json", result)
        # A prepared revision is not a completed production run: K08 measures
        # and registers the returned audio, without automatic mastering.
        _json(stage / "status.json", dict(schema_version=1, status="queued",
              stage="ableton_return", progress=None, error=None,
              timestamps={"queued": datetime.now(timezone.utc).isoformat()},
              run_id=revision_id, parent_run_id=parent))
        if manual:
            # Exclusive, atomic publication of the derived inbox receipt.
            with tempfile.TemporaryDirectory(prefix=".receipt-", dir=inbox) as tmp:
                receipt = Path(tmp) / "return.json"
                _json(receipt, data)
                try:
                    os.link(receipt, manifest_path)
                except FileExistsError:
                    raise ContractError("return manifest appeared during import") from None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    sub.add_parser("probe").add_argument("--observations", type=Path)
    exp = sub.add_parser("export")
    exp.add_argument("--run-dir", type=Path, required=True)
    exp.add_argument("--exports-root", type=Path, required=True)
    exp.add_argument("--amm-checkout", type=Path)
    exp.add_argument("--export-id")
    imp = sub.add_parser("import")
    imp.add_argument("--exports-root", type=Path, required=True)
    imp.add_argument("--runs-root", type=Path, required=True)
    imp.add_argument("--export-id", required=True)
    imp.add_argument("--confirm", action="store_true", required=True)
    args = parser.parse_args()
    if args.operation == "probe":
        result = probe(read_manifest(args.observations) if args.observations else None)
    elif args.operation == "export":
        result = export_bundle(args.run_dir, args.exports_root, args.run_dir.name,
                               args.export_id, midi_writer=wb_writer(args.amm_checkout)
                               if args.amm_checkout else None)
    else:
        result = import_return(args.exports_root, args.export_id, args.runs_root,
                               confirm=args.confirm)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
