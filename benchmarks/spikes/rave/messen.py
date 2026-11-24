"""RAVE: kausaler IIL-Export; RTF je vollständigem Eingabeblock."""
import json
from pathlib import Path
import sys
import uuid

from benchmarks.spikes import common, runner
from benchmarks.spikes.rave.install import manifest, verify


def load(args, fixture, torch):
    item = manifest()
    if args.rate != item["rate"] or args.block != item["block"]:
        raise ValueError("IIL-Export benötigt 48000 Hz und 2048 Samples pro Block")
    if args.sha256.lower() != item["sha256"]:
        raise ValueError("Nur der gepinnte und vertrauensbestätigte Export ist zulässig")
    verify(args.model, item)
    model = torch.jit.load(str(args.model), map_location=args.device).eval()
    mono = torch.tensor(fixture.samples, device=args.device).reshape(-1, 2).mean(1)
    blocks = [x.reshape(1, 1, -1) for x in mono.split(args.block)
              if x.numel() == args.block]
    if not blocks:
        raise ValueError("Signal kürzer als Block")
    sync = torch.cuda.synchronize if args.device == "cuda" else lambda: None
    stats_path = runner.ROOT / "benchmarks" / "results" / "local" / (
        "rave-blocks-" + uuid.uuid4().hex[:10] + ".jsonl")
    print("Blockstatistik:", stats_path)

    def infer(seed):
        torch.manual_seed(seed)
        timings, chunks = [], []
        with torch.inference_mode():
            for x in blocks:
                y, elapsed = common.timed(lambda: model.decode(model.encode(x)), sync)
                if y.numel() != args.block:
                    raise ValueError("Export gibt nicht genau einen Mono-Block zurück")
                chunks.append(y.reshape(1, -1))
                timings.append((elapsed, args.block / args.rate))
            audio = torch.cat(chunks, dim=-1)
        row = dict(seed=seed, phase="kalt" if seed == 0 else "warm",
                   block_samples=args.block, rate=args.rate,
                   first_block_ms=timings[0][0]*1000, **common.summarize(timings))
        with stats_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
        return audio, audio.shape[-1] / args.rate, args.rate

    return infer


def main(argv=None):
    return runner.run("rave", "streaming", load, argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
