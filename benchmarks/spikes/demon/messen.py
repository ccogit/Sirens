"""DEMON Session-Spike: synthetische Quelle, keine Web-Demo."""
import os
from pathlib import Path
import sys
from unittest.mock import patch

from benchmarks.spikes import runner
from benchmarks.spikes.demon.install import verify_snapshot, PIN


def loader(args, fixture, torch):
    model = args.model.resolve()
    verify_snapshot(model)
    vendor = Path(sys.prefix) / "demon-src"
    if not (vendor / "acestep" / "engine" / "session.py").is_file():
        raise ValueError("Gepinnter DEMON-Quellcode fehlt")
    from subprocess import check_output
    if check_output(["git", "-C", str(vendor), "rev-parse", "HEAD"],
                    text=True).strip() != PIN:
        raise ValueError("Falscher DEMON-Commit")
    if check_output(["git", "-C", str(vendor), "status", "--porcelain"],
                    text=True).strip():
        raise ValueError("DEMON-Checkout verändert")
    os.environ["ACESTEP_MODELS_DIR"] = str(model.parent)
    os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"] = "1"
    sys.path.insert(0, str(vendor))
    from acestep.engine.model_context import ModelContext
    from acestep.engine.session import Session
    from acestep.constants import TASK_INSTRUCTIONS
    from acestep.nodes.types import Audio

    def reject_download(*args, **kwargs):
        raise RuntimeError("Automatischer Modellbezug gesperrt")

    # Der gepinnte ModelContext ruft diese Methode vor dem Laden auf.
    # Der lokale Snapshot wurde bereits vollständig geprüft.
    with patch.object(ModelContext, "_ensure_downloaded", staticmethod(lambda *a, **k: None)):
        with torch.inference_mode():
            session = Session(project_root=str(model), config_path="acestep-v15-turbo",
                              device=args.device, decoder_backend="eager",
                              vae_backend="eager", use_flash_attention=False,
                              offload_text_encoder=args.device == "cuda")
            waveform = torch.tensor(fixture.samples, dtype=torch.float32).reshape(-1, 2).T.contiguous()
            if args.rate != 48000:
                import torchaudio
                waveform = torchaudio.functional.resample(waveform, args.rate, 48000)
            source = session.prepare_source(Audio(waveform=waveform.unsqueeze(0), sample_rate=48000))
            cond = session.encode_text(tags="instrumental electronic drums",
                                       instruction=TASK_INSTRUCTIONS["cover"],
                                       refer_latent=source.latent, duration=args.duration,
                                       bpm=fixture.truth.get("bpm", 120))
            depth = int(os.environ.get("SIRENS_DEMON_DEPTH", "1"))
            if depth not in (1, 4):
                raise ValueError("Ringtiefe muss 1 oder 4 sein")
            handle = session.stream(source=source, conditioning=cond, pipeline_depth=depth)

    def backend(seed):
        with torch.inference_mode():
            # Ein Runner-Sample umfasst alle Ticks bis zur nächsten fertigen
            # Ausgabe inklusive Decode. Kein RTF aus leeren Warmup-Ticks.
            for _ in range(64):
                latent = handle.tick()
                if latent is not None:
                    audio = handle.decode(latent)
                    wave = audio.waveform
                    if wave.ndim == 3:
                        wave = wave.squeeze(0)
                    return wave, wave.shape[-1] / audio.sample_rate, audio.sample_rate
            raise RuntimeError("Keine fertige Ausgabe nach 64 Ticks")
    return backend


if __name__ == "__main__":
    raise SystemExit(runner.run("demon", "streaming", loader))
