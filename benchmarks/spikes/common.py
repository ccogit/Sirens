"""Standardbibliothek-Messhilfe für isolierte Spikes."""
import datetime
import math
import time
import subprocess
import os
from benchmarks import result, baseline

def percentile(values, p):
    if not 0 <= p <= 100:
        raise ValueError("Perzentil außerhalb 0–100")
    if not values:
        return None
    vals = sorted(values)
    if any(not math.isfinite(v) or v < 0 for v in vals):
        raise ValueError("Ungültige Messwerte")
    i = (len(vals) - 1) * p / 100
    lo, hi = math.floor(i), math.ceil(i)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)

def rtf(seconds, audio_seconds):
    if not math.isfinite(seconds) or seconds < 0 or not math.isfinite(audio_seconds) or audio_seconds <= 0:
        raise ValueError("Ungültige Zeit/Dauer")
    return seconds / audio_seconds

def summarize(samples, peak=None):
    # samples: Paare (Wallclock-Sekunden, tatsächliche Audiodauer)
    ms = [s * 1000 for s, _ in samples]
    ratios = [rtf(s, d) for s, d in samples]
    return dict(p50_ms=percentile(ms, 50), p95_ms=percentile(ms, 95),
                p99_ms=percentile(ms, 99), peak_vram_mib=peak,
                rtf=percentile(ratios, 50), underruns=None,
                rtf_p50=percentile(ratios, 50), rtf_p95=percentile(ratios, 95),
                rtf_p99=percentile(ratios, 99), anzahl=len(samples))

def timed(call, synchronize=lambda: None):
    synchronize()
    start = time.perf_counter()
    value = call()
    synchronize()
    return value, time.perf_counter() - start

def gpu_memory():
    """Momentaufnahme aller GPUs bzw. dieses Prozesses, nicht Peak; WDDM ggf. null."""
    def query(kind, fields):
        try:
            out = subprocess.check_output(["nvidia-smi", "--query-" + kind + "=" + fields,
                                           "--format=csv,noheader,nounits"],
                                          text=True, timeout=5, stderr=subprocess.DEVNULL)
            return [line.split(",") for line in out.splitlines() if line.strip()]
        except (OSError, subprocess.SubprocessError):
            return []
    def number(v):
        try:
            n = int(v.strip())
            return n if n >= 0 else None
        except ValueError:
            return None
    gpus = [number(row[0]) for row in query("gpu", "memory.used")]
    procs = [number(row[1]) for row in query("compute-apps", "pid,used_gpu_memory")
             if len(row) == 2 and row[0].strip() == str(os.getpid())]
    return {"gpu_mib": gpus, "prozess_mib": sum(procs) if procs and None not in procs else None}

def make_result(kandidat, modus, rechner, kalt, warm, befehl, notizen):
    return result.validate(dict(wp="WP02", kandidat=kandidat, gate="nicht_gemessen",
                                modus=modus, zeitpunkt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                rechner=rechner, messwerte=dict(kalt=kalt, warm=warm),
                                befehl=befehl, notizen=notizen))
