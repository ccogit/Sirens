"""RAVE-IIL: gepinnter kausaler Export, latente Mutation."""
from pathlib import Path
import sys

from workers.rave.runtime import Adapter, Unavailable, audio_check, mix, preset

HERE = Path(__file__).resolve().parent
FRAMES = 2048


def factory(device="cuda"):
    # Kein Import oder Download beim Probe; ausschließlich lokal geprüfter Export.
    from benchmarks.spikes.rave.install import manifest, verify
    item = manifest()
    directory = Path(sys.prefix) / "weights"
    path = directory / item["filename"]
    verify(path, item)
    if (directory / "rave-trusted.txt").read_text(encoding="ascii").strip() != item["sha256"]:
        raise ValueError("Vertrauensbestätigung fehlt")
    import torch
    if device == "cuda" and not torch.cuda.is_available():
        raise Unavailable("CUDA fehlt")
    model = torch.jit.load(str(path), map_location=device).eval()
    return TorchRave(model, torch, device)


class TorchRave:
    def __init__(self, model, torch, device):
        self.model, self.torch, self.device = model, torch, device

    def transform(self, samples, params):
        torch = self.torch
        with torch.inference_mode():
            x = torch.tensor(samples, device=self.device).reshape(-1, 2).mean(1).reshape(1, 1, -1)
            z = self.model.encode(x)
            if z.ndim != 3 or z.shape[1] != 16:
                raise ValueError("Unbekannte Latentform")
            offsets = torch.tensor([params["latent_"+str(i)] for i in range(16)],
                                   device=self.device, dtype=z.dtype).reshape(1, 16, 1)
            target = z + offsets
            y = self.model.decode(z + params["morph"]*(target-z))
            if y.numel() != FRAMES:
                raise ValueError("Ungültige Exportform")
            return y.reshape(-1).detach().cpu().tolist()


class RaveAdapter(Adapter):
    def __init__(self, factory=factory, **kw):
        super().__init__(HERE, factory, **kw)

    def process(self, samples, *, controls=None):
        with self.lock:
            self.check()
            audio_check(samples)
            if len(samples) != FRAMES*2:
                raise ValueError("RAVE erwartet 2048 Stereo-Frames")
            params = self.params if controls is None else preset(self.cap, {**self.params, **controls})
            result = mix(samples, self.model.transform(samples, params), params["wet"])
            self.check()
            return result
