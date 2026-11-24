"""Mock-Sitzungen: Steuerzustand und begrenzte Arbeit außerhalb des HTTP-Threads."""
import json
import hashlib
import logging
import queue
import struct
import subprocess
import sys
import threading
import wave
from array import array
from collections import OrderedDict

from ..contracts import Ablehnung
from .contracts import (
    SESSION_TRANSITIONS, JOB_TRANSITIONS, asset_id, error, invalid, new_id,
    transition, uint, validate_command, source_path,
)
from .gpu_manager import GPUManager
from .model_registry import ModelRegistry
from .music_analysis import analyse_pcm, source_hash, CorrectionStore
from .pcm import pack
from .recordings import Recording, recording_root, repair, save_session, load_session, validate_session
from .schemas import validate
from .worker_supervisor import WorkerSupervisor

FIXTURE_ID = "33333333333333333333333333333333"
FIXTURE_FRAMES = 48000 * 4
MAX_SESSIONS = 4
MAX_HISTORY = 64
MAX_SOURCE_FRAMES = 48000 * 120
MAX_ASSETS = 64


def fixture_pcm(start, count):
    # Kleines periodisches, deterministisches Stereo-Testsignal, keine Musikdatei.
    return b"".join(struct.pack("<ff", value, -value)
                    for frame in range(start, start + count)
                    for value in (((frame % 128) - 64) / 256,))


class Sources:
    """Registrierte lokale Quellen; keine vom Client gewählten Cache-Pfade."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.RLock()
        self.items = {}
        self.stem_resolvers = {}
        self.grids = {}
        self.digests = {}
        self.recorded = {}
        self.corrections = CorrectionStore(cfg.realtime_dir / "cache" / "beatgrid")

    def register(self, relative):
        path = source_path(self.cfg.music_root, relative)
        return self._register(path, relative)

    def register_stem(self, stem_service, relative, model, stem):
        # Keine Client-Cachepfade: nur der Bestandsdienst darf sie auflösen.
        def resolve():
            path = stem_service.audiodatei(relative, model, stem).resolve()
            if self.cfg.data_dir.resolve() not in path.parents:
                raise error("unavailable")
            if self.cfg.music_root.resolve() in path.parents:
                raise error("unavailable")
            return path
        return self._register(resolve(), relative, resolve)

    def _register(self, path, relative, resolve=None):
        if path.suffix.lower() != ".wav" or not path.is_file():
            raise error("unavailable")
        try:
            with wave.open(str(path), "rb") as wav:
                rate, channels, width, count = (wav.getframerate(), wav.getnchannels(),
                                                wav.getsampwidth(), wav.getnframes())
        except (wave.Error, EOFError, OSError):
            raise invalid("audio") from None
        # Bewusst begrenzter, exakt vergleichbarer Referenzpfad für G2.
        rates = (44100, 48000) if resolve else (48000,)
        if rate not in rates or channels not in (1, 2) or width != 2 or count < 256:
            raise error("unavailable")
        frames = (count - 1) * 48000 // rate + 1
        if frames > MAX_SOURCE_FRAMES:
            raise error("unavailable")
        with self.lock:
            if len(self.items) >= MAX_ASSETS:
                raise error("unavailable")
            aid = new_id()
            metadata = dict(id=aid, kind="source", sample_rate=48000, channels=2, nframes=frames)
            self.items[aid] = (relative, metadata)
            if resolve is not None:
                self.stem_resolvers[aid] = (resolve, rate, count)
            return dict(metadata)

    def metadata(self, aid):
        asset_id(aid)
        if aid == FIXTURE_ID:
            return dict(id=aid, kind="source", sample_rate=48000, channels=2,
                        nframes=FIXTURE_FRAMES)
        with self.lock:
            if aid in self.recorded:
                return dict(self.recorded[aid])
            if aid not in self.items:
                raise error("not_found")
            return dict(self.items[aid][1])

    def load(self, aid):
        if aid == FIXTURE_ID:
            raw = fixture_pcm(0, FIXTURE_FRAMES)
            with self.lock:
                self.digests[aid] = hashlib.sha256(raw).hexdigest()
            return raw
        with self.lock:
            relative, meta = self.items[aid]
            self.grids.pop(aid, None)
            cached = self.stem_resolvers.get(aid)
        rate, count = (cached[1], cached[2]) if cached else (48000, meta["nframes"])
        path = cached[0]() if cached else source_path(self.cfg.music_root, relative)
        try:
            stat = path.stat()
            with wave.open(str(path), "rb") as wav:
                channels = wav.getnchannels()
                if (wav.getframerate() != rate or channels not in (1, 2)
                        or wav.getsampwidth() != 2 or wav.getnframes() != count):
                    raise invalid("audio")
                raw = wav.readframes(count)
            if len(raw) != count * channels * 2:
                raise invalid("audio")
            digest = source_hash(path)
            after = path.stat()
            if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise invalid("audio")
        except (wave.Error, EOFError, OSError):
            raise invalid("audio") from None
        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        if rate != 48000:
            # Begrenzte Offline-Referenz: lineare Interpolation im 48-kHz-Mock,
            # keine Aussage über samplegenaue Stemausrichtung oder Hörqualität.
            stereo = array("f")
            for frame in range(meta["nframes"]):
                left, fraction = divmod(frame * rate, 48000)
                right = min(left + 1, count - 1)
                for ch in range(2):
                    channel = min(ch, channels - 1)
                    a, b = samples[left * channels + channel], samples[right * channels + channel]
                    stereo.append((a + (b - a) * fraction / 48000) / 32768)
        elif channels == 1:
            stereo = array("f", (x/32768 for x in samples for _ in range(2)))
        else:
            stereo = array("f", (x/32768 for x in samples))
        with self.lock:
            self.digests[aid] = digest
        # Analyse beim expliziten Laden; GET dekodiert und hasht niemals.
        try:
            grid = self.corrections.load(digest, 48000)
            if grid is None:
                mono = [(stereo[i]+stereo[i+1])/2 for i in range(0, len(stereo), 24)]
                grid = analyse_pcm(mono, sample_rate=48000)["grid"]
            if grid is not None:
                with self.lock:
                    self.grids[aid] = dict(grid)
        except (Ablehnung, OSError, ValueError, KeyError, TypeError):
            # Ohne belastbares Raster bleibt die automatische Quantisierung gesperrt.
            pass
        if sys.byteorder != "little":
            stereo.byteswap()
        return stereo.tobytes()

    def record_asset(self, path, rate):
        with wave.open(str(path), "rb") as wav:
            count = wav.getnframes()
        aid = new_id()
        meta = dict(id=aid, kind="recording", sample_rate=rate, channels=2, nframes=count)
        with self.lock:
            self.recorded[aid] = meta
        return dict(meta)

    def beatgrid(self, aid):
        self.metadata(aid)
        with self.lock:
            if aid not in self.grids:
                raise error("unavailable")
            return dict(self.grids[aid])


class Recordings:
    """Begrenzte, an eine Sitzung gebundene Exportverwaltung."""
    LIMIT = 16 * 1024**3
    RESERVATION = 4 * 1024**3

    def __init__(self, cfg, sources):
        self.cfg, self.sources = cfg, sources
        self.root = None
        self.items = {}
        self.exports = {}
        self.lock = threading.RLock()

    def _prepare(self):
        if self.root is None:
            self.root = recording_root(self.cfg.realtime_dir / "recordings", self.cfg.music_root)
            for part in self.root.glob("*/segment-*.wav.part"):
                try:
                    repair(self.root, part.relative_to(self.root), self.cfg.music_root)
                except (Ablehnung, OSError, ValueError):
                    logging.warning("RT: Ein verwaistes Aufnahmesegment konnte nicht repariert werden.")
        return self.root

    def _budget(self):
        root = self._prepare()
        used = sum(p.stat().st_size for p in root.glob("*/*") if p.is_file() and not p.is_symlink())
        reserved = sum(rec.max_bytes-rec.total for rec, result in self.items.values() if result is None)
        return max(0, self.LIMIT-used-reserved)

    def create(self, sid, body, rate):
        if not isinstance(body, dict) or set(body) != {"name", "sample_rate"}:
            raise invalid("recording")
        if body["sample_rate"] != rate or type(body["sample_rate"]) is not int:
            raise invalid("sample_rate")
        with self.lock:
            if len(self.items) >= MAX_HISTORY or any(
                    key[0] == sid and result is None for key, (_, result) in self.items.items()):
                raise error("unavailable")
            budget = min(self.RESERVATION, self._budget()-1024**2)
            if budget < 6:
                raise error("unavailable")
            rid = new_id()
            rec = Recording(self.root, self.cfg.music_root, body["name"], rate, max_bytes=budget)
            self.items[sid, rid] = (rec, None)
            return {"id": rid, "next_frame": 0}

    def _get(self, sid, rid):
        asset_id(rid)
        if (sid, rid) not in self.items:
            raise error("not_found")
        return self.items[sid, rid]

    def append(self, sid, rid, start, payload):
        with self.lock:
            rec, result = self._get(sid, rid)
            if result is not None:
                raise invalid("recording")
            try:
                return {"next_frame": rec.append(payload, start)}
            except (Ablehnung, OSError):
                self.close(sid, rid)
                raise

    def close(self, sid, rid):
        with self.lock:
            rec, result = self._get(sid, rid)
            if result is None:
                paths = rec.stop()
                result = {"id": rid, "assets": [self.sources.record_asset(p, rec.rate) for p in paths],
                          "next_frame": rec.total // 6}
                self.items[sid, rid] = (rec, result)
            return result

    def close_session(self, sid):
        with self.lock:
            for key, (_, result) in tuple(self.items.items()):
                if key[0] == sid and result is None:
                    self.close(*key)

    def export(self, sid, body):
        validate_session(body)
        with self.lock:
            with self.sources.lock:
                for source in body["sources"]:
                    if self.sources.digests.get(source["asset_id"]) != source["sha256"]:
                        raise invalid("source_hash")
            for aid in body["assets"]:
                self.sources.metadata(aid)
            if len(self.exports) >= MAX_HISTORY or self._budget() < 5 * 1024**2:
                raise error("unavailable")
            path = save_session(self.root, self.cfg.music_root, body)
            eid = new_id()
            self.exports[sid, eid] = path.relative_to(self.root)
            return {"id": eid}

    def load_export(self, sid, eid):
        asset_id(eid)
        with self.lock:
            if (sid, eid) not in self.exports:
                raise error("not_found")
            return load_session(self.root, self.cfg.music_root, self.exports[sid, eid])


class SidecarProcess:
    """Nur fester lokaler Startbefehl; JSON-Antworten auf privater Pipe."""
    def __init__(self, origins):
        args = [sys.executable, "-u", "-m", "sirens.realtime.sidecar", "--port", "0"]
        for origin in sorted(origins):
            args.extend(("--origin", origin))
        self.process = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.lock = threading.Lock()
        self.responses = queue.Queue(maxsize=2)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.port = self._response()["port"]
            if type(self.port) is not int or not 1 <= self.port <= 65535:
                raise ValueError
        except Exception:
            self.close()
            raise error("unavailable") from None

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put_nowait(json.loads(line))
        except (OSError, ValueError, queue.Full):
            pass

    def _response(self):
        try:
            response = self.responses.get(timeout=3)
        except queue.Empty:
            raise error("unavailable") from None
        if not isinstance(response, dict) or "error" in response:
            raise error("unavailable")
        return response

    def request(self, data):
        with self.lock:
            if self.process.poll() is not None:
                raise error("unavailable")
            try:
                self.process.stdin.write(struct.pack("<I", len(data)) + data)
                self.process.stdin.flush()
            except (OSError, ValueError):
                raise error("unavailable") from None
            return self._response()

    def json(self, **request):
        return self.request(b"J" + json.dumps(request).encode("utf-8"))

    def close(self):
        p = self.process
        if p.poll() is None:
            try:
                self.json(op="stop")
            except (Ablehnung, OSError):
                pass
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=3)
        p.stdin.close()
        p.stdout.close()
        self.reader.join(timeout=1)


class Session:
    def __init__(self, manager, capability, rate):
        self.manager = manager
        self.data = dict(id=new_id(), state="created", epoch=0, seq=None,
                         capability_id=capability, sample_rate=rate, job_id=None)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.pending = queue.Queue(maxsize=8)
        self.thread = None
        self.worker = None
        self.sidecar = None
        self.token = None
        self.job = None
        self.params = {"gain": 1, "delay_frames": 0}
        self.bypass = False
        self.source_frame = 0
        self.render_seq = -1
        self.audio_epoch = -1
        self.asset = None
        self.dry = None
        self.dropped = 0
        self.last_error = None

    def snapshot(self):
        with self.lock:
            return dict(self.data)

    def _state(self, target):
        self.data["state"] = transition(SESSION_TRANSITIONS, self.data["state"], target)

    def _job_state(self, target):
        self.job["state"] = transition(JOB_TRANSITIONS, self.job["state"], target)

    def _epoch(self):
        if self.data["epoch"] == 2**32 - 1:
            raise invalid("epoch")
        self.data["epoch"] += 1
        self.data["seq"] = None
        self.render_seq = -1

    def command(self, body):
        with self.lock:
            last = self.data["seq"]
            validate_command(body, self.data["epoch"], -1 if last is None else last)
            name, args = body["command"], body["args"]
            state = self.data["state"]
            if name == "load":
                if state != "created":
                    raise invalid("state")
                self.asset = self.manager.asset(args["asset_id"])
                if self.asset["kind"] != "source":
                    raise error("unavailable")
                self._state("loading")
                self.job = dict(id=new_id(), session_id=self.data["id"], state="queued",
                                progress=0, asset_id=args["asset_id"], error=None)
                self.data["job_id"] = self.job["id"]
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()
            elif name == "play":
                self._state("playing")
            elif name == "pause":
                self._state("paused")
            elif name == "seek":
                if state not in ("ready", "playing", "paused"):
                    raise invalid("state")
                if args["source_frame"] >= self.asset["nframes"]:
                    raise invalid("source_frame")
                self._epoch()
                self.source_frame = args["source_frame"]
                return self.snapshot()
            elif name == "set_param":
                if state not in ("ready", "playing", "paused"):
                    raise invalid("state")
                key, value = args["name"], args["value"]
                if key not in self.params or not 0 <= value <= (2 if key == "gain" else 48000):
                    raise invalid("value")
                if key == "delay_frames" and type(value) is not int:
                    raise invalid("value")
                self.params[key] = value
            elif name == "bypass":
                if state not in ("ready", "playing", "paused"):
                    raise invalid("state")
                self.bypass = args["enabled"]
            else:
                # Zeitadressierte Befehle brauchen eine gemeinsame Master-Uhr.
                raise error("unavailable")
            self.data["seq"] = body["seq"]
            return self.snapshot()

    def transport(self):
        with self.lock:
            if self.data["state"] not in ("ready", "playing", "paused") or self.token is None:
                raise error("unavailable")
            result = {"port": self.sidecar.port, "token": self.token}
            self.token = None
            return result

    def dry_audio(self):
        with self.lock:
            if self.dry is None or self.data["state"] not in ("ready", "playing", "paused"):
                raise error("unavailable")
            return self.dry

    def render(self, body):
        """Nur Steuerdaten: PCM entsteht serverseitig im Worker-Thread."""
        fields = {"epoch", "seq", "source_frame", "start_frame", "nframes"}
        if not isinstance(body, dict) or set(body) not in (fields, fields | {"audio_epoch"}):
            raise invalid("render")
        with self.lock:
            if self.data["state"] != "playing":
                if self.last_error == "busy_gpu":
                    raise error("busy_gpu")
                raise error("unavailable")
            epoch = uint(body["epoch"], "epoch", 2**32-1)
            if epoch != self.data["epoch"]:
                raise error("stale_epoch")
            audio_epoch = uint(body.get("audio_epoch", epoch), "audio_epoch", 2**32-1)
            if audio_epoch < self.audio_epoch:
                raise error("stale_epoch")
            seq = uint(body["seq"], "seq", 2**32-1)
            if audio_epoch == self.audio_epoch and seq <= self.render_seq:
                raise invalid("seq")
            source = uint(body["source_frame"], "source_frame")
            start = uint(body["start_frame"], "start_frame")
            count = uint(body["nframes"], "nframes", 2048)
            if count < 256 or source + count > self.asset["nframes"]:
                raise invalid("nframes")
            try:
                self.pending.put_nowait((epoch, audio_epoch, seq, source, start, count,
                                         dict(self.params), self.bypass))
            except queue.Full:
                self.dropped += 1
                raise error("unavailable") from None
            self.audio_epoch = audio_epoch
            self.render_seq = seq
            return {"accepted": True}

    def _run(self):
        worker = sidecar = None
        try:
            with self.lock:
                if self.stop.is_set():
                    return
                self._job_state("running")
            dry = self.manager.sources.load(self.asset["id"])
            if self.stop.is_set():
                return
            worker = self.manager.supervisor(self.manager.registry, "mock",
                                             gpu=self.manager.gpu, max_restarts=0)
            worker.start(user_action=True)
            worker.request("load", self.params.copy())
            worker.request("warmup")
            sidecar = self.manager.sidecar_factory(self.manager.origins)
            token = sidecar.json(op="issue", session=self.data["id"], streams=[1])["token"]
            with self.lock:
                if self.stop.is_set():
                    return
                self.worker, self.sidecar, self.token = worker, sidecar, token
                self.dry = dry
                self._state("ready")
                self._job_state("ready")
                self.job["progress"] = 1
            loaded = {"gain": 1, "delay_frames": 0}
            previous = None
            while not self.stop.is_set():
                if not worker.worker.alive() or sidecar.process.poll() is not None:
                    raise error("unavailable")
                try:
                    epoch, audio_epoch, seq, source, start, count, params, bypass = self.pending.get(timeout=.1)
                except queue.Empty:
                    continue
                with self.lock:
                    if epoch != self.data["epoch"] or audio_epoch != self.audio_epoch or self.data["state"] != "playing":
                        continue
                if params != loaded or previous != (audio_epoch, source):
                    worker.request("load", params)
                    loaded = params
                chunk = dry[source*8:(source+count)*8]
                _, wet = worker.request("process", audio=chunk)
                previous = (audio_epoch, source + count)
                block = pack(dict(protocol_version=1, stream_id=1, epoch=audio_epoch, seq=seq,
                                  start_frame=start, nframes=count, channels=2, flags=0,
                                  sample_rate=self.data["sample_rate"]), chunk if bypass else wet)
                with self.lock:
                    if (self.stop.is_set() or epoch != self.data["epoch"] or audio_epoch != self.audio_epoch
                            or self.data["state"] != "playing"):
                        continue
                    if not sidecar.request(b"P" + self.data["id"].encode("ascii") + block).get("ok"):
                        self.dropped += 1
        except (Ablehnung, OSError, ValueError, KeyError, TypeError) as exc:
            with self.lock:
                if not self.stop.is_set():
                    self._state("error")
                    self.last_error = exc.code if isinstance(exc, Ablehnung) else "unavailable"
                    self.token = None
                    if self.job and self.job["state"] in ("queued", "running"):
                        self._job_state("error")
                        self.job["error"] = (exc.as_dict() if isinstance(exc, Ablehnung)
                                             else error("unavailable").as_dict())
        finally:
            try:
                self.manager.recordings.close_session(self.data["id"])
            except (Ablehnung, OSError):
                logging.warning("RT: Aufnahme konnte nicht abgeschlossen werden.")
            try:
                if sidecar:
                    try:
                        sidecar.json(op="revoke", session=self.data["id"])
                    except Ablehnung:
                        pass
                    sidecar.close()
            finally:
                if worker:
                    worker.close()

    def close(self):
        with self.lock:
            if self.data["state"] == "closed":
                return self.snapshot()
            if self.data["state"] != "stopping":
                self._epoch()
                self._state("stopping")
            self.stop.set()
            self.token = None
            self.dry = None
            if self.job and self.job["state"] in ("queued", "running"):
                self._job_state("cancelled")
            thread = self.thread
        if thread:
            thread.join(timeout=15)
            if thread.is_alive():
                with self.lock:
                    self._state("error")
                raise error("unavailable")
        try:
            self.manager.recordings.close_session(self.data["id"])
        except (Ablehnung, OSError):
            with self.lock:
                if self.data["state"] == "stopping":
                    self._state("error")
            raise error("unavailable") from None
        with self.lock:
            if self.data["state"] == "stopping":
                self._state("closed")
            return self.snapshot()


class Sessions:
    def __init__(self, cfg, origins, *, supervisor=WorkerSupervisor, sidecar_factory=SidecarProcess):
        self.registry = ModelRegistry(mock_enabled=cfg.rt_mock)
        self.sources = Sources(cfg)
        self.recordings = Recordings(cfg, self.sources)
        self.gpu = GPUManager(reserve_bytes=cfg.rt_reserve_bytes)
        self.origins = origins
        self.supervisor = supervisor
        self.sidecar_factory = sidecar_factory
        self.lock = threading.RLock()
        self.sessions = OrderedDict()
        self.closed = False
        self.stop = threading.Event()
        self.reconciler = threading.Thread(target=self._reconcile, daemon=True)
        self.reconciler.start()

    def _reconcile(self):
        while not self.stop.wait(1):
            if self.gpu.leases:
                self.gpu.reconcile()

    def create(self, body):
        validate("session_create", body)
        if body["capability_id"] != "mock":
            raise error("unavailable")
        cap = self.registry.resolve("mock")["capability"]
        if body["sample_rate"] not in cap["sample_rates"]:
            raise invalid("sample_rate")
        with self.lock:
            if self.closed:
                raise error("unavailable")
            if sum(s.snapshot()["state"] != "closed" for s in self.sessions.values()) >= MAX_SESSIONS:
                raise error("unavailable")
            for sid, s in list(self.sessions.items()):
                if len(self.sessions) < MAX_HISTORY:
                    break
                if s.snapshot()["state"] == "closed":
                    del self.sessions[sid]
            s = Session(self, "mock", body["sample_rate"])
            self.sessions[s.data["id"]] = s
            return s.snapshot()

    def get(self, sid):
        asset_id(sid)
        with self.lock:
            if sid not in self.sessions:
                raise error("not_found")
            return self.sessions[sid]

    def job(self, jid, cancel=False):
        asset_id(jid)
        with self.lock:
            sessions = tuple(self.sessions.values())
        for s in sessions:
            with s.lock:
                if s.job and s.job["id"] == jid:
                    break
        else:
            raise error("not_found")
        if cancel:
            with s.lock:
                if s.job["state"] not in ("queued", "running"):
                    return dict(s.job)
            s.close()
        with s.lock:
            return dict(s.job)

    def asset(self, aid):
        return self.sources.metadata(aid)

    def close(self):
        with self.lock:
            self.closed = True
            sessions = tuple(self.sessions.values())
        self.stop.set()
        try:
            for s in sessions:
                try:
                    s.close()
                except (Ablehnung, OSError):
                    logging.warning("RT: Sitzung konnte nicht vollständig geschlossen werden.")
        finally:
            self.reconciler.join(timeout=3)
