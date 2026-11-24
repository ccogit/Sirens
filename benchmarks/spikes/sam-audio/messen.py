"""SAM Audio: echte Text-Separation mit lokalem Snapshot."""
from benchmarks.spikes.runner import run

def load(args, fixture, torch):
    from sam_audio import SAMAudio, SAMAudioProcessor
    if not args.model.is_dir():
        raise ValueError("Lokaler vollständiger SAM-Audio-Snapshot erforderlich")
    model = SAMAudio.from_pretrained(str(args.model)).eval().to(args.device)
    processor = SAMAudioProcessor.from_pretrained(str(args.model))
    rate = processor.audio_sampling_rate
    import torchaudio
    mono = torch.tensor(fixture.samples).reshape(-1, 2).mean(1).unsqueeze(0)
    mono = torchaudio.functional.resample(mono, args.rate, rate)
    def infer(seed):
        torch.manual_seed(seed)
        with torch.inference_mode():
            batch = processor(audios=[mono], descriptions=["rhythmic clicking"]).to(args.device)
            output = model.separate(batch, predict_spans=False, reranking_candidates=1)
            audio = output.target[0]
        return audio, audio.shape[-1] / rate, rate
    return infer

if __name__ == "__main__":
    raise SystemExit(run("sam-audio", "offline", load))
