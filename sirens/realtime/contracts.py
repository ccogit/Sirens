"""Verträge der Steuer-API v1."""
import math
import re
from pathlib import Path
from uuid import uuid4
from ..contracts import Ablehnung, safe_audio_path

VERSION = 1
PREFIX = "/api/rt/v1/"
MAX_SAFE_INTEGER = 2**53 - 1
ERRORS = {"unavailable": 503, "busy_gpu": 409, "deadline_missed": 409,
          "stale_epoch": 409, "not_found": 404, "invalid": 400}
SESSION_TRANSITIONS = {
    "created": ("loading", "stopping", "error"),
    "loading": ("ready", "stopping", "error"),
    "ready": ("playing", "stopping", "error"),
    "playing": ("paused", "stopping", "error"),
    "paused": ("playing", "stopping", "error"),
    "stopping": ("closed", "error"),
    "error": ("stopping",), "closed": (),
}
JOB_TRANSITIONS = {"queued": ("running", "cancelled", "error"),
                   "running": ("ready", "error", "cancelled"),
                   "ready": (), "error": (), "cancelled": ()}
COMMANDS = {"load": {"asset_id"}, "play": set(), "pause": set(),
            "seek": {"source_frame"}, "set_param": {"name", "value"},
            "schedule": {"output_frame", "command"}, "bypass": {"enabled"}}
ID_PATTERN = r"^[a-f0-9]{32}$"

def error(code, field=None):
    messages = {"unavailable": "Echtzeit-Funktion nicht verfügbar.",
                "busy_gpu": "GPU ist belegt.", "deadline_missed": "Zeitgrenze überschritten.",
                "stale_epoch": "Veraltete Transportgeneration.", "not_found": "Nicht gefunden.",
                "invalid": "Ungültiger Vertragswert."}
    return Ablehnung(code, messages[code], field, ERRORS[code])

def invalid(field=None):
    return error("invalid", field)

def transition(table, current, target):
    if target not in table.get(current, ()):
        raise invalid("state")
    return target

def new_id():
    return uuid4().hex

def asset_id(value):
    if not isinstance(value, str) or not re.fullmatch(ID_PATTERN, value):
        raise invalid("asset_id")
    return value

def source_path(root, relative):
    return safe_audio_path(root, relative)

def cache_path(root, kind, identifier):
    if kind not in ("cache", "sessions"):
        raise invalid("kind")
    base = Path(root).resolve()
    result = (base / kind / asset_id(identifier)).resolve()
    if result.parent != base / kind:
        raise invalid("path")
    return result

def uint(value, field, maximum=MAX_SAFE_INTEGER):
    if type(value) is not int or not 0 <= value <= maximum:
        raise invalid(field)
    return value

def finite(value):
    return type(value) in (int, float) and -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER and math.isfinite(value)

def validate_command(command, epoch, last_seq=-1):
    if not isinstance(command, dict):
        raise invalid("command")
    name = command.get("command")
    if not isinstance(name, str) or name not in COMMANDS:
        raise invalid("command")
    uint(command.get("epoch"), "epoch", 2**32-1)
    uint(command.get("seq"), "seq", 2**32-1)
    if command["epoch"] != epoch:
        raise error("stale_epoch", "epoch")
    if command["seq"] <= last_seq:
        raise invalid("seq")
    args = command.get("args")
    if set(command) != {"command", "epoch", "seq", "args"} or not isinstance(args, dict) or set(args) != COMMANDS[name]:
        raise invalid("args")
    if name == "load":
        asset_id(args["asset_id"])
    elif name == "seek":
        uint(args["source_frame"], "source_frame")
    elif name == "set_param":
        if not isinstance(args["name"], str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,63}", args["name"]) or not finite(args["value"]):
            raise invalid("args")
    elif name == "bypass" and type(args["enabled"]) is not bool:
        raise invalid("enabled")
    elif name == "schedule":
        uint(args["output_frame"], "output_frame")
        nested = args["command"]
        if not isinstance(nested, dict) or nested.get("command") not in ("play", "pause", "set_param", "bypass"):
            raise invalid("command")
        if set(nested) != {"command", "args"}:
            raise invalid("command")
        validate_command({**nested, "epoch": epoch, "seq": command["seq"]}, epoch, last_seq)
    return command
