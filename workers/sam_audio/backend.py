"""Nur im separaten Worker importieren. Keine Gewichte automatisch beziehen."""
import hashlib
import json
import os
from pathlib import Path

PIN = "bb4c6999d2677c7402360e426afc01ddfad6dce0"


def verify_snapshot(receipt):
    """Lokale, vom Koordinator geprüfte Closure; keinerlei HTTP-Parameter."""
    receipt = Path(receipt)
    info = json.loads(receipt.read_text(encoding="utf-8"))
    if info.get("code_pin") != PIN or info.get("offline_audited") is not True:
        raise ValueError("SAM-Installation nicht offline-geprüft")
    snapshot = Path(info["snapshot"])
    if not snapshot.is_absolute() or not snapshot.is_dir():
        raise ValueError("Lokaler SAM-Snapshot fehlt")
    files = info["files"]
    if not isinstance(files, dict) or not {"checkpoint.pt", "config.json"} <= files.keys():
        raise ValueError("Gewichtsclosure fehlt")
    actual = set()
    for path in snapshot.rglob("*"):
        if path.is_symlink():
            raise ValueError("Snapshot darf keine Symlinks enthalten")
        if path.is_file():
            actual.add(path.relative_to(snapshot).as_posix())
    if actual != set(files):
        raise ValueError("Unvollständige Hashliste")
    for name, digest in files.items():
        with (snapshot / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("Snapshot-Hash stimmt nicht")
    return snapshot


class SamBackend:
    def __init__(self, receipt):
        snapshot = verify_snapshot(receipt)
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                          HF_DATASETS_OFFLINE="1", TORCH_FORCE_WEIGHTS_ONLY_LOAD="1")
        import torch
        import torchaudio
        from sam_audio import SAMAudio, SAMAudioProcessor
        self.torch = torch
        self.audio = torchaudio
        self.device = "cuda"
        self.model = SAMAudio.from_pretrained(str(snapshot)).eval().to(self.device)
        self.processor = SAMAudioProcessor.from_pretrained(str(snapshot))

    def separate(self, mono, rate, prompt):
        torch = self.torch
        model_rate = self.processor.audio_sampling_rate
        audio = torch.tensor(mono, dtype=torch.float32).unsqueeze(0)
        audio = self.audio.functional.resample(audio, rate, model_rate)
        with torch.inference_mode():
            torch.manual_seed(0)
            batch = self.processor(audios=[audio], descriptions=[prompt]).to(self.device)
            target = self.model.separate(batch, predict_spans=False, reranking_candidates=1).target[0]
            target = target.detach().cpu().reshape(-1)
            target = self.audio.functional.resample(target, model_rate, rate)
        # Resampling kann am Ende um wenige Samples aufrunden.
        if abs(target.numel() - len(mono)) > math_rounding(rate, model_rate):
            raise ValueError("SAM-Ausgabe nicht ausgerichtet")
        values = target[:len(mono)].tolist()
        return values + [0.0] * (len(mono) - len(values))


def math_rounding(rate, model_rate):
    return (rate + model_rate - 1) // model_rate + 1
