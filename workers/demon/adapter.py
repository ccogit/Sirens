"""Lokaler DEMON-Adapter; keine Fremdimporte bei probe oder Import."""
import json
import math
from pathlib import Path
import sys
import threading

HERE = Path(__file__).resolve().parent
INSTALL = "DEMON nicht installiert / nicht gemessen; workers/demon/install.ps1"
MAX_FRAMES = 131072


class Unavailable(RuntimeError):
    pass


def descriptor():
    return json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))["capability"]


class Backend:
    """ACE-Step Session am Pin des Messpfads, ausschließlich im Worker."""
    def __init__(self):
        import os
        from subprocess import check_output
        from unittest.mock import patch
        from benchmarks.spikes.demon.install import verify_snapshot, PIN

        venv = Path(sys.prefix)
        vendor = venv / "demon-src"
        model = venv / "weights" / "checkpoints"
        if sys.prefix == sys.base_prefix or not (venv / "installed.lock").is_file():
            raise Unavailable(INSTALL)
        verify_snapshot(model)
        if (check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"],
                         text=True).strip() != PIN or
                check_output(["git", "-C", str(vendor), "status", "--porcelain"],
                             text=True).strip()):
            raise Unavailable(INSTALL)
        os.environ.update(ACESTEP_MODELS_DIR=str(model.parent),
                          TORCH_FORCE_WEIGHTS_ONLY_LOAD="1",
                          HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        sys.path.insert(0, str(vendor))
        import torch
        from acestep.engine.model_context import ModelContext
        from acestep.engine.session import Session
        from acestep.constants import TASK_INSTRUCTIONS
        from acestep.nodes.types import Audio
        self.torch, self.Audio = torch, Audio
        self.instruction = TASK_INSTRUCTIONS["cover"]
        with patch.object(ModelContext, "_ensure_downloaded",
                          staticmethod(lambda *a, **k: None)), torch.inference_mode():
            self.session = Session(project_root=str(model.parent),
                                   config_path="acestep-v15-turbo", device="cuda",
                                   decoder_backend="eager", vae_backend="eager",
                                   vae_window=0.36, use_flash_attention=False,
                                   offload_text_encoder=True)

    def prepare(self, samples, prompt):
        with self.torch.inference_mode():
            waveform = self.torch.tensor(samples, dtype=self.torch.float32).reshape(-1, 2).T.contiguous()
            source = self.session.prepare_source(self.Audio(
                waveform=waveform.unsqueeze(0), sample_rate=48000))
            cond = self.session.encode_text(tags=prompt, instruction=self.instruction,
                                            refer_latent=source.latent,
                                            duration=len(samples)/96000, bpm=120)
            return self.session.stream(source=source, conditioning=cond, pipeline_depth=1)

    def tick(self, handle, seed, strength):
        with self.torch.inference_mode():
            return handle.tick(seed=seed, denoise=strength)

    def decode(self, handle, latent):
        with self.torch.inference_mode():
            audio = handle.decode(latent, t_start=0.0)
            wave = audio.waveform
            if wave.ndim == 3:
                wave = wave.squeeze(0)
            if audio.sample_rate != 48000 or wave.ndim != 2 or wave.shape[0] != 2:
                raise Unavailable("Unerwartetes DEMON-Ausgabeformat")
            return wave.T.contiguous().reshape(-1).cpu().tolist()

    def close(self):
        self.session = None
        self.torch.cuda.empty_cache()


class Adapter:
    def __init__(self, factory=Backend):
        self.factory = factory
        self.backend = None
        self.cancelled = threading.Event()
        self.lock = threading.RLock()
        self.epoch = -1
        self.failed = False

    def probe(self):
        cap = descriptor()
        if self.failed:
            cap["available"] = False
        return cap

    def load(self, epoch=0, prompt="instrumental electronic drums", strength=0.35, seed=0,
             bypass=False):
        if (type(epoch) is not int or epoch < 0 or epoch < self.epoch
                or not isinstance(prompt, str) or not 0 < len(prompt) <= 512
                or type(strength) not in (int, float) or not 0 <= strength <= 1
                or type(seed) is not int or not 0 <= seed <= 2147483647
                or type(bypass) is not bool):
            raise ValueError("Ungültige DEMON-Parameter")
        with self.lock:
            try:
                if self.backend is None:
                    self.backend = self.factory()
            except Exception as exc:
                self.failed = True
                raise Unavailable(INSTALL) from exc
            self.epoch, self.prompt, self.strength, self.seed, self.bypass = epoch, prompt, strength, seed, bypass
            self.cancelled.clear()
            self.failed = False
        return self.probe()

    def warmup(self):
        # Kein künstlicher Modelllauf; erste Ausgabe bleibt Teil der Kaltmessung.
        if self.backend is None or self.cancelled.is_set():
            raise Unavailable(INSTALL)

    def process(self, samples, epoch=None):
        if not samples or len(samples) % 2 or len(samples) > MAX_FRAMES*2 or any(
                not math.isfinite(x) or abs(x) > 1 for x in samples):
            raise ValueError("Ungültiges Stereo-PCM")
        with self.lock:
            if self.backend is None or self.cancelled.is_set() or (
                    epoch is not None and epoch != self.epoch):
                raise Unavailable("Veraltete oder gestoppte DEMON-Anfrage")
            if self.bypass:
                return list(samples)
            try:
                handle = self.backend.prepare(samples, self.prompt)
                for _ in range(64):
                    if self.cancelled.is_set():
                        raise Unavailable("DEMON abgebrochen")
                    latent = self.backend.tick(handle, self.seed, self.strength)
                    if latent is not None:
                        result = self.backend.decode(handle, latent)
                        if self.cancelled.is_set():
                            raise Unavailable("DEMON abgebrochen")
                        if not result or len(result) % 2 or len(result) > MAX_FRAMES*2 or any(
                                not math.isfinite(x) for x in result):
                            raise Unavailable("Ungültiges DEMON-Ergebnis")
                        return [max(-1., min(1., x)) for x in result]
                raise Unavailable("Keine fertige Ausgabe nach 64 Ticks")
            except Exception as exc:
                if not self.cancelled.is_set():
                    self.failed = True
                raise Unavailable("DEMON-Verarbeitung fehlgeschlagen") from exc

    def cancel(self):
        self.cancelled.set()

    def unload(self):
        self.cancel()
        with self.lock:
            backend, self.backend = self.backend, None
            if backend is not None:
                backend.close()

    def health(self):
        return {"loaded": self.backend is not None, "cancelled": self.cancelled.is_set(),
                "failed": self.failed, "epoch": self.epoch}
