"""AFTER v2: vollständige Struktur-/Timbre-Konditionierung, Lookahead."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from workers.rave.runtime import Adapter, Unavailable, audio_check, mix

HERE = Path(__file__).resolve().parent
CHUNK = 2048


def factory(device="cuda"):
    from benchmarks.spikes.after.messen import verify_local
    directory = Path(sys.prefix) / "weights"
    path = directory / "after-audio-to-audio.ts"
    receipt = json.loads((directory / "local-weight.json").read_text(encoding="utf-8"))
    if not isinstance(receipt.get("sha256"), str) or not isinstance(receipt.get("license"), str):
        raise ValueError("Gewichtsquittung fehlt")
    verify_local(SimpleNamespace(model=path, sha256=receipt["sha256"]))
    import torch
    if device == "cuda" and not torch.cuda.is_available():
        raise Unavailable("CUDA fehlt")
    # Pro Job neu laden: zustandsbehaftete Encoder dürfen Presets nicht verändern.
    return TorchAfter(lambda: torch.jit.load(str(path), map_location=device).eval(), torch, device)


class TorchAfter:
    def __init__(self, loader, torch, device):
        self.loader, self.torch, self.device = loader, torch, device
        self.model = loader()
        self.frames = 64 * int(self.model.ae_ratio)
        if self.frames <= 0 or self.frames > 262144 or self.frames % CHUNK:
            raise ValueError("Unbekannte Codec-Kompressionsrate")

    def transform(self, structure, timbre, params):
        torch = self.torch
        model = self.model
        try:
            torch.manual_seed(params["seed"])
            with torch.inference_mode():
                def mono(audio):
                    return torch.tensor(audio, device=self.device).reshape(-1, 2).mean(1).reshape(1, 1, -1)
                z_structure = model.emb_model_structure.encode(mono(structure))
                z_timbre = model.emb_model_structure.encode(mono(timbre))
                condition = model.encoder_time.forward_stream(z_structure)
                style = model.encoder.forward_stream(z_timbre)
                if model.post_encoder is not None:
                    style = model.post_encoder.forward_stream(style)
                model.set_guidance_structure(params["guidance"])
                model.set_nb_steps(params["steps"])
                latent = model.sample(torch.randn_like(z_structure), time_cond=condition, cond=style)
                y = model.emb_model_structure.decode(latent)
                if y.numel() != self.frames:
                    raise ValueError("Ungültige Exportform")
                return y.reshape(-1).detach().cpu().tolist()
        finally:
            # Keine Wiederverwendung des zustandsbehafteten Exports zwischen Jobs.
            self.model = None

    def reset(self):
        if self.model is None:
            self.model = self.loader()


class AfterAdapter(Adapter):
    """Eine Struktur + eine Referenz in getrennten Stereo-Blöcken; danach Ausgabe abrufen."""
    def __init__(self, factory=factory, **kw):
        super().__init__(HERE, factory, **kw)
        self.structure, self.timbre, self.output = [], [], []

    def unload(self):
        super().unload()
        with self.lock:
            self.structure, self.timbre, self.output = [], [], []

    def health(self):
        return {**super().health(), "frames": self.model.frames if self.model else 0}

    def transform(self, structure, timbre):
        with self.lock:
            self.check()
            audio_check(structure)
            audio_check(timbre)
            if len(structure) != 2*self.model.frames or len(timbre) != len(structure):
                raise ValueError("AFTER benötigt zwei vollständige Referenzen")
            self.model.reset()
            result = mix(structure, self.model.transform(structure, timbre, self.params), self.params["wet"])
            self.check()
            return result

    def process(self, samples):
        # IPC bleibt unter dem 1-MiB-Limit; keine Dateipfade oder neuen Befehle.
        with self.lock:
            self.check()
            audio_check(samples)
            if not samples:
                if not self.output:
                    raise ValueError("Keine Ausgabe bereit")
                result, self.output = self.output[:CHUNK*2], self.output[CHUNK*2:]
                return result
            if len(samples) != CHUNK*2 or self.output:
                raise ValueError("Erwartet Referenzblock bzw. Abruf der Ausgabe")
            count = self.model.frames*2
            target = self.structure if len(self.structure) < count else self.timbre
            target.extend(samples)
            if len(self.timbre) == count:
                try:
                    self.output = self.transform(self.structure, self.timbre)
                finally:
                    self.structure, self.timbre = [], []
            return []
