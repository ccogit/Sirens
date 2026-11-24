"""Magenta RealTime 2: 40-ms-JAX-Blöcke, isoliert und ohne Netzbezug."""
import math
import os
from pathlib import Path
import sys
import time
import uuid

from benchmarks.spikes import runner, common
from benchmarks import baseline, fixtures, result
from . import install

NAME = "magenta-realtime"


def save_audio(path, samples, np):
    audio = np.concatenate(samples, axis=0)
    if audio.ndim != 2 or audio.shape[1] != 2 or not np.isfinite(audio).all():
        raise ValueError("Ungültige Stereo-Ausgabe")
    fixtures.write_wav(path, fixtures.Fixture(
        np.clip(audio, -1, 1).flatten().tolist(),
        dict(rate=48000, channels=2, frames=len(audio))))


def one_block(model, conditioning, state):
    # Die Upstream-API materialisiert PCM auf dem Host (JAX device_get).
    wave, state = model.generate(conditioning=conditioning, frames=1, state=state)
    if wave.sample_rate != 48000 or wave.samples.shape != (1920, 2):
        raise ValueError("Unerwartete Magenta-Blockgröße")
    return wave.samples, state


def main(argv=None):
    parser = runner.parser(NAME)
    parser.set_defaults(rate=48000, block=1920)
    args = parser.parse_args(argv)
    if not (0 < args.duration <= 120 and args.rate >= 8000 and args.block == 1920
            and args.repeats >= 2 and 0 <= args.seconds <= 3600):
        parser.error("Ungültige Dauer, Rate oder Wiederholungen; Block fest 1920 Frames")
    if args.dry_run:
        return runner.run(NAME, "offline", None, argv)
    if (sys.prefix == sys.base_prefix or not Path(sys.prefix).name.startswith(".venv-spike-")
            or sys.platform != "linux"):
        parser.error("Isolierte Linux/WSL2-Umgebung erforderlich; siehe BERICHT.md")
    if args.model is None or not args.model.is_dir():
        parser.error("Lokales geprüftes Modellverzeichnis fehlt (--model)")
    try:
        install.verify_all(args.model)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["JAX_PLATFORMS"] = "cuda" if args.device == "cuda" else "cpu"
        os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
        import jax
        import numpy as np
        from magenta_rt import MagentaRT2Jax, paths
        from magenta_rt.audio import Waveform
        from magenta_rt.config import MUSICCOCA

        devices = jax.devices()
        if not devices or (args.device == "cuda" and devices[0].platform not in ("gpu", "cuda")):
            raise ValueError("CUDA-Gerät fehlt")
        paths.set_magenta_home(args.model.resolve())
        source = fixtures.generate(args.signal, args.rate, args.duration, 2)
        wave = Waveform(np.asarray(source.samples, dtype=np.float32).reshape(-1, 2),
                        sample_rate=args.rate)
        out = runner.ROOT / "benchmarks" / "results" / "local" / (NAME + "-" + uuid.uuid4().hex[:10])
        out.mkdir(parents=True, exist_ok=False)
        with runner.Sampler() as cold_gpu:
            model, load_s = common.timed(lambda: MagentaRT2Jax(size="mrt2_small"))
            embedding, embed_s = common.timed(lambda: model.embed_style(wave))
            conditioning = {MUSICCOCA.key: embedding}
            (first, state), first_s = common.timed(lambda: one_block(model, conditioning, None))
        cold = common.summarize([(load_s + embed_s + first_s, 0.04)], cold_gpu.proc_peak)
        cold.update(load_ms=load_s * 1000, embedding_ms=embed_s * 1000,
                    first_inference_ms=first_s * 1000,
                    gpu_total_sampled_peak_mib=cold_gpu.gpu_peak)
        samples = []
        audio = [first]
        min_blocks = math.ceil(args.duration * 25) * args.repeats
        start = time.perf_counter()
        with runner.Sampler() as warm_gpu:
            while len(samples) < min_blocks or time.perf_counter() - start < args.seconds:
                (block, state), elapsed = common.timed(lambda: one_block(model, conditioning, state))
                samples.append((elapsed, len(block) / 48000))
                if len(audio) < 100:
                    audio.append(block)
        warm = common.summarize(samples, warm_gpu.proc_peak)
        warm.update(gpu_total_sampled_peak_mib=warm_gpu.gpu_peak,
                    block_rtf=[common.rtf(s, d) for s, d in samples])
        save_audio(out / "cold.wav", [first], np)
        save_audio(out / "warm.wav", audio, np)
        data = common.make_result(NAME, "offline", baseline.collect(), cold, warm,
            "python -m benchmarks.spikes.magenta-realtime.messen --model <lokaler Pfad>",
            ["JAX-Blockmessung, keine hörbare End-to-End-Latenz; kein Gate.",
             "Fortlaufender Modellzustand, synthetisches Audio als Stilembedding.",
             "VRAM per nvidia-smi abgetastet; WSL2 kann Prozesswerte nicht liefern."])
        data["profil"] = dict(device=args.device, signal=args.signal, rate=args.rate,
                              block=1920, output_rate=48000, duration=args.duration,
                              repeats=args.repeats, seconds=args.seconds, jax=jax.__version__,
                              devices=[str(d) for d in devices])
        result.write(out / "result.json", data)
        (out / "result.md").write_text(result.markdown(data), encoding="utf-8")
        print("Ergebnis:", out)
        return 0
    except Exception as exc:
        parser.exit(1, "Inferenz fehlgeschlagen: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
