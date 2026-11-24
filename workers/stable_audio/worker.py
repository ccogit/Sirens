"""IPC v1: ein Clip, begrenzte PCM-Blöcke, Heartbeat während Modellarbeit."""
import json
import struct
import sys
import threading

from adapter import Adapter
from file_job import render_file

MAX = 1024 * 1024
adapter = Adapter()
out = sys.stdout.buffer
inp = sys.stdin.buffer
# Modellbibliotheken dürfen den Protokollkanal nicht mit Text beschreiben.
sys.stdout = sys.stderr
lock = threading.Lock()
done = threading.Event()
cancelled = threading.Event()


def send(kind, rid, payload, audio=b""):
    raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload),
                     allow_nan=False).encode()
    with lock:
        out.write(struct.pack("<I", len(raw)) + raw + audio)
        out.flush()


def heartbeat():
    while not done.is_set():
        send("heartbeat", "", {})
        done.wait(1)


def work(kind, rid, payload):
    try:
        raw = b""
        if kind == "load" and not payload:
            adapter.load()
            result = {}
        elif kind == "warmup" and not payload:
            adapter.warmup()
            result = {}
        elif kind == "unload" and not payload:
            adapter.unload()
            result = {}
        elif kind == "file_job":
            result = render_file(adapter, payload)
        elif kind == "process" and payload.get("audio_bytes") == 0:
            params = {k: v for k, v in payload.items() if k != "audio_bytes"}
            if set(params) == {"job"}:
                result = adapter.generate(params["job"])
            elif set(params) == {"offset", "frames"}:
                raw = adapter.chunk(params["offset"], params["frames"])
                result = {"audio_bytes": len(raw)}
            else:
                raise ValueError("Parameter")
        else:
            raise ValueError("Befehl")
        if not cancelled.is_set():
            send("result", rid, result, raw)
    except (ValueError, TypeError, KeyError):
        if not cancelled.is_set():
            send("error", rid, {"code": "invalid"})
    except Exception as exc:
        print(type(exc).__name__, file=sys.stderr)
        if not cancelled.is_set():
            send("error", rid, {"code": "unavailable"})


def main():
    threading.Thread(target=heartbeat, daemon=True).start()
    active = None
    try:
        while True:
            header = inp.read(4)
            if len(header) != 4:
                break
            size, = struct.unpack("<I", header)
            if not 0 < size <= MAX:
                break
            raw = inp.read(size)
            if len(raw) != size:
                break
            msg = json.loads(raw)
            if msg.get("version") != 1:
                break
            kind, rid, payload = msg["type"], msg["request_id"], msg["payload"]
            if not isinstance(payload, dict) or payload.get("audio_bytes", 0) != 0:
                break
            if kind == "cancel":
                cancelled.set()
                send("result", rid, {})
            elif kind == "health":
                send("result", rid, {"loaded": adapter.model is not None, "warmed": adapter.warmed})
            elif kind == "probe":
                send("result", rid, {"mode": "lookahead", "mock": False, "available": False})
            elif cancelled.is_set() or (active is not None and active.is_alive()):
                send("error", rid, {"code": "unavailable"})
            else:
                active = threading.Thread(target=work, args=(kind, rid, payload), daemon=True)
                active.start()
    finally:
        done.set()


if __name__ == "__main__":
    main()
