"""Offline-Stem-Cache: keine Modellimporte im Hauptprozess."""
import hashlib
import json
import shutil
import sys
import tempfile
import threading
import wave
from pathlib import Path

from ..contracts import Ablehnung, safe_audio_path
from .contracts import invalid, error, asset_id, new_id
from .worker_supervisor import WorkerSupervisor

MODELS = {
    "htdemucs": ("demucs-4.0.0", ("vocals", "drums", "bass", "other"), True),
    "htdemucs_6s": ("demucs-4.0.0", ("vocals", "drums", "bass", "other", "piano", "guitar"), True),
    "roformer": ("1523206d12a521bdb20673726562524cf0f9635b:87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e",
                 ("vocals", "instrumental"), True),
    "drumsep": ("unapproved", (), False),
}


def model(name):
    if not isinstance(name, str) or name not in MODELS:
        raise invalid("model")
    return MODELS[name]


def source_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_key(digest, name, revision, params):
    try:
        raw = json.dumps([digest, name, revision, params], sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise invalid("params") from None
    return hashlib.sha256(raw.encode()).hexdigest()


def wav_shape(path):
    with wave.open(str(path), "rb") as stream:
        shape = (stream.getframerate(), stream.getnchannels(), stream.getnframes())
        if not all(shape):
            raise ValueError("Unvollständige WAV-Datei")
        remaining = shape[2]
        width = shape[1] * stream.getsampwidth()
        while remaining:
            count = min(remaining, 65536)
            if len(stream.readframes(count)) != count * width:
                raise ValueError("Unvollständige WAV-Datei")
            remaining -= count
        return shape


class StemAdapter:
    """Trenner erhält Quelle, privaten Ausgabeordner und Parameter; kein HTTP-Pfad."""
    def __init__(self, music_root, cache_root, runners, *, publish_lock=None):
        self.music_root = Path(music_root).resolve()
        self.cache_root = Path(cache_root).resolve()
        if self.cache_root == self.music_root or self.music_root in self.cache_root.parents:
            raise ValueError("Cache darf nicht im Originalordner liegen")
        self.runners = dict(runners)
        self.lock = threading.Lock()
        self.publish_lock = publish_lock if publish_lock is not None else threading.Lock()

    def capabilities(self):
        return [{"id": name, "revision": revision, "stems": list(stems),
                 "available": enabled and name in self.runners, "mode": "offline"}
                for name, (revision, stems, enabled) in MODELS.items()]

    def separate(self, relative, name, params=None, *, fallback=True, cancelled=lambda: False):
        model(name)
        params = {} if params is None else params
        if not isinstance(params, dict):
            raise invalid("params")
        source = safe_audio_path(self.music_root, relative)
        if not source.is_file():
            raise error("not_found")
        with self.lock:
            try:
                return self._run(source, name, params, cancelled)
            except (OSError, RuntimeError, ValueError, EOFError, wave.Error, Ablehnung):
                if cancelled() or not fallback or name != "roformer" or "htdemucs" not in self.runners:
                    raise
                return {**self._run(source, "htdemucs", {}, cancelled), "fallback_from": name}

    def _run(self, source, name, params, cancelled):
        if cancelled():
            raise error("unavailable")
        revision, stems, enabled = model(name)
        if not enabled or name not in self.runners:
            raise error("unavailable")
        digest = source_hash(source)
        key = cache_key(digest, name, revision, params)
        target = self.cache_root / key
        expected = wav_shape(source)
        def valid(directory):
            return (directory.is_dir() and not directory.is_symlink()
                    and {path.name for path in directory.iterdir()} == {stem + ".wav" for stem in stems}
                    and all((directory / (stem + ".wav")).is_file()
                            and not (directory / (stem + ".wav")).is_symlink()
                            and wav_shape(directory / (stem + ".wav")) == expected
                            for stem in stems))
        try:
            hit = valid(target)
        except (OSError, ValueError, EOFError, wave.Error):
            hit = False
        if target.exists() and not hit:
            raise ValueError("Ungültiger Cache; manuelle Bereinigung erforderlich")
        if not hit:
            self.cache_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".stem-", dir=self.cache_root) as temp:
                staging = Path(temp) / "result"
                staging.mkdir()
                self.runners[name](source, staging, params)
                if not valid(staging) or source_hash(source) != digest:
                    raise ValueError("Stem-Format oder Quelle geändert")
                with self.publish_lock:
                    if cancelled():
                        raise error("unavailable")
                    staging.rename(target)
        return {"model": name, "revision": revision, "key": key,
                "stems": list(stems), "cache_hit": hit}


class _DemucsRegistry:
    """Fester Startbefehl aus der lokalen Konfiguration, nie aus HTTP."""
    def __init__(self, registry):
        self.root = registry.root
        self.python = Path(registry.env.get("SIRENS_STEMS_PYTHON") or sys.executable).expanduser()

    def resolve(self, name):
        if name != "htdemucs" or not self.python.is_absolute() or not self.python.is_file():
            raise error("unavailable")
        return {"command": [str(self.python), "-u",
                            str(self.root / "workers/separation/worker.py"), "--demucs"],
                "capability": {"device": "cpu", "controls": [], "mock": False}}


class SeparationJobs:
    """Begrenzte Offline-Jobs, eigene Assets und gemeinsamer GPU-Manager."""
    def __init__(self, cfg, registry, gpu, supervisor=WorkerSupervisor):
        self.cfg, self.registry, self.gpu = cfg, registry, gpu
        self.supervisor = supervisor
        self.root = cfg.realtime_dir.resolve()
        self.cache = self.root / "cache" / "separation"
        self.lock = threading.RLock()
        self.items, self.assets = {}, {}
        self.export_count = 0
        self.closed = False

    def start(self, body):
        if not isinstance(body, dict) or set(body) != {"pfad", "model"}:
            raise invalid("job")
        name = body["model"]
        if name not in ("roformer", "htdemucs"):
            model(name)
            raise error("unavailable")
        source = safe_audio_path(self.cfg.music_root, body["pfad"])
        music = self.cfg.music_root.resolve()
        if self.root == music or music in self.root.parents or self.cache.resolve() != self.cache:
            raise invalid("path")
        if not source.is_file():
            raise error("not_found")
        if source.suffix.lower() != ".wav" or source.stat().st_size > 160 * 1024**2:
            raise invalid("audio")
        with self.lock:
            if self.closed or any(j["_thread"].is_alive() for j in self.items.values()):
                raise error("unavailable")
            if len(self.items) >= 64 or len(self.assets) >= 320:
                raise error("unavailable")
            jid = new_id()
            job = {"id": jid, "state": "queued", "progress": 0, "model": name,
                   "error": None, "assets": {}, "cache_hit": False}
            stop = threading.Event()
            job["_stop"], job["_worker"] = stop, None
            thread = threading.Thread(target=self._run, args=(job, body["pfad"], source), daemon=True)
            job["_thread"] = thread
            self.items[jid] = job
            snapshot = self._snapshot(job)
            thread.start()
            return snapshot

    def _snapshot(self, job):
        result = {key: value for key, value in job.items() if not key.startswith("_")}
        worker = job["_worker"]
        if worker and job["state"] == "running" and worker.file_progress is not None:
            result["progress"] = min(.99, worker.file_progress)
        return result

    def _runner(self, job, name, source, staging, params):
        stop = job["_stop"]
        jid = new_id()
        out = self.root / "jobs" / jid
        ready = out.with_name(jid + ".ready")
        registry = self.registry if name == "roformer" else _DemucsRegistry(self.registry)
        worker = self.supervisor(registry, "separation" if name == "roformer" else name,
                                 gpu=self.gpu, max_restarts=0, music_root=self.cfg.music_root,
                                 realtime_dir=self.root)
        try:
            with self.lock:
                if stop.is_set():
                    raise error("unavailable")
                job["_worker"] = worker
                # Unbekannter Peak: konservatives, explizites Budget; keine Messbehauptung.
                worker.start(user_action=True, peak_bytes=8 * 1024**3)
            result = worker.request_file_job(jid, source, out, params, 3600)
            if stop.is_set():
                raise error("unavailable")
            expected = {stem + ".wav" for stem in model(name)[1]}
            if set(result["files"]) != expected:
                raise invalid("files")
            for filename in result["files"]:
                (ready / filename).rename(staging / filename)
            with self.lock:
                job["vram_peak_bytes"] = result.get("vram_peak_bytes")
        finally:
            worker.close()
            shutil.rmtree(ready, ignore_errors=True)
            with self.lock:
                job["_worker"] = None

    def _run(self, job, relative, source):
        stop = job["_stop"]
        try:
            with self.lock:
                if stop.is_set():
                    return
                job["state"] = "running"
            # RoFormer und Demucs liefern derzeit 44,1-kHz-Stereo; kein
            # implizites Resampling und keine ungemessene Sampleausrichtung.
            rate, channels, frames = wav_shape(source)
            with wave.open(str(source), "rb") as audio:
                if (rate, channels) != (44100, 2) or audio.getsampwidth() not in (2, 3) or frames > 44100 * 600:
                    raise invalid("audio")
            runners = {name: (lambda src, dst, params, name=name:
                       self._runner(job, name, src, dst, params))
                       for name in ("roformer", "htdemucs")}
            result = StemAdapter(self.cfg.music_root, self.cache, runners, publish_lock=self.lock).separate(
                relative, job["model"], cancelled=stop.is_set)
            paths = {"original": source, **{stem: self.cache / result["key"] / (stem + ".wav")
                                          for stem in result["stems"]}}
            prepared, published = {}, {}
            for stem, path in paths.items():
                if stop.is_set():
                    return
                aid = new_id()
                meta = {"id": aid, "kind": "source" if stem == "original" else "cache",
                        "sample_rate": rate, "channels": channels, "nframes": frames}
                prepared[aid] = (path, meta, source_hash(path))
                published[stem] = aid
            with self.lock:
                if stop.is_set():
                    return
                self.assets.update(prepared)
                job.update(model=result["model"], cache_hit=result["cache_hit"],
                           assets=published, state="ready", progress=1)
                if "fallback_from" in result:
                    job["fallback_from"] = result["fallback_from"]
        except Exception as exc:
            with self.lock:
                if not stop.is_set():
                    job.update(state="error", error=(exc.as_dict() if isinstance(exc, Ablehnung)
                                                      else error("unavailable").as_dict()))

    def job(self, jid, cancel=False):
        asset_id(jid)
        with self.lock:
            job = self.items.get(jid)
            if job is None:
                return None
            if cancel and job["state"] in ("queued", "running"):
                job["_stop"].set()
                job["state"] = "cancelled"
                worker, thread = job["_worker"], job["_thread"]
            else:
                return self._snapshot(job)
        if worker:
            worker.cancel()
        thread.join(timeout=15)
        if thread.is_alive():
            raise error("unavailable")
        with self.lock:
            return self._snapshot(job)

    @staticmethod
    def contract_job(detail):
        # Offline-Korrelation ohne Mock-Sitzung; Detailantwort separat.
        return {"id": detail["id"], "session_id": detail["id"], "state": detail["state"],
                "progress": detail["progress"], "asset_id": detail["assets"].get("original"),
                "error": detail["error"]}

    def asset(self, aid, audio=False):
        asset_id(aid)
        with self.lock:
            entry = self.assets.get(aid)
        if entry is None:
            return None
        path, meta, digest = entry
        if not audio:
            return dict(meta)
        if (path.is_symlink() or not path.is_file() or path.resolve() != path
                or source_hash(path) != digest):
            raise error("unavailable")
        return path

    def export(self, jid, stream, length):
        """Expliziter PCM16-Mixexport, niemals ein Pfad vom Client."""
        asset_id(jid)
        with self.lock:
            job = self.items.get(jid)
            if job is None or job["state"] != "ready":
                raise error("not_found")
            meta = self.assets[job["assets"]["original"]][1]
            expected = 44 + meta["nframes"] * 4
            if length != expected or not 44 < length <= 128 * 1024**2:
                raise invalid("audio")
            if self.closed or self.export_count >= 32:
                raise error("unavailable")
            self.export_count += 1
        directory = self.root / "exports" / "separation"
        if (directory.resolve() != directory or directory == self.cfg.music_root.resolve()
                or self.cfg.music_root.resolve() in directory.parents):
            raise invalid("path")
        directory.mkdir(parents=True, exist_ok=True)
        eid = new_id()
        with tempfile.TemporaryDirectory(prefix=".mix-", dir=directory) as temp:
            staging = Path(temp) / "mix.wav"
            with staging.open("xb") as output:
                remaining = length
                while remaining:
                    block = stream.read(min(remaining, 65536))
                    if not block:
                        raise invalid("audio")
                    output.write(block)
                    remaining -= len(block)
            try:
                if wav_shape(staging) != (44100, 2, meta["nframes"]):
                    raise invalid("audio")
                with wave.open(str(staging), "rb") as audio:
                    if audio.getsampwidth() != 2:
                        raise invalid("audio")
            except (ValueError, EOFError, wave.Error):
                raise invalid("audio") from None
            target = directory / (eid + ".wav")
            staging.rename(target)
        return {"id": eid, "file": "exports/separation/" + target.name}

    def close(self):
        with self.lock:
            self.closed = True
            ids = list(self.items)
        for jid in ids:
            self.job(jid, cancel=True)
            thread = self.items[jid]["_thread"]
            thread.join(timeout=15)
            if thread.is_alive():
                raise error("unavailable")
