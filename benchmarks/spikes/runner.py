"""Lokaler Spike-Runner. Keine Modelle beim Import oder im Dry-Run."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from benchmarks import baseline, fixtures, result
from benchmarks.spikes import common

ROOT = Path(__file__).resolve().parents[2]

def parser(name):
    p = argparse.ArgumentParser(description="WP02: " + name)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--model", type=Path, help="Lokal geprüfte Gewichte bzw. Snapshot")
    p.add_argument("--sha256", help="SHA-256 der Modelldatei (bei TorchScript Pflicht)")
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--duration", type=float, default=4.0)
    p.add_argument("--rate", type=int, default=44100)
    p.add_argument("--block", type=int, default=4096)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--signal", choices=fixtures.SIGNALS, default="click120")
    p.add_argument("--seconds", type=float, default=0, help="Zusätzliche Mindest-Wallclock-Dauer")
    return p

class Sampler:
    def __init__(self):
        self.stop = threading.Event()
        self.gpu_peak = None
        self.proc_peak = None
        self.thread = threading.Thread(target=self.sample, daemon=True)

    def sample(self):
        while not self.stop.is_set():
            snapshot = common.gpu_memory()
            gpu = snapshot["gpu_mib"]
            if gpu and all(v is not None for v in gpu):
                total = sum(gpu)
                self.gpu_peak = max(self.gpu_peak or 0, total)
            proc = snapshot["prozess_mib"]
            if proc is not None:
                self.proc_peak = max(self.proc_peak or 0, proc)
            self.stop.wait(0.2)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.thread.join()

def run(name, mode, loader, argv=None):
    p = parser(name)
    args = p.parse_args(argv)
    if not (0 < args.duration <= 120 and args.rate >= 8000 and args.block > 0
            and args.repeats >= 2 and 0 <= args.seconds <= 3600):
        p.error("Ungültige Dauer, Rate, Blockgröße oder Wiederholungen")
    if args.dry_run:
        fixtures.generate(args.signal, args.rate, min(args.duration, 0.1), 2)
        print("Dry-Run OK: " + name + "; keine Inferenz, Gate nicht_gemessen")
        return 0
    if sys.prefix == sys.base_prefix or not Path(sys.prefix).name.startswith(".venv-spike-"):
        p.error("Eigene .venv-spike-" + name + " fehlt; siehe install.ps1")
    if args.model is None or not args.model.exists():
        p.error("Lokale geprüfte Gewichte fehlen (--model); kein automatischer Download")
    if args.model.is_file():
        if not args.sha256:
            p.error("SHA-256 des geprüften Modells fehlt")
        with args.model.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest.lower() != args.sha256.lower():
            p.error("SHA-256 des Modells stimmt nicht")
    if importlib.util.find_spec("torch") is None:
        p.error("PyTorch fehlt in der Spike-Umgebung")
    # Offline-Modus vor den Fremdimports; für nicht-HF-Downloads zusätzlich Netz sperren.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    if args.device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA nicht verfügbar")
    sync = torch.cuda.synchronize if args.device == "cuda" else lambda: None
    source = fixtures.generate(args.signal, args.rate, args.duration, 2)
    # Nur synthetisches Signal; keine Benutzerdaten.
    out = ROOT / "benchmarks" / "results" / "local" / (name + "-" + uuid.uuid4().hex[:10])
    out.mkdir(parents=True, exist_ok=False)
    try:
        if args.device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        with Sampler() as cold_gpu:
            backend, load_s = common.timed(lambda: loader(args, source, torch), sync)
            first, first_s = common.timed(lambda: backend(0), sync)
        cold = common.summarize([(load_s + first_s, first[1])], cold_gpu.proc_peak)
        cold.update(load_ms=load_s*1000, first_inference_ms=first_s*1000,
                    gpu_total_sampled_peak_mib=cold_gpu.gpu_peak,
                    torch_peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20 if args.device == "cuda" else None)
        write_audio(out / "cold.wav", first)
        if args.device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        samples = []
        start = time.perf_counter()
        with Sampler() as warm_gpu:
            while len(samples) < args.repeats or time.perf_counter() - start < args.seconds:
                audio, elapsed = common.timed(lambda: backend(len(samples)+1), sync)
                samples.append((elapsed, audio[1]))
                if len(samples) <= 3:
                    write_audio(out / ("warm-%d.wav" % len(samples)), audio)
        warm = common.summarize(samples, warm_gpu.proc_peak)
        warm.update(gpu_total_sampled_peak_mib=warm_gpu.gpu_peak,
                    torch_peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20 if args.device == "cuda" else None)
        data = common.make_result(name, mode, baseline.collect(), cold, warm,
                 "python -m benchmarks.spikes." + name + ".messen (lokale Modellpfade separat)",
                 ["Device: " + args.device, "VRAM per nvidia-smi abgetastet, kurze Peaks ggf. verfehlt.",
                  "Keine hörbare End-to-End-Latenz, kein Gate; Audio außerhalb des Timings gespeichert.",
                  "Seeds: kalt 0, warm fortlaufend ab 1."])
        data["profil"] = dict(device=args.device, signal=args.signal, rate=args.rate,
                              block=args.block, duration=args.duration, seconds=args.seconds,
                              repeats=args.repeats, torch=torch.__version__, cuda=torch.version.cuda)
        result.write(out / "result.json", data)
        (out / "result.md").write_text(result.markdown(data), encoding="utf-8")
        print("Ergebnis: " + str(out.relative_to(ROOT)))
        return 0
    except Exception as exc:
        p.exit(1, "Inferenz fehlgeschlagen: " + str(exc) + "\n")

def write_audio(path, output):
    tensor, seconds, rate = output
    # Erwartet Kanäle x Frames, keine Normalisierung; Clip nur für Hörprobe.
    tensor = tensor.detach().cpu().float()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    if tensor.ndim != 2 or tensor.shape[0] not in (1, 2) or tensor.shape[-1] == 0:
        raise ValueError("Unerwartete Audioform")
    if not tensor.isfinite().all().item():
        raise ValueError("Nicht endliche Audioausgabe")
    if abs(seconds - tensor.shape[-1] / rate) > 1e-6:
        raise ValueError("Audiodauer inkonsistent")
    fixture = fixtures.Fixture(tensor.clamp(-1, 1).T.contiguous().flatten().tolist(),
              dict(rate=rate, channels=tensor.shape[0], frames=tensor.shape[-1]))
    fixtures.write_wav(path, fixture)
