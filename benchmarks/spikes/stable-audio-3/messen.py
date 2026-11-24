"""Stable Audio 3: Audio-to-audio aus synthetischem Signal, nur lokaler HF-Cache."""
import os
from benchmarks.spikes.runner import run

def load(args, fixture, torch):
    if not args.model.is_dir():
        raise ValueError("Lokaler vollständiger HF-Cache für small-music erforderlich")
    os.environ["HF_HUB_CACHE"] = str(args.model.resolve())
    from stable_audio_3 import StableAudioModel
    model = StableAudioModel.from_pretrained("small-music", device=args.device)
    waveform = torch.tensor(fixture.samples).reshape(-1, 2).T.contiguous()
    def infer(seed):
        with torch.inference_mode():
            audio = model.generate(prompt="electronic percussion", duration=args.duration,
                                   init_audio=(args.rate, waveform), init_noise_level=0.5,
                                   seed=seed)
            if audio.ndim == 3:
                audio = audio[0]
        return audio, audio.shape[-1] / 44100, 44100
    return infer

if __name__ == "__main__":
    raise SystemExit(run("stable-audio-3", "lookahead", load))
