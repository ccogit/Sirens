"""CPU-Worker, künstliche Fehler nur im ausdrücklich aktivierten Mock."""
import json
import os
import struct
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sirens.realtime.mock import MockAdapter
from sirens.contracts import Ablehnung

MAX = 1024 * 1024
adapter = MockAdapter()
out = sys.stdout.buffer
inp = sys.stdin.buffer
lock = threading.Lock()
cancelled = threading.Event()
done = threading.Event()


def send(kind, request_id, payload, audio=b""):
    data = json.dumps(dict(version=1, request_id=request_id, type=kind, payload=payload),
                      allow_nan=False).encode("utf-8")
    with lock:
        out.write(struct.pack("<I", len(data)) + data + audio)
        out.flush()


def heartbeats():
    while not done.is_set():
        send("heartbeat", "", {})
        done.wait(1)


def process(rid, payload, audio):
    try:
        if cancelled.wait(payload.get("delay_seconds", 0)):
            send("error", rid, {"code": "unavailable"})
            return
        if payload.get("crash"):
            os._exit(17)
        if payload.get("memory_bytes", 0) > payload.get("memory_limit_bytes", MAX):
            send("error", rid, {"code": "busy_gpu"})
            return
        samples = struct.unpack("<" + "f" * (len(audio)//4), audio)
        result = adapter.process(samples)
        raw = struct.pack("<" + "f" * len(result), *result)
        send("result", rid, {"audio_bytes": len(raw)}, raw)
    except (Ablehnung, ValueError, TypeError, struct.error):
        send("error", rid, {"code": "invalid"})


def main():
    threading.Thread(target=heartbeats, daemon=True).start()
    active = None
    try:
        while True:
            header = inp.read(4)
            if len(header) != 4:
                break
            size, = struct.unpack("<I", header)
            if not 0 < size <= MAX:
                break
            msg = json.loads(inp.read(size))
            if msg["version"] != 1:
                break
            kind, rid, payload = msg["type"], msg["request_id"], msg["payload"]
            if kind == "process":
                count = payload["audio_bytes"]
                if not 0 <= count <= MAX or count % 8:
                    break
                audio = inp.read(count)
                if len(audio) != count:
                    break
                if active is not None and active.is_alive():
                    send("error", rid, {"code": "unavailable"})
                    continue
                active = threading.Thread(target=process, args=(rid, payload, audio), daemon=True)
                active.start()
                continue
            try:
                if kind == "probe":
                    result = adapter.probe()
                elif kind == "load":
                    cancelled.clear()
                    result = adapter.load(**payload)
                elif kind == "warmup":
                    adapter.warmup()
                    result = {}
                elif kind == "health":
                    result = adapter.health()
                elif kind == "cancel":
                    cancelled.set()
                    adapter.cancel()
                    result = {}
                elif kind == "unload":
                    cancelled.set()
                    if active is not None:
                        active.join(1)
                    adapter.unload()
                    result = {}
                else:
                    send("error", rid, {"code": "invalid"})
                    continue
                send("result", rid, result)
            except (Ablehnung, TypeError, ValueError):
                send("error", rid, {"code": "invalid"})
    finally:
        done.set()


if __name__ == "__main__":
    main()
