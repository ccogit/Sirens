"""RAVE: echter lokaler TorchScript-Forward, blockweise mit Streaming-Export."""
from benchmarks.spikes.runner import run

def load(args, fixture, torch):
    if not args.model.is_file():
        raise ValueError("Geprüfter lokaler RAVE-TorchScript-Export erforderlich")
    model = torch.jit.load(str(args.model), map_location=args.device).eval()
    mono = torch.tensor(fixture.samples, device=args.device).reshape(-1, 2).mean(1)
    # Der Export muss mit der angegebenen Samplerate/Blockgröße kompatibel sein.
    def infer(seed):
        torch.manual_seed(seed)
        with torch.inference_mode():
            chunks = [model(x.reshape(1, 1, -1)).reshape(1, -1)
                      for x in mono.split(args.block) if x.numel() == args.block]
            if not chunks:
                raise ValueError("Signal kürzer als Block")
            audio = torch.cat(chunks, dim=-1)
        return audio, audio.shape[-1] / args.rate, args.rate
    return infer

if __name__ == "__main__":
    raise SystemExit(run("rave", "unbekannt", load))
