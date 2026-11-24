"""WP11: explizite lokale Messung der Worker-Adapter; keine automatische Installation."""
import argparse
import datetime
import math
from pathlib import Path
import shlex
import sys
import time
import uuid

from benchmarks import baseline, fixtures, result
from benchmarks.spikes import common
from workers.rave.adapter import RaveAdapter, FRAMES, factory as rave_factory
from workers.after.adapter import AfterAdapter, factory as after_factory

ROOT = Path(__file__).resolve().parents[2]


def cases(name):
    if name == "rave":
        return [
            ("latent-tief", {"seed": 7, "latent_0": -0.75, "wet": 1}, "sinus440"),
            ("latent-hoch", {"seed": 7, "latent_0": 0.75, "wet": 1}, "sinus440"),
            ("morph", {"seed": 7, "latent_1": 1.0, "morph": 0.5, "wet": 0.75}, "sinus440"),
        ]
    return [
        ("timbre-440", {"seed": 7, "guidance": 1, "steps": 10, "wet": 1}, "sinus440"),
        ("timbre-1000", {"seed": 7, "guidance": 1, "steps": 10, "wet": 1}, "sinus1000"),
        ("struktur", {"seed": 7, "guidance": 0.5, "steps": 10, "wet": 0.75}, "sinus440"),
    ]


def signal(name, rate, frames):
    return fixtures.generate(name, rate, frames/rate, 2).samples


def save(path, samples, rate):
    fixtures.write_wav(path, fixtures.Fixture(samples, dict(
        rate=rate, channels=2, frames=len(samples)//2)))


def paced_rave(adapter, samples, seconds):
    """Block-Deadline-Simulation, keine Browser- oder Audio-Geräte-Messung."""
    block_s = FRAMES/48000
    count = math.ceil(seconds/block_s)
    start = time.perf_counter()
    late = 0
    timings = []
    for index in range(count):
        target = start + index*block_s
        delay = target-time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        _, elapsed = common.timed(lambda: adapter.process(samples))
        timings.append((elapsed, block_s))
        if time.perf_counter() > target+block_s:
            late += 1
    return timings, late, count, time.perf_counter()-start


def measure(name, adapter, directory, seconds, device, command):
    rate = 48000 if name == "rave" else 44100
    warm, cold = [], []
    rows = []
    import torch
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    try:
        for label, params, reference in cases(name):
            _, load_s = common.timed(lambda: adapter.load(**params))
            frames = FRAMES if name == "rave" else adapter.health()["frames"]
            source = signal("sinus440" if name == "rave" else "click120", rate, frames)
            ref = signal(reference, rate, frames)
            def infer():
                return adapter.process(source) if name == "rave" else adapter.transform(source, ref)
            first, first_s = common.timed(infer)
            cold.append((load_s+first_s, frames/rate))
            output, elapsed = common.timed(infer)
            warm.append((elapsed, frames/rate))
            save(directory / (label+".wav"), output, rate)
            rows.append(dict(preset=label, params=params, reference=reference,
                             load_ms=load_s*1000, first_ms=first_s*1000,
                             warm_ms=elapsed*1000, frames=frames))
            adapter.unload()
        soak = None
        if seconds:
            adapter.load(**cases(name)[0][1])
            adapter.warmup()
            timings, late, count, wall = paced_rave(adapter, signal("sinus440", rate, FRAMES), seconds)
            soak = dict(blocks=count, deadline_misses=late, audio_seconds=count*FRAMES/rate,
                        wall_seconds=wall, **common.summarize(timings))
        peak = torch.cuda.max_memory_reserved()/2**20 if device == "cuda" else None
        data = common.make_result(name, "offline" if name == "rave" else "lookahead",
            baseline.collect(), common.summarize(cold), common.summarize(warm), command,
            ["Nur Inferenz/Adapter; Control-to-audio, Geräte-Underruns und Hörurteil nicht gemessen.",
             "Kein G1/G3-Entscheid durch dieses Skript. RAVE-Soak zählt simulierte Block-Deadlines.",
             "AFTER lädt für reproduzierbare Jobs den Export erneut; Warmzeit enthält ggf. erneutes Laden.",
             "Torch Peak Reserved separat; kein Gesamt-GPU-Peak."])
        data.update(wp="WP11", cases=rows, soak=soak, torch_peak_reserved_mib=peak,
                    device=device, torch_version=torch.__version__)
        result.write(directory / "result.json", data)
        (directory / "result.md").write_text(result.markdown(data), encoding="utf-8")
        return data
    finally:
        adapter.unload()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model", choices=("rave", "after"))
    p.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    p.add_argument("--seconds", type=int, default=0, help="RAVE Block-Deadline-Test (1800 für 30 Min.)")
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--measure", action="store_true", help="Vertrauensbestätigten lokalen Export explizit laden")
    args = p.parse_args(argv)
    if not 0 <= args.seconds <= 3600 or (args.model == "after" and args.seconds):
        p.error("Soak nur für RAVE, maximal 3600 Sekunden")
    if args.dry_run:
        print("Dry-Run:", args.model, [case[0] for case in cases(args.model)], "Gate nicht_gemessen")
        return 0
    if args.model == "rave":
        adapter = RaveAdapter(lambda: rave_factory(args.device), allow_unmeasured=True)
    else:
        adapter = AfterAdapter(lambda: after_factory(args.device), allow_unmeasured=True)
    directory = ROOT / "benchmarks" / "results" / "local" / ("wp11-"+args.model+"-"+uuid.uuid4().hex[:10])
    directory.mkdir(parents=True, exist_ok=False)
    command = "python -m benchmarks.neural_mutation.messen " + shlex.join(
        list(sys.argv[1:] if argv is None else argv))
    measure(args.model, adapter, directory, args.seconds, args.device, command)
    print("Ergebnis:", directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
