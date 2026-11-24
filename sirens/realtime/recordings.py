"""WP16: Stereo-PCM24, segmentierter Export und Wiederherstellung."""
import json
import math
import os
import re
import shutil
import struct
import threading
from pathlib import Path
from uuid import uuid4

from ..contracts import Ablehnung
from .contracts import invalid, validate_command
from .schemas import matches

FRAME = 6
HEADER = 44
RIFF_LIMIT = ((2**32 - 1 - 36) // FRAME) * FRAME
MAX_BLOCK_FRAMES = 2048
MAX_SESSION_BYTES = 4 * 1024**2
NAME = re.compile(r"[a-zA-Z0-9_-]{1,64}")
PART = re.compile(r"segment-[0-9]{6}\.wav\.part")


def _rate(rate):
    if type(rate) is not int or not 8000 <= rate <= 192000:
        raise invalid("sample_rate")
    return rate


def _inside(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if root not in path.parents:
        raise invalid("path")
    return path


def recording_root(root, music_root):
    root, music = Path(root).resolve(), Path(music_root).resolve()
    if root == music or root in music.parents or music in root.parents:
        raise invalid("path")
    root.mkdir(parents=True, exist_ok=True)
    return root


def wav_header(rate, size):
    _rate(rate)
    if type(size) is not int or size < 0 or size > RIFF_LIMIT or size % FRAME:
        raise invalid("size")
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + size,
                       b"WAVE", b"fmt ", 16, 1, 2, rate, rate * FRAME,
                       FRAME, 24, b"data", size)


def pcm24(payload):
    """Float32 LE interleaved; Rundung auf nächste PCM-Stufe, Sättigung."""
    if not isinstance(payload, bytes) or not 8 <= len(payload) <= MAX_BLOCK_FRAMES * 8 or len(payload) % 8:
        raise invalid("payload")
    out = bytearray()
    for (value,) in struct.iter_unpack("<f", payload):
        if not math.isfinite(value):
            raise invalid("sample")
        sample = max(-8388608, min(8388607, round(max(-1., min(1., value)) * 8388608)))
        out.extend(sample.to_bytes(3, "little", signed=True))
    return bytes(out)


def _finish(path, rate, size):
    target = path.with_suffix("")
    if target.exists() or target.is_symlink():
        raise invalid("path")
    with path.open("r+b", buffering=0) as file:
        file.truncate(HEADER + size)
        file.seek(0)
        if file.write(wav_header(rate, size)) != HEADER:
            raise OSError("WAV-Kopf unvollständig")
        os.fsync(file.fileno())
    os.replace(path, target)
    return target


def repair(root, relative, music_root):
    """Repariert nur eigene temporäre Segmente; verwirft unvollständige Frames."""
    base = recording_root(root, music_root)
    raw = base / relative
    path = _inside(base, raw)
    if raw.is_symlink() or not PART.fullmatch(path.name) or path.parent.parent != base:
        raise invalid("path")
    with path.open("rb") as file:
        head = file.read(HEADER)
        if len(head) != HEADER:
            raise invalid("header")
        rate = struct.unpack_from("<I", head, 24)[0]
        # Größenfelder können nach einem Absturz veraltet sein.
        expected = wav_header(rate, 0)
        if head[:4] != expected[:4] or head[8:40] != expected[8:40]:
            raise invalid("header")
        size = (os.fstat(file.fileno()).st_size - HEADER) // FRAME * FRAME
    return _finish(path, rate, size)


class Recording:
    """Ein Besitzer pro Aufnahme; append/stop werden serialisiert."""
    def __init__(self, root, music_root, name, rate, *,
                 segment_bytes=RIFF_LIMIT, max_bytes=16 * 1024**3,
                 reserve_bytes=1024**2):
        self.rate = _rate(rate)
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise invalid("name")
        if (type(segment_bytes) is not int or not FRAME <= segment_bytes <= RIFF_LIMIT
                or segment_bytes % FRAME or type(max_bytes) is not int
                or max_bytes < FRAME or type(reserve_bytes) is not int or reserve_bytes < 0):
            raise invalid("size")
        self.segment_bytes, self.max_bytes = segment_bytes, max_bytes
        self.reserve = reserve_bytes
        self.root = recording_root(root, music_root)
        self.directory = self.root / (name + "-" + uuid4().hex)
        self.directory.mkdir()
        self.total = self.size = 0
        self.segments = []
        self.file = self.part = None
        self.closed = False
        self.lock = threading.Lock()

    def _space(self, size):
        if shutil.disk_usage(self.directory).free < size + self.reserve:
            raise OSError("Nicht genügend Speicherplatz")

    def _open(self):
        self._space(HEADER)
        self.part = self.directory / f"segment-{len(self.segments):06d}.wav.part"
        self.file = self.part.open("xb", buffering=0)
        if self.file.write(wav_header(self.rate, 0)) != HEADER:
            raise OSError("WAV-Kopf unvollständig")
        self.size = 0

    def _seal(self):
        if self.file is None:
            return
        self.file.close()
        self.file = None
        self.segments.append(_finish(self.part, self.rate, self.size))
        self.size = 0
        self.part = None

    def append(self, payload, start_frame):
        data = pcm24(payload)
        with self.lock:
            if self.closed or type(start_frame) is not int or start_frame != self.total // FRAME:
                raise invalid("start_frame")
            if self.total + len(data) > self.max_bytes:
                self.closed = True
                self._seal()
                raise Ablehnung("invalid", "Aufnahmegrößenlimit erreicht.", "size")
            offset = 0
            try:
                while offset < len(data):
                    if self.file is None:
                        self._open()
                    n = min(len(data) - offset, self.segment_bytes - self.size)
                    self._space(n)
                    if self.file.write(data[offset:offset+n]) != n:
                        raise OSError("PCM-Block unvollständig geschrieben")
                    self.size += n
                    self.total += n
                    offset += n
                    if self.size == self.segment_bytes:
                        self._seal()
            except OSError as exc:
                self.closed = True
                try:
                    self._seal()
                except (OSError, Ablehnung):
                    # Temporäres Segment bleibt für repair erhalten.
                    pass
                raise Ablehnung("unavailable", "Aufnahme beendet: " + str(exc), "storage", 503) from exc
            return self.total // FRAME

    def stop(self):
        with self.lock:
            self.closed = True
            self._seal()
            return tuple(self.segments)


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _array(items, limit=100000):
    return {"type": "array", "items": items, "maxItems": limit}


_TEXT = {"type": "string", "minLength": 1, "maxLength": 256}
_ID = {"type": "string", "pattern": "[a-f0-9]{32}"}
_UINT = {"type": "integer", "minimum": 0, "maximum": 2**53 - 1}
_NAME = {"type": "string", "pattern": "[a-zA-Z][a-zA-Z0-9_]{0,63}"}
# Eigenes Dateiformat, kein Ersatz für eingefrorenes HTTP-Session-Schema.
SESSION_SCHEMA = _object({
    "version": {"enum": [1]},
    "sample_rate": {"type": "integer", "minimum": 8000, "maximum": 192000},
    "sources": _array(_object({"asset_id": _ID, "sha256": {"type": "string", "pattern": "[a-f0-9]{64}"}})),
    "models": _array(_object({"name": _TEXT, "version": _TEXT})),
    "presets": _array(_object({"name": _TEXT, "version": _TEXT})),
    "parameters": _array(_object({"name": _NAME, "value": {"type": "number"}})),
    "seeds": _array(_object({"name": _TEXT, "seed": _UINT})),
    "timeline": _array(_object({"frame": _UINT, "command": {"type": "object"}})),
    "assets": _array(_ID),
})


def validate_session(value):
    if not matches(SESSION_SCHEMA, value):
        raise invalid("session")
    names = [p["name"] for p in value["parameters"]]
    if len(names) != len(set(names)):
        raise invalid("parameters")
    last_frame, last_epoch, last_seq = -1, -1, -1
    for event in value["timeline"]:
        command = event["command"]
        epoch = command.get("epoch")
        if type(epoch) is not int or epoch < last_epoch or event["frame"] < last_frame:
            raise invalid("timeline")
        validate_command(command, epoch, last_seq if epoch == last_epoch else -1)
        last_frame, last_epoch, last_seq = event["frame"], epoch, command["seq"]
    return value


def save_session(root, music_root, value):
    validate_session(value)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_SESSION_BYTES:
        raise invalid("session")
    base = recording_root(root, music_root)
    directory = base / ("session-" + uuid4().hex)
    directory.mkdir()
    part = directory / "session.json.part"
    with part.open("xb") as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())
    target = directory / "session.json"
    os.replace(part, target)
    return target


def load_session(root, music_root, relative):
    base = recording_root(root, music_root)
    path = _inside(base, base / relative)
    if path.name != "session.json" or path.parent.parent != base:
        raise invalid("path")
    try:
        with path.open("rb") as file:
            raw = file.read(MAX_SESSION_BYTES + 1)
        if len(raw) > MAX_SESSION_BYTES:
            raise invalid("session")
        return validate_session(json.loads(raw))
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise invalid("session") from exc


def replay_parameters(value, frame):
    """Parameterzustand bis zum angegebenen Master-Frame, ohne Modellaufruf."""
    validate_session(value)
    if type(frame) is not int or not 0 <= frame <= 2**53 - 1:
        raise invalid("frame")
    params = {p["name"]: p["value"] for p in value["parameters"]}
    pending = []
    for event in value["timeline"]:
        if event["frame"] > frame:
            break
        command = event["command"]
        if command["command"] == "schedule":
            at = command["args"]["output_frame"]
            nested = command["args"]["command"]
            if at <= frame and nested["command"] == "set_param":
                pending.append((max(at, event["frame"]), nested["args"]))
        elif command["command"] == "set_param":
            pending.append((event["frame"], command["args"]))
    for _, args in sorted(pending, key=lambda x: x[0]):
        params[args["name"]] = args["value"]
    return params
