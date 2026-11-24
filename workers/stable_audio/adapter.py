"""Stable Audio 3 small-music, ausschließlich explizit geladener lokaler Cache."""
import hashlib
import math
import os
from pathlib import Path

REVISION = "8bdfb53c6b0fbc62113cd571fd37373efe15fa14"
MODEL = "models--stabilityai--stable-audio-3-small-music"
HASHES = {
    "model.safetensors": "da85866b11b01d0694d990785f6abbd79c8064df1b0e6f8aea52935e0ef84b64",
    "model_config.json": "100776f25af5aa83f70e0c6b384de6690cb4e5ad01c24f7cfbb6524d18765f06",
    "t5gemma-b-b-ul2/model.safetensors": "9b05ea5a4f211d023832f706fb2c0e83e4fc721b6da35ab69ceb0b55eb7800d3",
    "t5gemma-b-b-ul2/tokenizer.json": "7794135caa3ea73918949c902a781cc61dab674a4b59c17d85931c77c1114cbd",
    "t5gemma-b-b-ul2/tokenizer.model": "61a7b147390c64585d6c3543dd6fc636906c9af3865a5548f27f31aee1d4c8e2",
}
PAD_TYPES = ("Rise", "Fill", "Drop", "Break", "Bassline", "Extend")
RATE = 44100


def validate_job(job):
    if set(job) != {"type", "prompt", "seed", "strength", "bars", "duration"}:
        raise ValueError("Pad-Parameter")
    if job["type"] not in PAD_TYPES or type(job["bars"]) is not int or job["bars"] not in (1, 2, 4, 8):
        raise ValueError("Pad-Typ/Takte")
    if not isinstance(job["prompt"], str) or not 0 < len(job["prompt"].strip()) <= 1000:
        raise ValueError("Prompt")
    if type(job["seed"]) is not int or not 0 <= job["seed"] < 2**53:
        raise ValueError("Seed")
    for key, low, high in (("strength", 0, 1), ("duration", 0.25, 30)):
        value = job[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(key)
    return dict(job)


def verify_cache(cache):
    root = Path(cache).resolve() / MODEL
    if (root / "refs/main").read_text(encoding="utf-8").strip() != REVISION:
        raise ValueError("Falsche Modellrevision")
    snapshot = root / "snapshots" / REVISION
    for name, expected in HASHES.items():
        with (snapshot / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Gewicht/Config stimmt nicht: " + name)
    return snapshot


class Adapter:
    def __init__(self, loader=None):
        self.loader = loader or self._load_model
        self.model = None
        self.warmed = False
        self.clip = None

    @staticmethod
    def _load_model():
        cache = os.environ.get("SIRENS_RT_STABLE_AUDIO_CACHE")
        if not cache:
            raise ValueError("Lokaler Cache fehlt")
        verify_cache(cache)
        os.environ["HF_HUB_CACHE"] = str(Path(cache).resolve())
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from stable_audio_3 import StableAudioModel
        import torch
        model = StableAudioModel.from_pretrained("small-music", device="cuda")

        def infer(prompt, duration, seed):
            with torch.inference_mode():
                audio = model.generate(prompt=prompt, duration=duration, seed=seed, steps=8)
                if audio.ndim == 3:
                    audio = audio[0]
                if audio.ndim != 2 or audio.shape[0] != 2 or not torch.isfinite(audio).all():
                    raise ValueError("Ungültiges Audio")
                # Native 44,1 kHz; keine implizite Zeitdehnung. Peak-Schutz.
                audio = audio.detach().float().cpu()
                peak = float(audio.abs().max())
                if peak > 0.89125:
                    audio = audio * (0.89125 / peak)
                return audio.T.contiguous().numpy().astype("<f4").tobytes()
        return infer

    def load(self):
        self.unload()
        self.model = self.loader()

    def warmup(self):
        if self.model is None:
            raise ValueError("Nicht geladen")
        self.model("electronic percussion", 8, 0)
        self.warmed = True

    def generate(self, job):
        job = validate_job(job)
        if not self.warmed:
            raise ValueError("Nicht aufgewärmt")
        self.clip = None
        # Stärke ist Wet-Anteil im Einsatzplan; keine ungemessene Modellsteuerung.
        raw = self.model(job["type"] + ": " + job["prompt"], job["duration"], job["seed"])
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 31 * RATE * 8 or len(raw) % 8:
            raise ValueError("Clipformat")
        self.clip = raw
        return {"frames": len(raw)//8, "sample_rate": RATE, "channels": 2, "strength": job["strength"]}

    def chunk(self, offset, frames):
        if (self.clip is None or type(offset) is not int or type(frames) is not int
                or offset < 0 or not 1 <= frames <= 131072 or offset + frames > len(self.clip)//8):
            raise ValueError("Clipbereich")
        return self.clip[offset*8:(offset+frames)*8]

    def unload(self):
        self.clip = None
        self.model = None
        self.warmed = False
