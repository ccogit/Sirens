"""Offline production asset validation. No audio/model imports in Sirens."""
from __future__ import annotations

import math
import http.client
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
from urllib.parse import urlencode


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
        totals = [0] * channels
        silence = longest_silence = 0
        first = last = None
        while chunk := wav.readframes(8192):
            for i in range(0, len(chunk), channels * 3):
                frame = tuple(int.from_bytes(chunk[j:j+3], "little", signed=True)
                              for j in range(i, i + channels * 3, 3))
                if first is None:
                    first = frame
                last = frame
                silence = silence + 1 if all(abs(s) < 8 for s in frame) else 0
                longest_silence = max(longest_silence, silence)
                for channel, sample in enumerate(frame):
                    totals[channel] += sample
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
    dc_offset = max(abs(total) for total in totals) / (frames * 8388608)
    warnings = []
    if dc_offset > .02:
        warnings.append("DC offset")
    if longest_silence / rate > .5:
        warnings.append("long silence; inspect for dropout or intentional pause")
    if not loop and max(abs(s) for s in (*first, *last)) / 8388608 > .02:
        warnings.append("non-zero cut boundary; listen for clicks")
    return dict(sample_rate=rate, channels=channels, frames=frames,
                sha256=sha256_file(path), measured=dict(
                    bpm=None, key=None, duration_seconds=duration,
                    peak_dbfs=20 * math.log10(peak / 8388608),
                    rms_dbfs=10 * math.log10(energy / (frames * channels) / 8388608**2),
                    clipped_samples=clips, seam_delta=seam, dc_offset=dc_offset,
                    longest_silence_seconds=longest_silence / rate,
                    warnings=warnings, listening=None))


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
                 timeout=180, cancelled=lambda: False, stable_python=None):
        self.python = Path(python).resolve(strict=True)
        self.stable_python = Path(stable_python).resolve(strict=True) if stable_python else self.python
        self.lease = lease
        self.model_dir = model_dir
        self.stable_cache = stable_cache
        self.timeout = timeout
        self.cancelled = cancelled
        self.script = Path(__file__).resolve().parents[2] / "workers" / "production_assets" / "worker.py"
        self._child = None

    @classmethod
    def coordinated(cls, python, gpu_adapter, *, peak_bytes, user_action, **kwargs):
        """Use K00 GPUAdapter with confirmed process termination before release."""
        worker = cls(python, **kwargs)
        worker.lease = lambda: gpu_adapter.worker_lease(
            peak_bytes, user_action=user_action, stopped=worker.stopped)
        return worker

    def stopped(self):
        return self._child is None or self._child.poll() is not None

    def verify_source(self, request, source):
        if request["kind"] == "speech":
            if self.model_dir is None or not (Path(self.model_dir) / "config.json").is_file():
                raise AssetError("local Qwen3-TTS model is missing")
            revision = Path(self.model_dir).resolve().name
            if (not re.fullmatch(r"[0-9a-f]{40}", revision) or
                    source.get("revision") != revision or source.get("backend") != "qwen3-tts-customvoice"):
                raise AssetError("Qwen3-TTS requires a pinned local snapshot and matching provenance")
            source.update(voice_preset="Ryan", voice_language="English", voice_clone=False)
        else:
            revision = "8bdfb53c6b0fbc62113cd571fd37373efe15fa14"
            if source.get("backend") != "stable-audio-3-small-music" or source.get("revision") != revision:
                raise AssetError("Stable Audio source revision does not match verified worker")
            if self.stable_cache is None or not (Path(self.stable_cache) / "models--stabilityai--stable-audio-3-small-music" / "snapshots" / revision).is_dir():
                raise AssetError("verified local Stable Audio snapshot missing")

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
            interpreter = self.stable_python if payload["kind"] not in ("speech", "convert") else self.python
            with subprocess.Popen([str(interpreter), str(self.script), str(job)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  env=env, shell=False) as child:
                self._child = child
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
    from .cache import cache_key
    value = dict(version=1, request=request, source=source, input_hash=input_hash,
                 bpm=plan["bpm"], key=plan["key"])
    return cache_key("asset", value, source["backend"], source["revision"], request["seed"])


def render_assets(plan, run_dir, *, resolve, worker=None, generated_sources=None,
                  gap_ids=(), cache_dir=None, commercial=False, allow_test=False,
                  cancelled=lambda: False):
    """Produce one manifest entry per validated request, including explicit errors.

    resolve(request) MUST try the existing AMM/SecondRoom sources first and return
    a vetted Candidate or None. None alone is not permission to generate:
    the coordinator must separately confirm a catalogue gap via gap_ids.
    generated_sources is trusted local configuration keyed by 'speech'/'sound'.
    cache_dir is the P00 production root (HashCache uses its cache/ subdirectory).
    Never infer a licence or automatically extract reference audio.
    """
    from .contracts import validate_plan, validate_assets, safe_path, sha256_file
    validate_plan(plan)
    root = Path(run_dir).resolve(strict=True)
    manifest_path = safe_path(root, "assets.json")
    assets_dir = safe_path(root, "assets")
    if manifest_path.exists() or assets_dir.exists() or safe_path(root, "asset_provenance.json").exists():
        raise AssetError("run assets already exist; use a new run")
    assets_dir.mkdir()
    cache = None
    if cache_dir is not None:
        from .cache import HashCache
        cache_root = Path(cache_dir).resolve()
        cache_root.mkdir(parents=True, exist_ok=True)
        cache = HashCache(cache_root)
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
            if candidate is None and isinstance(worker, Worker):
                worker.verify_source(request, source)
            approved_source(source, commercial=commercial, allow_test=allow_test)
            key = _cache_key(request, source, input_hash, plan)
            kwargs = dict(duration_seconds=request["duration_seconds"],
                          loop=request["kind"] == "loop", speech=request["kind"] == "speech")
            with tempfile.TemporaryDirectory(dir=assets_dir) as tmp:
                pending = Path(tmp) / "asset.wav"
                # P00 cache verifies immutable bytes before copying.
                cache_hit = cache.restore(key, Path(tmp)) if cache is not None else False
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
                if cache is not None and not cache_hit:
                    cache.publish(key, Path(tmp), ["asset.wav"])
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


class LocalHTTP:
    """Only direct loopback HTTP; no proxy, redirects, external hosts or retries."""
    def __init__(self, port, timeout=15):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid local service port")
        self.port, self.timeout = port, timeout

    def request(self, method, path, body=None, *, binary=False):
        if not path.startswith("/api/") or "\\r" in path or "\\n" in path:
            raise AssetError("invalid local service route")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout)
        try:
            connection.request(method, path, None if body is None else _json_bytes(body),
                               {"Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status not in (200, 202):
                raise AssetError("local service returned HTTP " + str(response.status))
            limit = 64 * 1024 * 1024 if binary else 8 * 1024 * 1024
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise AssetError("local service response exceeds limit")
            return raw if binary else json.loads(raw)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            if isinstance(exc, AssetError):
                raise
            raise AssetError("local service unavailable or response invalid; do not retry uncertain submission") from exc
        finally:
            connection.close()


class SecondRoom:
    """Thin transport over the existing WB-owned delivery ledger."""
    revision = "8cd35755376b11ef753cb323576a824a366a2f1e"

    def __init__(self, transport=None):
        self.http = transport or LocalHTTP(8099)

    def list(self, project_id):
        return self.http.request("GET", "/api/projects/" + asset_id(project_id) + "/deliveries")

    def job(self, job_id):
        return self.http.request("GET", "/api/jobs/" + asset_id(job_id))

    def status(self):
        return self.http.request("GET", "/api/status")

    def generate(self, project_id, *, kind, prompt, op_id, seconds, seed):
        """Explicit submit only; the WB guard and GPU broker remain authoritative."""
        if kind not in ("texture", "loop"):
            raise AssetError("SecondRoom supports texture/loop, not Foley or speech")
        if self.status().get("safe_to_generate") is not True:
            raise AssetError("SecondRoom live/GPU guard not clear")
        return self.http.request("POST", "/api/generate",
                                 dict(project_id=asset_id(project_id), kind=kind,
                                      prompt=prompt, op_id=asset_id(op_id), seconds=seconds,
                                      seeds=[seed], model="turbo"))

    def await_job(self, job_id, *, timeout=180, cancelled=lambda: False):
        deadline = time.monotonic() + timeout
        while True:
            if cancelled():
                raise Cancelled("poll cancelled; upstream job may still be active")
            result = self.job(job_id)
            if result["status"] == "succeeded":
                return result
            if result["status"] not in ("queued", "running"):
                raise AssetError("SecondRoom job did not succeed; inspect existing job, no resubmit")
            if time.monotonic() >= deadline:
                raise AssetError("SecondRoom polling timed out; upstream job may still be active")
            time.sleep(.25)

    def used(self, project_id, *, delivery_ids=(), sample_ids=()):
        """Call only after actual placement, not on discovery or failed runs."""
        return self.http.request("POST", "/api/used",
                                 dict(project_id=asset_id(project_id),
                                      delivery_ids=[asset_id(i) for i in delivery_ids],
                                      sample_ids=[asset_id(i) for i in sample_ids]))


class AMMSamples:
    """Use the existing Sample-DB query and immutable CAS audio route."""
    revision = "26c5ce2fe9641ed958414f78d58643527bc3032f"

    def __init__(self, transport=None):
        self.http = transport or LocalHTTP(8000)

    def search(self, text, *, commercial=False, pack=None):
        params = {"q": text, "limit": 30, "commercial_safe": str(commercial).lower()}
        if pack:
            params["pack"] = pack
        return self.http.request("GET", "/api/samples?" + urlencode(params))

    def signature_kits(self):
        return self.http.request("GET", "/api/factory/signature-kits")

    def selected(self, sample_id, scratch, *, commercial=False):
        """Import one coordinator-selected sample only; no auto harvest."""
        identifier = asset_id(sample_id)
        row = self.http.request("GET", "/api/samples/" + identifier)
        licence = row.get("license") or {}
        licence_id = licence.get("id")
        if (row.get("id") != identifier or row.get("status") != "active" or
                row.get("quality_tier") not in ("A", "B") or
                (row.get("rating") or {}).get("rejected") or
                not licence_id or licence_id.lower() == "unknown"):
            raise AssetError("AMM sample is not active/approved")
        if licence.get("attribution_required") and not row.get("attribution"):
            raise AssetError("AMM sample requires missing attribution")
        source = dict(backend="amm-sampledb", revision=self.revision,
                      sample_id=identifier, license=licence_id,
                      license_confirmed=True, commercial_ok=licence.get("commercial_ok") is True,
                      use="commercial" if commercial else "production",
                      attribution=row.get("attribution"), pack=row.get("pack"),
                      origin=row.get("origin"))
        approved_source(source, commercial=commercial)
        # This is existing local CAS content, not a web download or a reference extraction.
        from .contracts import safe_path
        output = safe_path(scratch, identifier + ".wav")
        data = self.http.request("GET", "/api/samples/" + identifier + "/audio", binary=True)
        if output.exists():
            if output.read_bytes() != data:
                raise AssetError("AMM immutable CAS response changed")
        else:
            with output.open("xb") as f:
                f.write(data)
        return Candidate(output, source, {"bpm": row.get("bpm"), "key": row.get("musical_key")})


def selected_delivery(secondroom, project_id, delivery_id, host_root, *, commercial=False):
    """Resolve an existing verified SecondRoom delivery under a configured local root."""
    delivery_id = asset_id(delivery_id)
    row = next((r for r in secondroom.list(project_id) if r.get("id") == delivery_id), None)
    if not row or row.get("fits") is not True or row.get("path_exists") is not True:
        raise AssetError("SecondRoom delivery is not verified")
    if row.get("job_id") and secondroom.job(row["job_id"]).get("status") != "succeeded":
        raise AssetError("SecondRoom job not succeeded")
    if not row.get("host_path") or not row.get("license"):
        raise AssetError("SecondRoom delivery missing host or licence evidence")
    root = Path(host_root).resolve(strict=True)
    path = Path(row["host_path"])
    if not path.is_absolute() or not path.is_relative_to(root):
        raise AssetError("SecondRoom host path not mapped to approved root")
    source = dict(backend="secondroom", revision=secondroom.revision,
                  delivery_id=delivery_id, job_id=row.get("job_id"),
                  license=row["license"], license_confirmed=True,
                  commercial_ok=row.get("commercial_ok") is True,
                  use="commercial" if commercial else "production",
                  attribution=row.get("attribution"))
    approved_source(source, commercial=commercial)
    return local_candidate(root, path.relative_to(root).as_posix(), source,
                           {"bpm": row.get("bpm"), "key": row.get("musical_key")})


def g1_requests(text, *, seed=101, speech_seconds=8):
    """Reproducible maritime test requests; text must be supplied verbatim."""
    if not isinstance(text, str) or not text.strip():
        raise AssetError("G1 requires the exact spoken cue")
    sounds = (
        ("bell-buoy", "isolated maritime bell buoy, distant metallic ringing over calm water, no music", 4),
        ("seagulls", "a few distant seagull calls over a quiet harbour, no music or speech", 5),
        ("foghorn", "single low distant ship foghorn, soft natural decay, no music", 5),
        ("ship-bell", "one clear brass ship bell strike, natural ringing decay, no music", 3),
    )
    requests = [dict(id=name, kind="foley", prompt=prompt, seed=seed + i,
                     duration_seconds=duration) for i, (name, prompt, duration) in enumerate(sounds)]
    requests.append(dict(id="spoken-cue", kind="speech", text=text,
                         prompt="calm close male spoken word, English, no singing",
                         seed=seed + len(sounds), duration_seconds=speech_seconds))
    return requests


class AssetStage:
    """K00 Runner's assets(brief, plan, root, cancelled) adapter.

    Leave Runner's whole-stage cache disabled for this stage unless its key
    includes the current selection, licensing and model receipts. This adapter
    rechecks rights before restoring each asset through the shared P00 cache.
    """
    def __init__(self, *, resolve, worker_factory=None, generated_sources=None,
                 gap_ids=(), cache_dir=None, commercial=False):
        self.resolve = resolve
        self.worker_factory = worker_factory
        self.generated_sources = generated_sources
        self.gap_ids = tuple(gap_ids)
        self.cache_dir = cache_dir
        self.commercial = commercial

    def assets(self, brief, plan, root, cancelled):
        worker = self.worker_factory(cancelled) if self.worker_factory else None
        return render_assets(plan, root, resolve=self.resolve, worker=worker,
                             generated_sources=self.generated_sources, gap_ids=self.gap_ids,
                             cache_dir=self.cache_dir, commercial=self.commercial,
                             cancelled=cancelled)
