"""AFTER v2: vollständiger lokaler TorchScript-Audio-to-Audio-Pfad.

API nach acids-ircam/AFTER, Notebook audio_to_audio_demo.ipynb,
Commit 21298c907f469d6c7787c60dd38d46f98981b75c (CC-BY-NC-4.0).
Keine Checkpoints, kein Rückfall auf feste Timbre-Vektoren.
"""
import json
from pathlib import Path
import sys

from benchmarks import fixtures
from benchmarks.spikes import runner
from benchmarks.spikes.after.install import digest


def verify_local(args):
    directory = Path(sys.prefix) / "weights"
    target = directory / "after-audio-to-audio.ts"
    if args.model.resolve() != target.resolve():
        raise ValueError("Registrierter lokaler AFTER-Export erforderlich")
    receipt = json.loads((directory / "local-weight.json").read_text(encoding="utf-8"))
    if (receipt.get("trusted_local_export") is not True
            or not receipt.get("license") or receipt.get("filename") != target.name
            or receipt.get("size_bytes") != target.stat().st_size
            or receipt.get("sha256") != args.sha256.lower()
            or digest(target) != receipt["sha256"]):
        raise ValueError("Lokaler Export nicht freigegeben oder verändert")


def transfer(model, structure, timbre, torch):
    """Die beiden unabhängigen Audioquellen tatsächlich konditionieren."""
    z_structure = model.emb_model_structure.encode(structure)
    z_timbre = model.emb_model_structure.encode(timbre)
    condition = model.encoder_time.forward_stream(z_structure)
    style = model.encoder.forward_stream(z_timbre)
    if model.post_encoder is not None:
        style = model.post_encoder.forward_stream(style)
    model.set_guidance_structure(1.0)
    model.set_nb_steps(10)
    latent = model.sample(torch.randn_like(z_structure), time_cond=condition, cond=style)
    return model.emb_model_structure.decode(latent)


def load(args, fixture, torch):
    verify_local(args)
    if args.rate != 44100:
        raise ValueError("Gepinntes AFTER-Notebook erwartet 44100 Hz")
    model = torch.jit.load(str(args.model), map_location=args.device).eval()
    # Notebook verwendet 64 latente Frames; der Export liefert die Kompressionsrate.
    count = 64 * int(model.ae_ratio)
    if count <= 0 or count > args.rate * 120:
        raise ValueError("Ungültige Codec-Kompressionsrate")
    mono = torch.tensor(fixture.samples, device=args.device).reshape(-1, 2).mean(1)
    if mono.numel() < count:
        raise ValueError("Dauer zu kurz; mindestens %g Sekunden erforderlich" % (count / args.rate))
    structure = mono[:count].reshape(1, 1, -1)
    reference = fixtures.generate("sinus440", args.rate, (count + 1) / args.rate, 1)
    timbre = torch.tensor(reference.samples[:count], device=args.device).reshape(1, 1, -1)

    def infer(seed):
        torch.manual_seed(seed)
        with torch.inference_mode():
            y = transfer(model, structure, timbre, torch)
            if y.numel() != count:
                raise ValueError("Unerwartete Audioform des AFTER-Exports")
            y = y.reshape(1, -1)
        return y, y.shape[-1] / args.rate, args.rate

    return infer


if __name__ == "__main__":
    raise SystemExit(runner.run("after", "lookahead", load))
