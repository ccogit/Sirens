"""IPC v1 für SAM Audio; Dateijob nach ADR 0006."""
import json
import os
import struct
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import Cancelled, separate

MAX = 1024 * 1024


def factory():
    from backend import SamBackend
    return SamBackend(os.environ["SIRENS_RT_SAM_AUDIO_RECEIPT"])


def main(make_model=factory):
    inp, out = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr
    cap = json.loads(Path(__file__).with_name("manifest.json").read_text(encoding="utf-8"))["capability"]
    lock = threading.Lock()
    done, cancel = threading.Event(), threading.Event()
    model = None
    active = None
    progress = 0.0

    def send(kind, rid, payload):
        data = json.dumps(dict(version=1, request_id=rid, type=kind, payload=payload),
                          allow_nan=False).encode("utf-8")
        with lock:
            out.write(struct.pack("<I", len(data)) + data)
            out.flush()

    def heartbeat():
        while not done.is_set():
            send("heartbeat", "", {"progress": progress})
            done.wait(1)

    def update(value):
        nonlocal progress
        progress = value

    def run(kind, rid, payload):
        nonlocal model
        try:
            if kind == "load":
                if payload or model is not None or cancel.is_set():
                    raise ValueError("Ungültiger Ladezustand")
                model = make_model()
                result = {}
            elif kind == "file_job":
                if model is None or cancel.is_set():
                    raise Cancelled()
                if set(payload) != {"job_id", "source", "out_dir", "params"}:
                    raise ValueError("Ungültiger Dateijob")
                update(0.0)
                result = {"files": separate(model, payload["source"], payload["out_dir"],
                                            payload["params"], cancel, update)}
            elif kind == "warmup":
                if model is None or cancel.is_set():
                    raise Cancelled()
                model.separate([0.0]*44100, 44100, "silence")
                result = {}
            else:
                raise ValueError("Unbekannte Arbeit")
            if cancel.is_set():
                raise Cancelled()
            send("result", rid, result)
        except Cancelled:
            send("error", rid, {"code": "unavailable"})
        except (ValueError, TypeError, KeyError):
            send("error", rid, {"code": "invalid"})
        except Exception:
            send("error", rid, {"code": "unavailable"})

    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        while True:
            header = inp.read(4)
            if len(header) != 4:
                break
            size, = struct.unpack("<I", header)
            if not 0 < size <= MAX:
                break
            data = inp.read(size)
            if len(data) != size:
                break
            msg = json.loads(data)
            if msg.get("version") != 1 or set(msg) != {"version", "type", "request_id", "payload"}:
                break
            kind, rid, payload = msg["type"], msg["request_id"], msg["payload"]
            if not isinstance(payload, dict) or not isinstance(rid, str) or "audio_bytes" in payload:
                break
            busy = active is not None and active.is_alive()
            if kind == "cancel":
                cancel.set()
                send("result", rid, {})
            elif kind == "probe":
                send("result", rid, cap)
            elif kind == "health":
                send("result", rid, {"loaded": model is not None, "busy": busy, "progress": progress})
            elif busy:
                send("error", rid, {"code": "unavailable"})
            elif kind == "unload":
                model = None
                cancel.clear()
                send("result", rid, {})
            elif kind in {"load", "warmup", "file_job"}:
                active = threading.Thread(target=run, args=(kind, rid, payload), daemon=True)
                active.start()
            else:
                send("error", rid, {"code": "invalid"})
    finally:
        cancel.set()
        done.set()


if __name__ == "__main__":
    main()
