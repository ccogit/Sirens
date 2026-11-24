"""Gemeinsamer WP11-Lebenszyklus und begrenztes IPC (nur Standardbibliothek)."""
import copy
import json
import math
import struct
import sys
import threading
from pathlib import Path

MAX = 1024 * 1024


class Unavailable(Exception):
    pass


def descriptor(directory):
    return json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))["capability"]


def preset(cap, values):
    controls = {c["name"]: c for c in cap["controls"]}
    if set(values) - controls.keys():
        raise ValueError("Unbekannter Regler")
    params = {key: c["default"] for key, c in controls.items()}
    for key, value in values.items():
        c = controls[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not c["min"] <= value <= c["max"]:
            raise ValueError("Ungültiger Regler")
        if key in ("seed", "steps") and int(value) != value:
            raise ValueError("Ganzzahl erforderlich")
        params[key] = int(value) if key in ("seed", "steps") else value
    return params


def audio_check(samples):
    if len(samples) % 2 or any(not math.isfinite(s) or not -1 <= s <= 1 for s in samples):
        raise ValueError("Ungültige PCM-Samples")


def mix(dry, mono, wet):
    if len(dry) != 2 * len(mono) or any(not math.isfinite(s) for s in mono):
        raise ValueError("Ungültige Modell-Ausgabe")
    return [max(-1.0, min(1.0, (1-wet)*s + wet*mono[i//2])) for i, s in enumerate(dry)]


class Adapter:
    def __init__(self, directory, factory, *, allow_unmeasured=False):
        self.cap = descriptor(directory)
        self.factory = factory
        self.allow_unmeasured = allow_unmeasured
        self.model = None
        self.cancelled = threading.Event()
        self.params = {}
        self.lock = threading.RLock()

    def probe(self):
        return copy.deepcopy(self.cap)

    def load(self, **values):
        params = preset(self.cap, values)
        with self.lock:
            self.unload()
            if not (self.cap["available"] or self.allow_unmeasured):
                raise Unavailable("Gate nicht freigegeben")
            try:
                self.model = self.factory()
            except (OSError, ImportError, ValueError, RuntimeError) as exc:
                raise Unavailable("Modell nicht installiert oder nicht verifiziert") from exc
            self.params = params
            self.cancelled.clear()
            return self.probe()

    def check(self):
        if self.model is None or self.cancelled.is_set():
            raise Unavailable("Modell nicht geladen oder abgebrochen")

    def warmup(self):
        # Aufwärmen mit separatem Exportzustand; echte erste Inferenz wird gemessen.
        self.check()

    def cancel(self):
        self.cancelled.set()

    def unload(self):
        self.cancel()
        with self.lock:
            self.model = None
            self.params = {}

    def health(self):
        return {"mock": False, "loaded": self.model is not None,
                "cancelled": self.cancelled.is_set()}


def serve(adapter):
    """IPC v1. Während Inferenz bleiben Heartbeat und Cancel erreichbar."""
    inp, out = sys.stdin.buffer, sys.stdout.buffer
    write_lock, done = threading.Lock(), threading.Event()
    active = None

    def send(kind, rid, payload, audio=b""):
        raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload),
                         allow_nan=False).encode("utf-8")
        with write_lock:
            out.write(struct.pack("<I", len(raw)) + raw + audio)
            out.flush()

    def heartbeat():
        while not done.is_set():
            send("heartbeat", "", {})
            done.wait(1)

    def process(rid, audio):
        try:
            samples = struct.unpack("<" + "f"*(len(audio)//4), audio)
            result = adapter.process(samples)
            raw = struct.pack("<" + "f"*len(result), *result)
            if len(raw) > MAX:
                raise ValueError("Ausgabeblock zu groß")
            with adapter.lock:
                adapter.check()
                send("result", rid, {"audio_bytes": len(raw)}, raw)
        except Unavailable:
            send("error", rid, {"code": "unavailable"})
        except (ValueError, TypeError, struct.error):
            send("error", rid, {"code": "invalid"})
        except Exception:
            send("error", rid, {"code": "unavailable"})

    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        while True:
            raw = inp.read(4)
            if len(raw) != 4:
                break
            size, = struct.unpack("<I", raw)
            if not 0 < size <= MAX:
                break
            raw = inp.read(size)
            if len(raw) != size:
                break
            msg = json.loads(raw)
            if msg.get("version") != 1:
                break
            kind, rid, payload = msg["type"], msg["request_id"], msg["payload"]
            if not isinstance(payload, dict) or not isinstance(rid, str):
                break
            if kind == "process":
                size = payload.get("audio_bytes")
                if type(size) is not int or size % 8 or not 0 <= size <= MAX:
                    break
                audio = inp.read(size)
                if len(audio) != size:
                    break
                if set(payload) != {"audio_bytes"} or (active and active.is_alive()):
                    send("error", rid, {"code": "unavailable"})
                    continue
                active = threading.Thread(target=process, args=(rid, audio), daemon=True)
                active.start()
                continue
            try:
                if kind != "load" and payload:
                    raise ValueError("Unerwartete Parameter")
                if kind == "cancel":
                    adapter.cancel()
                    result = {}
                elif kind == "probe":
                    result = adapter.probe()
                elif kind == "health":
                    result = adapter.health()
                elif active and active.is_alive():
                    raise Unavailable("Inferenz läuft")
                elif kind == "load":
                    result = adapter.load(**payload)
                elif kind == "unload":
                    adapter.unload()
                    result = {}
                elif kind == "warmup":
                    adapter.warmup()
                    result = {}
                else:
                    raise ValueError("Unbekannter Befehl")
                send("result", rid, result)
            except Unavailable:
                send("error", rid, {"code": "unavailable"})
            except (ValueError, TypeError):
                send("error", rid, {"code": "invalid"})
    finally:
        adapter.cancel()
        done.set()
