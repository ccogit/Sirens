"""Isolated asset worker. Only this process imports audio/model libraries.

Invoked by the coordinator under its GPU lease, with a temporary JSON job.
No installation or model download at runtime.
"""
import json
import math
import os
import sys
from pathlib import Path

for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE",
            "HF_HUB_DISABLE_TELEMETRY"):
    os.environ[key] = "1"


def write_wav(output, samples, rate, target_frames=None):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples[:, None]
    if (samples.ndim != 2 or samples.shape[1] not in (1, 2)
            or not len(samples) or not np.isfinite(samples).all()):
        raise ValueError("invalid audio")
    if not isinstance(rate, int) or not 8000 <= rate <= 192000:
        raise ValueError("invalid source sample rate")
    if rate != 48000:
        gcd = math.gcd(rate, 48000)
        samples = resample_poly(samples, 48000 // gcd, rate // gcd, axis=0)
    if target_frames is not None:
        # Only one-sample rounding differences may be corrected. No text cut,
        # time stretching or hiding a short generation.
        if abs(len(samples) - target_frames) > 1:
            raise ValueError("generated duration does not match request")
        if len(samples) < target_frames:
            samples = np.pad(samples, ((0, 1), (0, 0)), mode="edge")
        samples = samples[:target_frames]
    peak = float(np.max(np.abs(samples)))
    if peak == 0 or peak >= 1:
        raise ValueError("silent or clipped source")
    if output.exists():
        raise ValueError("output already exists")
    sf.write(str(output), samples, 48000, format="WAV", subtype="PCM_24")


def stable(request, output):
    import numpy as np
    # Reuse the verified existing loader/cache pin and inference implementation.
    # The existing file_job endpoint accepts only pad enums and synthesizes its
    # own prompt; it cannot carry maritime Foley prompts.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stable_audio"))
    from adapter import Adapter, RATE, REVISION
    duration, seed, prompt = request["duration_seconds"], request["seed"], request["prompt"]
    if not .25 <= duration <= 30 or type(seed) is not int or not 0 <= seed < 2**53:
        raise ValueError("Stable Audio duration/seed outside tested envelope")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 1000:
        raise ValueError("Stable Audio prompt")
    adapter = Adapter()
    try:
        adapter.load()
        pcm = adapter.model(prompt, duration, seed)
        samples = np.frombuffer(pcm, dtype="<f4").reshape(-1, 2)
        # Duration tolerance for non-loop assets is checked in the main process.
        target = round(duration * 48000) if request["kind"] == "loop" else None
        write_wav(output, samples, RATE, target)
    finally:
        adapter.unload()


def speech(request, output, model_dir):
    import torch
    from qwen_tts import Qwen3TTSModel
    model_dir = Path(model_dir).resolve(strict=True)
    if not (model_dir / "config.json").is_file():
        raise ValueError("Qwen3-TTS local model missing")
    text = request["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty text")
    torch.manual_seed(request["seed"])
    torch.cuda.manual_seed_all(request["seed"])
    model = Qwen3TTSModel.from_pretrained(
        str(model_dir), device_map="cuda:0", dtype=torch.bfloat16,
        attn_implementation="sdpa", local_files_only=True)
    # Preset speaker only: no arbitrary reference audio or voice cloning.
    wavs, rate = model.generate_custom_voice(
        text=text, language="English", speaker="Ryan",
        instruct="Calm, intimate, close-miked male spoken word. Speak naturally, "
                 "with gentle pauses at punctuation. No singing. Do not add words.")
    if len(wavs) != 1:
        raise ValueError("one spoken cue expected")
    write_wav(output, wavs[0], int(rate))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: worker.py LOCAL_JOB_JSON")
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = Path(job["output"])
    if not output.is_absolute() or not output.parent.is_dir():
        raise ValueError("output path")
    if job["kind"] == "convert":
        import soundfile as sf
        samples, rate = sf.read(job["input"], dtype="float32", always_2d=True)
        write_wav(output, samples, rate)
    elif job["kind"] == "speech":
        speech(job["request"], output, job["model_dir"])
    elif job["kind"] in ("texture", "foley", "loop", "fill"):
        stable(job["request"], output)
    else:
        raise ValueError("unsupported asset kind")


if __name__ == "__main__":
    main()
