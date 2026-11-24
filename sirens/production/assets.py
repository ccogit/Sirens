"""Offline production asset validation. No audio/model imports in Sirens."""
from __future__ import annotations

import math
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
import re
import wave
from pathlib import Path


class AssetError(ValueError):
    """An asset cannot be used without correction or explicit approval."""


def inspect_wav(path, *, duration_seconds=None, loop=False, speech=False):
    """Inspect PCM24, report technical measurements, never infer musical quality."""
    from .contracts import validate_wav, sha256_file
    validate_wav(path)
    with wave.open(str(path), "rb") as wav:
        channels, frames = wav.getnchannels(), wav.getnframes()
        rate = wav.getframerate()
        peak = energy = clips = 0
        first = last = None
        while chunk := wav.readframes(8192):
            for i in range(0, len(chunk), channels * 3):
                frame = tuple(int.from_bytes(chunk[j:j+3], "little", signed=True)
                              for j in range(i, i + channels * 3, 3))
                if first is None:
                    first = frame
                last = frame
                for sample in frame:
                    peak = max(peak, abs(sample))
                    energy += sample * sample
                    clips += sample in (-8388608, 8388607)
    if not peak or clips:
        raise AssetError("silent or clipped asset")
    duration = frames / rate
    if duration_seconds is not None:
        if not math.isfinite(duration_seconds) or duration_seconds <= 0:
            raise AssetError("invalid requested duration")
        if speech and duration > duration_seconds + 1 / rate:
            raise AssetError("spoken cue exceeds slot; replan, never truncate text")
        if loop and abs(duration - duration_seconds) > 1 / rate:
            raise AssetError("loop length differs from requested length")
    seam = max(abs(a-b) for a,b in zip(first,last)) / 8388608
    if loop and seam > 0.02:
        raise AssetError("loop boundary discontinuity")
    return dict(sample_rate=rate, channels=channels, frames=frames,
                sha256=sha256_file(path), measured=dict(
                    bpm=None, key=None, duration_seconds=duration,
                    peak_dbfs=20 * math.log10(peak / 8388608),
                    rms_dbfs=10 * math.log10(energy / (frames * channels) / 8388608**2),
                    clipped_samples=clips, seam_delta=seam, listening=None))


def approved_source(source, *, commercial=False, allow_test=False):
    """Require explicit usage metadata; unknown rights never pass commercial gate."""
    for field in ("backend", "revision", "license", "use"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise AssetError("missing source " + field)
    if source["use"] not in ({"production", "commercial", "test-only"} if allow_test else {"production", "commercial"}):
        raise AssetError("source is not cleared for production")
    if source["license"].strip().lower() == "unknown" or source.get("license_confirmed") is not True:
        raise AssetError("unknown license")
    if commercial and (source["use"] != "commercial" or source.get("commercial_ok") is not True):
        raise AssetError("commercial use is not approved")
    return source


def asset_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise AssetError("unsafe asset ID")
    return value


class Cancelled(AssetError):
    """The caller cancelled before publication."""


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, indent=2).encode("utf-8")


def _write_json(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(_json_bytes(value))
            f.close()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class Candidate:
    """A rights-confirmed, operator-selected local file, not a plan path."""
    path: Path
    source: dict
    measured: dict


def local_candidate(root, relative, source, measured=None):
    from .contracts import safe_path
    path = safe_path(root, relative)
    if not path.is_file():
        raise AssetError("selected source file is missing")
    return Candidate(path, dict(source), dict(measured or {}))


class Worker:
    """Run only our fixed worker script with a separately installed interpreter.

    lease is supplied by the production coordinator, never invented here.
    The context must hold the central GPU lease for the entire child lifetime.
    No network or GPU is used for PCM conversion.
    """
    def __init__(self, python, *, lease=None, model_dir=None, stable_cache=None,
                 timeout=180, cancelled=lambda: False):
        self.python = Path(python).resolve(strict=True)
        self.lease = lease
        self.model_dir = model_dir
        self.stable_cache = stable_cache
        self.timeout = timeout
        self.cancelled = cancelled
        self.script = Path(__file__).resolve().parents[2] / "workers" / "production_assets" / "worker.py"

    def _invoke(self, payload, dest):
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_DATASETS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"}
        if self.stable_cache is not None:
            env["SIRENS_RT_STABLE_AUDIO_CACHE"] = str(Path(self.stable_cache).resolve())
        payload = {**payload, "output": str(dest.resolve())}
        # The temporary job file is local and is never written to Git.
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp) / "job.json"
            job.write_bytes(_json_bytes(payload))
            with subprocess.Popen([str(self.python), str(self.script), str(job)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  env=env, shell=False) as child:
                try:
                    deadline = time.monotonic() + self.timeout
                    while child.poll() is None:
                        if self.cancelled():
                            raise Cancelled("asset worker cancelled")
                        if time.monotonic() >= deadline:
                            raise AssetError("asset worker timed out")
                        time.sleep(.05)
                    if child.returncode != 0:
                        raise AssetError("asset worker failed; verify local model/cache and installation")
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.wait()

    def convert(self, source, dest):
        self._invoke({"kind": "convert", "input": str(source.resolve())}, dest)

    def generate(self, request, dest):
        if self.lease is None:
            raise AssetError("coordinator GPU lease not supplied")
        if request["kind"] == "speech" and self.model_dir is None:
            raise AssetError("local Qwen3-TTS model is not configured")
        if request["kind"] != "speech" and self.stable_cache is None:
            raise AssetError("verified Stable Audio cache is not configured")
        payload = {"kind": request["kind"], "request": request}
        if request["kind"] == "speech":
            payload["model_dir"] = str(Path(self.model_dir).resolve(strict=True))
        with self.lease():
            self._invoke(payload, dest)


def _cache_key(request, source, input_hash, plan):
    value = dict(version=1, request=request, source=source, input_hash=input_hash,
                 bpm=plan["bpm"], key=plan["key"])
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def render_assets(plan, run_dir, *, resolve, worker=None, generated_sources=None,
                  gap_ids=(), cache_dir=None, commercial=False, allow_test=False,
                  cancelled=lambda: False):
    """Produce one manifest entry per validated request, including explicit errors.

    resolve(request) MUST try the existing AMM/SecondRoom sources first and return
    a vetted Candidate or None. None alone is not permission to generate:
    the coordinator must separately confirm a catalogue gap via gap_ids.
    generated_sources is trusted local configuration keyed by 'speech'/'sound'.
    Never infer a licence or automatically extract reference audio.
    """
    from .contracts import validate_plan, validate_assets, safe_path, sha256_file
    validate_plan(plan)
    root = Path(run_dir).resolve(strict=True)
    manifest_path = safe_path(root, "assets.json")
    assets_dir = safe_path(root, "assets")
    if manifest_path.exists() or assets_dir.exists():
        raise AssetError("run assets already exist; use a new run")
    assets_dir.mkdir()
    cache = None
    if cache_dir is not None:
        cache = Path(cache_dir).resolve()
        cache.mkdir(parents=True, exist_ok=True)
    entries = []
    for original in plan["asset_requests"]:
        request = dict(original)
        identifier = asset_id(request["id"])
        target = safe_path(root, "assets/" + identifier + ".wav")
        try:
            if cancelled():
                raise Cancelled("asset run cancelled")
            if request["kind"] == "speech" and not request.get("text", "").strip():
                raise AssetError("speech text is empty")
            # Spoken word is generated only from exact text; a reused cue must
            # carry the exact same transcript as evidence.
            candidate = resolve(request)
            measured = {}
            if candidate is not None:
                if not isinstance(candidate, Candidate):
                    raise AssetError("invalid selected source")
                source = dict(candidate.source)
                if request["kind"] == "speech" and source.get("text") != request["text"]:
                    raise AssetError("reused speech transcript does not match")
                measured = dict(candidate.measured)
                input_hash = sha256_file(candidate.path)
            else:
                if identifier not in gap_ids:
                    raise AssetError("no selected licensed source; catalogue gap not confirmed")
                if request["kind"] == "sample":
                    raise AssetError("sample request needs a licensed existing source")
                if worker is None:
                    raise AssetError("local asset worker unavailable")
                family = "speech" if request["kind"] == "speech" else "sound"
                source = dict((generated_sources or {}).get(family, {}))
                if request["kind"] != "speech" and not request.get("prompt", "").strip():
                    raise AssetError("generation requires explicit prompt")
                input_hash = None
            source.update(seed=request["seed"], prompt=request.get("prompt"),
                          input_sha256=input_hash)
            if request["kind"] == "speech":
                source["text"] = request["text"]
            approved_source(source, commercial=commercial, allow_test=allow_test)
            key = _cache_key(request, source, input_hash, plan)
            cached = cache / (key + ".wav") if cache else None
            receipt = cache / (key + ".json") if cache else None
            kwargs = dict(duration_seconds=request["duration_seconds"],
                          loop=request["kind"] == "loop", speech=request["kind"] == "speech")
            with tempfile.TemporaryDirectory(dir=assets_dir) as tmp:
                pending = Path(tmp) / "asset.wav"
                cache_hit = False
                if cached and receipt and cached.is_file() and receipt.is_file() and not (
                        cached.is_symlink() or receipt.is_symlink()):
                    try:
                        prior = json.loads(receipt.read_text(encoding="utf-8"))
                        cache_hit = (prior["sha256"] == sha256_file(cached) and
                                     prior["key"] == key)
                        if cache_hit:
                            shutil.copyfile(cached, pending)
                            inspect_wav(pending, **kwargs)
                    except (OSError, ValueError, KeyError, wave.Error):
                        cache_hit = False
                if not cache_hit:
                    pending.unlink(missing_ok=True)
                    if candidate is not None:
                        try:
                            inspect_wav(candidate.path)
                            shutil.copyfile(candidate.path, pending)
                        except (ValueError, OSError, wave.Error):
                            if worker is None:
                                raise AssetError("source needs local WAV conversion")
                            worker.convert(candidate.path, pending)
                        if sha256_file(candidate.path) != input_hash:
                            raise AssetError("source changed during copy")
                    else:
                        worker.generate(request, pending)
                if cancelled():
                    raise Cancelled("asset run cancelled")
                info = inspect_wav(pending, **kwargs)
                if request["kind"] not in ("speech", "loop") and abs(
                        info["measured"]["duration_seconds"] - request["duration_seconds"]) > max(.1, .1 * request["duration_seconds"]):
                    raise AssetError("asset duration differs from request")
                # The upstream measurements are evidence, never plan guesses.
                for field in ("bpm", "key"):
                    info["measured"][field] = measured.get(field)
                if request["kind"] == "loop":
                    bpm = info["measured"]["bpm"]
                    if bpm is None or abs(bpm - plan["bpm"]) > .2:
                        raise AssetError("loop BPM unverified or mismatched")
                    if plan["key"] and request.get("tonal", False) and (
                            info["measured"]["key"] != plan["key"]):
                        raise AssetError("tonal loop key unverified or mismatched")
                if cached and receipt and not cache_hit:
                    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as out:
                        temp = Path(out.name)
                    try:
                        shutil.copyfile(pending, temp)
                        os.replace(temp, cached)
                        _write_json(receipt, {"key": key, "sha256": info["sha256"]})
                    finally:
                        temp.unlink(missing_ok=True)
                os.replace(pending, target)
            entries.append(dict(id=identifier, kind=request["kind"],
                                file="assets/" + target.name, source=source,
                                cache_hit=cache_hit, **info))
        except (AssetError, ValueError, OSError, KeyError, TypeError, wave.Error) as exc:
            # Do not leak absolute paths, local user text or service responses in errors.
            target.unlink(missing_ok=True)
            entries.append(dict(id=identifier, kind=request["kind"],
                                error=str(exc) if isinstance(exc, AssetError) else type(exc).__name__))
    manifest = dict(schema_version=1, assets=entries)
    validate_assets(manifest, plan=plan, root=root)
    _write_json(safe_path(root, "asset_provenance.json"),
                dict(schema_version=1, assets=[dict(id=e["id"], sha256=e.get("sha256"),
                     source=e.get("source"), error=e.get("error")) for e in entries]))
    _write_json(manifest_path, manifest)
    return manifest
