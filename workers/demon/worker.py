"""IPC v1, separater Modellprozess; stdout ausschließlich Protokoll."""
import json
from pathlib import Path
import struct
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workers.demon.adapter import Adapter, Unavailable, INSTALL

MAX = 1024 * 1024


def main():
    out, inp = sys.stdout.buffer, sys.stdin.buffer
    # Fremdbibliotheken dürfen die binäre Pipe nicht mit Logtext beschädigen.
    sys.stdout = sys.stderr
    adapter = Adapter()
    lock, done = threading.Lock(), threading.Event()

    def send(kind, rid, payload, audio=b""):
        data = json.dumps(dict(version=1, request_id=rid, type=kind, payload=payload),
                          allow_nan=False).encode("utf-8")
        with lock:
            out.write(struct.pack("<I", len(data)) + data + audio)
            out.flush()

    def heartbeat():
        while not done.wait(1):
            send("heartbeat", "", {})

    def run(kind, rid, payload, raw):
        try:
            if kind == "process":
                samples = struct.unpack("<" + "f" * (len(raw)//4), raw)
                result = adapter.process(samples, epoch=payload.get("epoch"))
                data = struct.pack("<" + "f" * len(result), *result)
                send("result", rid, {"audio_bytes": len(data)}, data)
                return
            if kind == "load":
                result = adapter.load(**payload)
            elif kind in ("probe", "health"):
                result = getattr(adapter, kind)()
            elif kind in ("warmup", "unload"):
                getattr(adapter, kind)()
                result = {}
            else:
                raise ValueError("Unbekannter Befehl")
            send("result", rid, result)
        except Unavailable:
            send("error", rid, {"code": "unavailable", "message": INSTALL})
        except (ValueError, TypeError, struct.error):
            send("error", rid, {"code": "invalid"})
        except Exception:
            send("error", rid, {"code": "unavailable"})

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
            msg = json.loads(inp.read(size))
            if msg["version"] != 1:
                break
            kind, rid, payload = msg["type"], msg["request_id"], msg["payload"]
            count = payload.get("audio_bytes", 0)
            if type(count) is not int or not 0 <= count <= MAX or count % 8:
                break
            raw = inp.read(count)
            if len(raw) != count:
                break
            if kind == "cancel":
                adapter.cancel()
                send("result", rid, {})
            elif kind == "health" or kind == "probe":
                run(kind, rid, payload, raw)
            elif active is not None and active.is_alive():
                send("error", rid, {"code": "unavailable"})
            else:
                active = threading.Thread(target=run, args=(kind, rid, payload, raw), daemon=True)
                active.start()
    finally:
        done.set()
        adapter.cancel()


if __name__ == "__main__":
    main()
