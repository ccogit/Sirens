"""Dateijob-Worker; Modellarbeit ausschließlich in der eigenen Umgebung."""
import json
import os
import shutil
import struct
import sys
import threading
from pathlib import Path

from roformer import run

MAX = 1024 * 1024
# Modellbibliotheken dürfen das IPC nicht mit Konsolenausgaben verunreinigen.
wire = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
lock = threading.Lock()
stop = threading.Event()
progress = 0


def send(kind, rid, payload):
    raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload),
                     allow_nan=False).encode()
    with lock:
        wire.write(struct.pack("<I", len(raw)) + raw)


def heartbeat():
    while not stop.is_set():
        send("heartbeat", "", {"progress": progress})
        stop.wait(.25)


def demucs_run(source, out):
    # Bestandsumgebung, CPU, nur lokal vorhandene Gewichte.
    from importlib.metadata import version
    if version("demucs") != "4.0.0":
        raise RuntimeError("Demucs 4.0.0 erforderlich")
    import torch
    def no_download(*args, **kwargs):
        raise RuntimeError('Demucs-Gewichte fehlen lokal; separat installieren')
    torch.hub.download_url_to_file = no_download
    from demucs.separate import main as separate
    staging = out / 'demucs'
    separate(['-n', 'htdemucs', '--device', 'cpu', '-o', str(staging), str(source)])
    names = ['vocals.wav', 'drums.wav', 'bass.wav', 'other.wav']
    for name in names:
        (staging / 'htdemucs' / source.stem / name).rename(out / name)
    shutil.rmtree(staging)
    return {'files': names, 'vram_peak_bytes': 0}


def main():
    global progress
    weight = Path(sys.prefix) / "weights" / "MelBandRoformer.ckpt"
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        while True:
            head = sys.stdin.buffer.read(4)
            if len(head) != 4:
                return
            size, = struct.unpack("<I", head)
            if not 0 < size <= MAX:
                return
            msg = json.loads(sys.stdin.buffer.read(size))
            rid, kind = msg["request_id"], msg["type"]
            try:
                if kind == "file_job":
                    payload = msg["payload"]
                    if set(payload) != {"job_id", "source", "out_dir", "params"} or payload["params"] != {}:
                        raise ValueError("Ungültiger Dateijob")
                    source, out = Path(payload["source"]), Path(payload["out_dir"])
                    if not source.is_absolute() or not out.is_absolute() or not out.is_dir() or any(out.iterdir()):
                        raise ValueError("Privater Ausgabeordner erforderlich")
                    progress = .05
                    if sys.argv[1:] == ["--demucs"]:
                        result = demucs_run(source, out)
                    else:
                        descriptor = run(source, out, weight)
                        result = {"files": ["vocals.wav", "instrumental.wav"],
                                  "vram_peak_bytes": descriptor["vram_peak_bytes"]}
                    progress = 1
                    send("result", rid, result)
                elif kind == "health":
                    send("result", rid, {"loaded": False})
                elif kind == "cancel":
                    send("result", rid, {})
                    return
                else:
                    send("error", rid, {"code": "unavailable"})
            except Exception:
                send("error", rid, {"code": "unavailable"})
    finally:
        stop.set()
        thread.join(timeout=1)


if __name__ == "__main__":
    main()
