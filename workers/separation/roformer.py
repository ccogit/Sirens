"""Expliziter Offline-Dateilauf; kein Download, kein Import im Hauptprozess."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PIN = "1523206d12a521bdb20673726562524cf0f9635b"
SHA = "87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e"


def run(source, output, weight):
    if weight.stat().st_size != 913106900:
        raise ValueError("Falsche Gewichtsgröße")
    with weight.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != SHA:
            raise ValueError("Falscher Gewichts-Hash")
    upstream = Path(sys.prefix) / "msst"
    def git(*args):
        return subprocess.check_output(["git", "-C", str(upstream), *args], text=True).strip()
    if git("rev-parse", "HEAD") != PIN or git("status", "--porcelain"):
        raise ValueError("Ungeprüfter MSST-Arbeitsbaum")
    sys.path.insert(0, str(upstream))
    import torch
    import soundfile as sf
    import numpy as np
    from utils.settings import get_model_from_config
    from utils.model_utils import demix
    if torch.__version__ != "2.7.1+cu128" or not torch.cuda.is_available():
        raise ValueError("Geprüfte CUDA-Umgebung fehlt")
    mix, rate = sf.read(source, dtype="float32", always_2d=True)
    if rate != 44100 or mix.shape[1] != 2:
        raise ValueError("44100 Hz Stereo erforderlich")
    if not np.isfinite(mix).all():
        raise ValueError("Ungültige Audiodaten")
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    kind = "mel_band_roformer"
    config_path = upstream / "configs/KimberleyJensen/config_vocals_mel_band_roformer_kj.yaml"
    model, config = get_model_from_config(kind, str(config_path))
    checkpoint = torch.load(weight, map_location="cpu", weights_only=True)
    for key in ("state", "state_dict", "model_state_dict"):
        if key in checkpoint:
            checkpoint = checkpoint[key]
            break
    model.load_state_dict(checkpoint, strict=True)
    model.to(device).eval()
    config.inference.batch_size = 1
    config.training.use_amp = True
    torch.manual_seed(0)
    with torch.inference_mode():
        stems = demix(config, model, torch.tensor(mix.T.copy()), device, kind)
    vocals = torch.as_tensor(stems["vocals"]).detach().cpu().numpy().T
    if vocals.shape != mix.shape or not np.isfinite(vocals).all():
        raise ValueError("Stem nicht samplegenau oder ungültig")
    instrumental = mix - vocals
    for name, audio in (("vocals", vocals), ("instrumental", instrumental)):
        if np.max(np.abs(audio)) > 1:
            raise ValueError("Stem würde beim PCM-Export clippen")
        sf.write(output / (name + ".wav"), audio, rate, subtype="PCM_24")
    torch.cuda.synchronize(device)
    return {"id": "roformer", "mock": False, "available": True, "mode": "offline",
            "sample_rates": [44100], "channels": 2, "context_frames": 0,
            "hop_frames": 1, "latency_frames": 0, "controls": [],
            "vram_peak_bytes": torch.cuda.max_memory_allocated(device),
            "device": "cuda", "license": "MIT", "model_revision": PIN + ":" + SHA}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--weight", type=Path, required=True)
    p.add_argument("--descriptor", type=Path, required=True)
    args = p.parse_args()
    if not args.output.is_dir() or any(args.output.iterdir()):
        p.error("Leerer privater Ausgabeordner erforderlich")
    descriptor = run(args.source, args.output, args.weight)
    args.descriptor.write_text(json.dumps(descriptor, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
