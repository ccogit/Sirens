"""Expliziter lokaler Produktjob; Messdatei und Stems außerhalb des Repos."""
import argparse
import datetime
import json
import math
import shutil
import time
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write
from benchmarks.separation.quality import pcm

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("song", help="Relativer Songpfad im konfigurierten Musikordner")
    p.add_argument("output", type=Path, help="Neuer externer Ausgabeordner")
    p.add_argument("--port", type=int, default=8093)
    a = p.parse_args()
    out = a.output.resolve()
    if ROOT == out or ROOT in out.parents or out.exists():
        p.error("Neuer Ausgabeordner außerhalb des Repositorys erforderlich")
    if not 1 <= a.port <= 65535:
        p.error("Ungültiger Port")
    prefix = f"http://127.0.0.1:{a.port}/api/rt/v1/"
    # Kein Proxy und keine nichtlokale Zieladresse.
    opener = build_opener(ProxyHandler({}))

    def req(path, data=None):
        payload = None if data is None else json.dumps(data).encode()
        return opener.open(Request(prefix + path, data=payload,
                                   headers={"Content-Type": "application/json"}), timeout=60)

    def get_json(path, data=None):
        with req(path, data) as response:
            return json.load(response)

    start = time.monotonic()
    job = get_json("separation/jobs", {"pfad": a.song, "model": "roformer"})
    jid = job["id"]
    try:
        while job["state"] in ("queued", "running"):
            if time.monotonic() - start > 3700:
                raise TimeoutError("Zeitgrenze für Messung")
            time.sleep(.5)
            job = get_json("jobs/" + jid)
            print(f"{job['state']}: {job['progress']:.0%}", flush=True)
        elapsed = time.monotonic() - start
        if job["state"] == "ready":
            job = get_json("separation/jobs/" + jid)
        if job["state"] != "ready" or job["model"] != "roformer":
            raise RuntimeError("Kein RoFormer-Ergebnis: " + json.dumps(job))
        out.mkdir()
        for stem in ("original", "vocals", "instrumental"):
            aid = job["assets"][stem]
            with req("assets/" + aid + "/audio") as response, (out / (stem + ".wav")).open("xb") as stream:
                shutil.copyfileobj(response, stream)
        tracks = [pcm(out / (stem + ".wav")) for stem in ("original", "vocals", "instrumental")]
        if any(shape != tracks[0][0] for shape, _ in tracks):
            raise ValueError("Format/Framezahl weicht ab")
        rate, _, frames = tracks[0][0]
        x, v, i = [samples for _, samples in tracks]
        rms = math.sqrt(sum((a-b-c)**2 for a,b,c in zip(x,v,i)) / len(x))
        cold = dict.fromkeys(METRICS)
        if not job["cache_hit"]:
            for metric in ("p50_ms", "p95_ms", "p99_ms"):
                cold[metric] = elapsed * 1000
            cold["rtf"] = elapsed / (frames / rate)
            peak = job.get("vram_peak_bytes")
            if type(peak) is int and peak > 0:
                cold["peak_vram_mib"] = peak / 1024**2
        write(out / "result.json", {
            "wp": "WP08", "kandidat": "roformer-produktjob", "gate": "nicht_gemessen",
            "modus": "offline", "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "befehl": "python -m benchmarks.separation.product_job SONG EXTERNER_ORDNER",
            "rechner": collect(), "messwerte": {"kalt": cold, "warm": dict.fromkeys(METRICS)},
            "notizen": ["Ein einzelner Produktjob inkl. IPC/Cache-Prüfung und Polling, keine Verteilungsstatistik.",
                         f"Cache-Treffer: {job['cache_hit']}; Rekonstruktions-RMS: {rms}",
                         "Leakage und Lag separat mit quality.py und orthogonalen Referenzen prüfen. Hörprüfung offen."]})
    finally:
        if job["state"] in ("queued", "running"):
            get_json("jobs/" + jid + "/cancel", {})


if __name__ == "__main__":
    main()
