"""IPC v1; Windows startet ausschließlich den festen WSL2-Workerpfad."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from workers.magenta.adapter import Companion, MAX_BYTES


def serve(adapter, descriptor, inp, out):
    lock = threading.Lock()
    done = threading.Event()
    active = None
    processing = threading.Event()

    def send(kind, rid, payload, audio=b""):
        raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload),
                         allow_nan=False).encode()
        with lock:
            out.write(struct.pack("<I", len(raw)) + raw + audio)
            out.flush()

    def heartbeat():
        try:
            while not done.wait(0.5):
                send("heartbeat", "", {})
        except OSError:
            done.set()

    def process(rid, audio):
        try:
            raw = adapter.process(audio)
            # Cancel und Ausgabe sind bezüglich des Adapterzustands geordnet.
            with adapter.lock:
                processing.clear()
                if adapter.active:
                    send("result", rid, {"audio_bytes": len(raw)}, raw)
        except (ValueError, TypeError):
            processing.clear()
            send("error", rid, {"code": "invalid"})
        except Exception:
            processing.clear()
            send("error", rid, {"code": "unavailable"})

    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        while not done.is_set():
            header = inp.read(4)
            if len(header) != 4:
                break
            size, = struct.unpack("<I", header)
            if not 0 < size <= MAX_BYTES:
                break
            raw = inp.read(size)
            if len(raw) != size:
                break
            msg = json.loads(raw)
            if (not isinstance(msg, dict) or msg.get("version") != 1
                    or not isinstance(msg.get("request_id"), str)
                    or not isinstance(msg.get("payload"), dict)):
                break
            kind, rid, payload = msg.get("type"), msg["request_id"], msg["payload"]
            if kind == "process":
                count = payload.get("audio_bytes")
                if type(count) is not int or not 0 <= count <= MAX_BYTES or count % 8:
                    break
                audio = inp.read(count)
                if len(audio) != count:
                    break
                if processing.is_set():
                    send("error", rid, {"code": "unavailable"})
                else:
                    processing.set()
                    active = threading.Thread(target=process, args=(rid, audio), daemon=True)
                    active.start()
                continue
            try:
                if kind == "probe":
                    response = descriptor
                elif kind == "load":
                    adapter.load(**payload)
                    response = {}
                elif kind == "warmup":
                    adapter.warmup()
                    response = {}
                elif kind == "health":
                    response = adapter.health()
                elif kind == "cancel":
                    adapter.cancel()
                    response = {}
                elif kind == "unload":
                    adapter.unload()
                    response = {}
                else:
                    send("error", rid, {"code": "invalid"})
                    continue
                send("result", rid, response)
            except (TypeError, ValueError):
                send("error", rid, {"code": "invalid"})
            except Exception:
                send("error", rid, {"code": "unavailable"})
    finally:
        done.set()
        adapter.cancel()
        if active is None or not active.is_alive():
            adapter.unload()


def main():
    if sys.platform == "win32":
        return subprocess.call(["wsl.exe", "--cd", str(ROOT), "--exec", "python3.12",
                                "workers/magenta/worker.py"])
    from workers.magenta.backend import ENV, MagentaBackend
    if sys.platform != "linux":
        return 1
    if Path(sys.prefix).resolve() != ENV.resolve():
        python = ENV / "bin/python"
        if not python.is_file():
            return 1
        os.execv(str(python), [str(python), "-u", str(Path(__file__).resolve())])
    descriptor = json.loads(Path(__file__).with_name("manifest.json").read_text(encoding="utf-8"))["capability"]
    out = sys.stdout.buffer
    # Modellbibliotheken dürfen das IPC auf stdout nicht mit Text beschädigen.
    sys.stdout = sys.stderr
    serve(Companion(MagentaBackend), descriptor, sys.stdin.buffer, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
