"""Isolierter MRT2-Small-Backend nach dem gepinnten WP24-Messpfad."""
import os
import sys
from pathlib import Path

from .adapter import HOP, RATE

ENV = Path.home() / ".venv-worker-magenta"


class MagentaBackend:
    def __init__(self):
        if sys.platform != "linux" or Path(sys.prefix).resolve() != ENV.resolve():
            raise RuntimeError("Isolierte Magenta-WSL-Umgebung erforderlich")
        from .install import verify_all, MODEL
        verify_all(MODEL)
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                          JAX_PLATFORMS="cuda", XLA_PYTHON_CLIENT_PREALLOCATE="false")
        import jax
        import numpy as np
        from magenta_rt import MagentaRT2Jax, paths
        from magenta_rt.audio import Waveform
        from magenta_rt.config import MUSICCOCA
        if not any(d.platform in ("gpu", "cuda") for d in jax.devices()):
            raise RuntimeError("CUDA-Gerät fehlt")
        paths.set_magenta_home(MODEL.resolve())
        self.np, self.waveform, self.key = np, Waveform, MUSICCOCA.key
        self.model = MagentaRT2Jax(size="mrt2_small")

    def embed(self, pcm):
        samples = self.np.frombuffer(pcm, dtype="<f4").reshape(-1, 2).copy()
        wave = self.waveform(samples, sample_rate=RATE)
        return {self.key: self.model.embed_style(wave)}

    def generate(self, conditioning, state):
        wave, state = self.model.generate(conditioning=conditioning, frames=1, state=state)
        if wave.sample_rate != RATE or wave.samples.shape != (HOP, 2):
            raise ValueError("Unerwartete Magenta-Blockgröße")
        return self.np.asarray(wave.samples, dtype="<f4").tobytes(), state

    def close(self):
        self.model = None
        # JAX-Speicher endgültig beim Beenden des isolierten Prozesses freigeben.
