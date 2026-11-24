"""V1 production manifests. Pure standard library, no backend imports.

Validators return the original mapping on success and raise ContractError on
invalid input. Optional root checks verify containment and audio metadata.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from fractions import Fraction
from pathlib import Path, PurePosixPath, PureWindowsPath

SCHEMA_VERSION = 1
SAMPLE_RATE = 48000
PPQ = 960
ASSET_KINDS = {"speech", "texture", "foley", "loop", "fill", "sample"}
# Portable semantic automation parameters, normalized unless explicitly dB.
AUTOMATION_RANGES = {
    "volume": (0, 1), "gain": (0, 1), "gain_db": (-60, 12),
    "pan": (-1, 1), "cutoff": (0, 1), "resonance": (0, 1),
    "filter_cutoff": (0, 1), "filter_resonance": (0, 1),
    "expression": (0, 1), "modulation": (0, 1), "send": (0, 1),
    "send_a": (0, 1), "send_b": (0, 1), "mute": (0, 1),
}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


class ContractError(ValueError):
    """Invalid or unsafe production manifest."""


def _require(condition, field):
    if not condition:
        raise ContractError(field)


def _walk(value, field="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            _require(isinstance(key, str), field)
            _require(key.lower() not in {"shell", "command", "eval", "exec", "script", "python_code", "shell_command"}, field + "." + key)
            _walk(item, field + "." + key)
    elif isinstance(value, list):
        for item in value:
            _walk(item, field)
    elif isinstance(value, float):
        _require(math.isfinite(value), field)
    else:
        _require(value is None or type(value) in (str, int, bool), field)


def _object(value, fields=(), field="object"):
    _require(isinstance(value, dict), field)
    for name in fields:
        _require(name in value, field + "." + name + " missing")
    return value


def _manifest(value, fields):
    _object(value, ("schema_version", *fields))
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1, "schema_version")
    _walk(value)
    return value


def _list(value, field):
    _require(isinstance(value, list), field)
    return value


def _str(value, field, nullable=False):
    _require((nullable and value is None) or isinstance(value, str), field)


def _number(value, field, lo=None, hi=None, integer=False, nullable=False):
    if nullable and value is None:
        return
    _require(type(value) in ((int,) if integer else (int, float)), field)
    _require((lo is None or value >= lo) and (hi is None or value <= hi), field)


def _id(value, field="id"):
    _require(isinstance(value, str) and _ID.fullmatch(value) is not None and value not in (".", ".."), field)


def _ids(items, key):
    seen = set()
    for item in items:
        _object(item, (key,))
        value = item[key]
        _id(value, key)
        _require(value not in seen, "duplicate " + key)
        seen.add(value)
    return seen


def safe_path(root, relative):
    """Reject traversal, absolute paths and symlinks (including parents)."""
    validate_relative_path(relative)
    root = Path(root).resolve(strict=True)
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        _require(not path.is_symlink(), "symlink: " + relative)
    _require(path.resolve().is_relative_to(root), "path escapes root")
    return path


def validate_relative_path(value):
    _require(isinstance(value, str) and bool(value), "path")
    _require(not any(ord(c) < 32 for c in value) and "\\" not in value and ":" not in value, "unsafe path")
    _require(not PurePosixPath(value).is_absolute() and not PureWindowsPath(value).drive, "absolute path")
    _require(all(p not in ("", ".", "..") for p in value.split("/")), "unsafe path component")
    return value


def sha256_file(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_manifest(path):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    try:
        with open(path, encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=pairs)
        _walk(value)
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        raise ContractError(str(exc)) from exc


def _hash(value):
    _require(isinstance(value, str) and _HASH.fullmatch(value) is not None, "sha256")


def tick_to_sample(tick, bpm):
    return round(Fraction(tick * SAMPLE_RATE * 60, PPQ) / Fraction(str(bpm)))


def expected_frames(plan):
    return round((Fraction(plan["total_bars"] * 240, 1) / Fraction(str(plan["bpm"]))
                  + Fraction(str(plan["tail_seconds"]))) * SAMPLE_RATE)


def validate_brief(value):
    _manifest(value, ("title", "style", "negative_tags", "lyrics", "bpm", "key",
                      "target_seconds", "seed", "reference_ids", "vocal_mode"))
    for key in ("title", "style", "lyrics", "key", "vocal_mode"):
        _str(value[key], key, nullable=key in ("key", "lyrics", "style", "vocal_mode"))
    _number(value["bpm"], "bpm", 1, nullable=True)
    _number(value["target_seconds"], "target_seconds", 0.001, nullable=True)
    _number(value["seed"], "seed", integer=True)
    for key in ("negative_tags", "reference_ids"):
        for item in _list(value[key], key):
            _str(item, key)
    return value


def _timeline(value):
    _number(value["bpm"], "bpm", 1)
    _require(value["meter"] == [4, 4] and all(type(x) is int for x in value["meter"]), "meter")
    _require(type(value["ppq"]) is int and value["ppq"] == PPQ, "ppq")


def _sections(sections, total, label):
    sections = _list(sections, "sections")
    _ids(sections, "id")
    end = 0
    for section in sections:
        _object(section, ("start_bar", "bars", label))
        _number(section["start_bar"], "start_bar", 0, integer=True)
        _number(section["bars"], "bars", 1, integer=True)
        _str(section[label], label)
        _require(section["start_bar"] == end, "sections must be contiguous")
        end += section["bars"]
    if total is not None:
        _require(end == total, "sections must cover total_bars")


def validate_plan(value, *, automation_ranges=None):
    _manifest(value, ("seed", "bpm", "key", "meter", "ppq", "total_bars",
                      "tail_seconds", "sections", "tracks", "asset_requests", "mix"))
    _timeline(value)
    _number(value["seed"], "seed", integer=True)
    _str(value["key"], "key", nullable=True)
    _number(value["total_bars"], "total_bars", 1, integer=True)
    _number(value["tail_seconds"], "tail_seconds", 0, 4)
    _sections(value["sections"], value["total_bars"], "intent")
    limit = value["total_bars"] * PPQ * 4
    requests = _list(value["asset_requests"], "asset_requests")
    request_ids = _ids(requests, "id")
    for request in requests:
        _object(request, ("kind", "seed", "duration_seconds"))
        _require(isinstance(request["kind"], str) and request["kind"] in ASSET_KINDS, "asset kind")
        _number(request["seed"], "asset seed", integer=True)
        _number(request["duration_seconds"], "duration_seconds", 0.001)
        if request["kind"] == "speech":
            _str(request.get("text"), "speech text")
        if "prompt" in request:
            _str(request["prompt"], "prompt", nullable=True)
    tracks = _list(value["tracks"], "tracks")
    _ids(tracks, "id")
    ranges = AUTOMATION_RANGES if automation_ranges is None else automation_ranges
    for track in tracks:
        _object(track, ("role", "backend", "patch", "events", "automation"))
        _id(track["patch"], "patch")
        _str(track["role"], "role")
        _require(track["backend"] in ("instrument", "asset"), "backend")
        for event in _list(track["events"], "events"):
            _object(event, ("tick", "duration_ticks"))
            _number(event["tick"], "tick", 0, limit - 1, integer=True)
            _number(event["duration_ticks"], "duration_ticks", 1, limit - event["tick"], integer=True)
            if track["backend"] == "asset":
                _require(isinstance(event.get("asset_id"), str) and event["asset_id"] in request_ids, "asset_id")
            else:
                _number(event.get("note"), "note", 0, 127, integer=True)
                _number(event.get("velocity"), "velocity", 1, 127, integer=True)
        for event in _list(track["automation"], "automation"):
            _object(event, ("tick", "parameter", "value"))
            _number(event["tick"], "automation tick", 0, limit, integer=True)
            _require(isinstance(event["parameter"], str) and event["parameter"] in ranges, "automation parameter")
            _number(event["value"], "automation value", *ranges[event["parameter"]])
    mix = _object(value["mix"], ("target_lufs", "ceiling_dbtp"))
    _number(mix["target_lufs"], "target_lufs", nullable=True)
    _number(mix["ceiling_dbtp"], "ceiling_dbtp", hi=0)
    return value


class _PCMReader:
    """Bounded little-endian RIFF PCM reader, including extensible PCM."""
    def __init__(self, file):
        import struct

        self.file = file
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        header = file.read(12)
        _require(len(header) == 12 and header[:4] == b"RIFF" and
                 header[8:] == b"WAVE", "invalid RIFF/WAVE header")
        end = 8 + struct.unpack_from("<I", header, 4)[0]
        _require(12 <= end <= size, "truncated RIFF/WAVE")
        fmt = data = None
        while file.tell() < end:
            _require(end - file.tell() >= 8, "truncated WAV chunk header")
            chunk, length = struct.unpack("<4sI", file.read(8))
            offset = file.tell()
            stop = offset + length
            _require(stop <= end, "truncated WAV chunk")
            if chunk == b"fmt ":
                _require(fmt is None and length >= 16, "invalid WAV fmt chunk")
                raw = file.read(min(length, 40))
                tag, channels, rate, byte_rate, align, bits = struct.unpack_from("<HHIIHH", raw)
                if tag == 0xfffe:
                    _require(length >= 40, "truncated extensible WAV format")
                    extension, valid_bits = struct.unpack_from("<HH", raw, 16)
                    _require(extension >= 22 and 18 + extension <= length,
                             "invalid extensible WAV format")
                    _require(raw[24:40] == bytes.fromhex("0100000000001000800000aa00389b71"),
                             "WAV subformat must be integer PCM (not float)")
                    _require(valid_bits == bits, "WAV valid bits differ from container bits")
                else:
                    _require(tag == 1, "WAV format must be integer PCM (not float)")
                _require(channels > 0 and rate > 0 and bits > 0 and bits % 8 == 0 and
                         align == channels * (bits // 8) and byte_rate == rate * align,
                         "invalid WAV PCM geometry")
                fmt = channels, rate, bits // 8, align
            elif chunk == b"data":
                _require(data is None, "duplicate WAV data chunk")
                data = offset, length
            # Legacy wave writers may omit padding for the final odd data chunk.
            if length & 1 and stop == end:
                _require(chunk == b"data", "missing WAV chunk padding")
            else:
                stop += length & 1
                _require(stop <= end, "missing WAV chunk padding")
            file.seek(stop)
        _require(fmt is not None and data is not None, "missing WAV fmt/data chunk")
        self.channels, self.rate, self.width, self.align = fmt
        offset, self.remaining = data
        _require(self.remaining % self.align == 0, "partial WAV frame")
        self.frames = self.remaining // self.align
        file.seek(offset)

    def getnchannels(self):
        return self.channels

    def getframerate(self):
        return self.rate

    def getsampwidth(self):
        return self.width

    def getnframes(self):
        return self.frames

    def readframes(self, count):
        length = min(count * self.align, self.remaining)
        raw = self.file.read(length)
        _require(len(raw) == length, "truncated WAV data")
        self.remaining -= length
        return raw


def open_pcm_wav(path):
    """Return a context manager exposing the PCM metadata and frame reader."""
    from contextlib import contextmanager

    @contextmanager
    def opened():
        try:
            with open(path, "rb") as file:
                yield _PCMReader(file)
        except (OSError, EOFError) as exc:
            raise ContractError(str(exc)) from exc

    return opened()


def validate_wav(path, *, channels=None, frames=None):
    with open_pcm_wav(path) as wav:
        _require(wav.getframerate() == SAMPLE_RATE and wav.getsampwidth() == 3, "WAV must be 48 kHz PCM24")
        _require(wav.getnchannels() in (1, 2), "WAV channels")
        _require(wav.getnframes() > 0, "empty WAV")
        if channels is not None:
            _require(wav.getnchannels() == channels, "WAV channel mismatch")
        if frames is not None:
            _require(wav.getnframes() == frames, "WAV frame mismatch")
        while wav.readframes(65536):
            pass


def _audio(item, root, frames):
    validate_relative_path(item["file"])
    _hash(item["sha256"])
    _number(item["channels"], "channels", 1, 2, integer=True)
    if root is not None:
        path = safe_path(root, item["file"])
        validate_wav(path, channels=item["channels"], frames=frames)
        _require(sha256_file(path) == item["sha256"], "audio hash mismatch")


def validate_assets(value, plan=None, root=None):
    _manifest(value, ("assets",))
    items = _list(value["assets"], "assets")
    ids = _ids(items, "id")
    for item in items:
        if item.get("error") is not None:
            _require(isinstance(item["error"], (str, dict)), "asset error")
            continue
        _object(item, ("file", "kind", "sample_rate", "channels", "frames", "sha256", "source", "measured"))
        _require(isinstance(item["kind"], str) and item["kind"] in ASSET_KINDS, "asset kind")
        _require(item["sample_rate"] == SAMPLE_RATE, "sample_rate")
        _number(item["frames"], "frames", 1, integer=True)
        _object(item["source"], ("backend", "revision", "seed", "license", "use"))
        _object(item["measured"], ("bpm", "key"))
        _audio(item, root, item["frames"])
    if plan is not None:
        validate_plan(plan)
        _require(ids == {r["id"] for r in plan["asset_requests"]}, "asset request coverage")
    return value


def validate_stems(value, plan=None, root=None):
    _manifest(value, ("sample_rate", "frames", "stems"))
    _require(value["sample_rate"] == SAMPLE_RATE, "sample_rate")
    _number(value["frames"], "frames", 1, integer=True)
    items = _list(value["stems"], "stems")
    ids = _ids(items, "track_id")
    for item in items:
        _object(item, ("role", "file", "channels", "sha256", "source"))
        _object(item["source"], ("backend", "patch", "revision"))
        _audio(item, root, value["frames"])
    if plan is not None:
        validate_plan(plan)
        _require(value["frames"] == expected_frames(plan), "stem length")
        _require(ids == {t["id"] for t in plan["tracks"]}, "track coverage")
    return value


def validate_mix_report(value):
    # V1 prose does not specify exact measurement key names.
    _manifest(value, ("warnings",))
    _list(value["warnings"], "warnings")
    return value


def validate_report(value):
    _manifest(value, ("technical", "music", "production", "gates", "missing", "provenance", "listening"))
    for key in ("technical", "music", "production", "gates", "provenance"):
        _object(value[key])
    _list(value["missing"], "missing")
    listening = _object(value["listening"], ("blind_pairs", "results"))
    for key in ("blind_pairs", "results"):
        _list(listening[key], key)
    return value


def validate_status(value):
    _manifest(value, ("status", "stage", "progress", "error", "timestamps"))
    _require(value["status"] in ("queued", "running", "succeeded", "failed", "cancelled"), "status")
    _str(value["stage"], "stage", nullable=True)
    _number(value["progress"], "progress", 0, 1, nullable=True)
    _require(value["error"] is None or isinstance(value["error"], (str, dict)), "error")
    timestamps = _object(value["timestamps"], ("queued",))
    for stamp in timestamps.values():
        _str(stamp, "timestamp", nullable=True)
    return value


def validate_ableton(value, root=None):
    _manifest(value, ("run_id", "export_id", "bpm", "meter", "ppq", "sample_rate", "frames",
                      "sections", "tracks", "reference_mix", "project_file", "mode", "capabilities", "warnings"))
    _timeline(value)
    _require(value["sample_rate"] == SAMPLE_RATE, "sample_rate")
    _number(value["frames"], "frames", 1, integer=True)
    _id(value["run_id"], "run_id")
    _id(value["export_id"], "export_id")
    _sections(value["sections"], None, "label")
    _require(value["mode"] in ("set", "import_bundle", "live_editable"), "mode")
    _require((value["mode"] == "set") == (value["project_file"] is not None), "project_file/mode mismatch")
    caps = _object(value["capabilities"], ("live_version", "edition", "max_for_live", "open_set", "render", "reason"))
    for key in ("live_version", "edition", "reason"):
        _str(caps[key], key, nullable=True)
    for key in ("max_for_live", "open_set", "render"):
        _require(caps[key] is None or type(caps[key]) is bool, key)
    if value["mode"] == "live_editable":
        _require(caps["open_set"] is True and bool(value.get("set_binding")), "live set binding required")
    _list(value["warnings"], "warnings")
    def path_check(relative):
        validate_relative_path(relative)
        if root is not None:
            _require(safe_path(root, relative).is_file(), "missing export file")
    path_check(value["reference_mix"])
    if root is not None:
        validate_wav(safe_path(root, value["reference_mix"]), frames=value["frames"])
    if value["project_file"] is not None:
        path_check(value["project_file"])
        _require(value["project_file"].lower().endswith(".als"), "project_file extension")
    tracks = _list(value["tracks"], "tracks")
    _ids(tracks, "track_id")
    for track in tracks:
        _object(track, ("role", "audio_file", "midi_file", "patch", "automation_file", "sha256"))
        _id(track["patch"], "patch")
        _str(track["role"], "role")
        _hash(track["sha256"])
        path_check(track["audio_file"])
        if root is not None:
            audio = safe_path(root, track["audio_file"])
            validate_wav(audio, frames=value["frames"])
            _require(sha256_file(audio) == track["sha256"], "audio hash mismatch")
        for key in ("midi_file", "automation_file"):
            if track[key] is not None:
                path_check(track[key])
    return value


def validate_return(value, root=None):
    _manifest(value, ("export_id", "parent_run_id", "master_file", "notes"))
    for key in ("export_id", "parent_run_id"):
        _id(value[key], key)
    validate_relative_path(value["master_file"])
    if root is not None:
        validate_wav(safe_path(root, value["master_file"]))
    for key in ("stems", "midi"):
        for item in _list(value.get(key, []), key):
            path = item if isinstance(item, str) else _object(item, ("file",))["file"]
            validate_relative_path(path)
            if root is not None:
                _require(safe_path(root, path).is_file(), "missing return file")
    if value.get("project_file") is not None:
        validate_relative_path(value["project_file"])
    return value


VALIDATORS = {
    "brief": validate_brief, "plan": validate_plan, "assets": validate_assets,
    "stems": validate_stems, "mix_report": validate_mix_report, "report": validate_report,
    "status": validate_status, "ableton": validate_ableton, "return": validate_return,
}


def validate_manifest(kind, value, **kwargs):
    _require(kind in VALIDATORS, "unknown manifest kind")
    return VALIDATORS[kind](value, **kwargs)
