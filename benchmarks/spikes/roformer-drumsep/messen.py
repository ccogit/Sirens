"""RoFormer/DrumSep: lokaler, experimenteller MSST-Messpfad."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from benchmarks.spikes import runner

PIN = "1523206d12a521bdb20673726562524cf0f9635b"
MODELS = {
    "MelBandRoformer.ckpt": ("mel_band_roformer",
        "configs/KimberleyJensen/config_vocals_mel_band_roformer_kj.yaml", "vocals"),
    "model_drumsep.th": ("htdemucs", "configs/config_drumsep.yaml", "kick"),
}


def verified_model(path):
    manifest = json.loads(Path(__file__).with_name("weights.json").read_text(encoding="utf-8"))
    item = next((x for x in manifest["models"] if x["filename"] == path.name), None)
    if item is None or not item["approved"] or not item["sha256"]:
        raise ValueError("Gewicht nicht freigegeben oder nicht gepinnt")
    if path.stat().st_size != item["size_bytes"]:
        raise ValueError("Falsche Gewichtsgröße")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != item["sha256"]:
            raise ValueError("Falscher Gewichts-Hash")
    return MODELS[path.name]


def load(args, source, torch):
    model_type, config_path, stem = verified_model(args.model)
    if args.rate != 44100:
        raise ValueError("MSST-Konfiguration benötigt 44100 Hz")
    upstream = Path(sys.prefix) / "msst"
    head = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                                   text=True).strip()
    if head != PIN:
        raise ValueError("MSST-Commit stimmt nicht")
    if subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain"],
                               text=True).strip():
        raise ValueError("MSST-Arbeitsbaum ist nicht sauber")
    sys.path.insert(0, str(upstream))
    from utils.settings import get_model_from_config
    from utils.model_utils import demix

    model, config = get_model_from_config(model_type, str(upstream / config_path))
    checkpoint = torch.load(args.model, map_location="cpu", weights_only=True)
    for key in ("state", "state_dict", "model_state_dict"):
        if key in checkpoint:
            checkpoint = checkpoint[key]
            break
    model.load_state_dict(checkpoint, strict=True)
    model.to(args.device).eval()
    config.inference.batch_size = 1
    config.training.use_amp = args.device == "cuda" and model_type != "htdemucs"
    mix = torch.tensor(source.samples, dtype=torch.float32).reshape(-1, 2).T.contiguous()

    def inference(seed):
        torch.manual_seed(seed)
        stems = demix(config, model, mix, torch.device(args.device), model_type)
        audio = torch.as_tensor(stems[stem])
        return audio, audio.shape[-1] / args.rate, args.rate
    return inference


if __name__ == "__main__":
    raise SystemExit(runner.run("roformer-drumsep", "offline", load))
