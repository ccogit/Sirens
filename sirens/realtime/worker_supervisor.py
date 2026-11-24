"""Persistenter Worker über begrenztes, längenpräfigiertes IPC v1."""
import json
import math
import os
import queue
import signal
import struct
import subprocess
import threading
import time
from uuid import uuid4

from .contracts import error, invalid, ERRORS
from .gpu_manager import Priority
from .model_registry import PROFILES

MAX = 1024 * 1024


def _frame(kind, rid, payload, audio=b""):
    try:
        raw = json.dumps(dict(version=1, type=kind, request_id=rid, payload=payload),
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise invalid("payload") from None
    if len(raw) > MAX or len(audio) > MAX:
        raise invalid("payload")
    return struct.pack("<I", len(raw)) + raw + audio


def _read(pipe):
    header = pipe.read(4)
    if len(header) != 4:
        raise EOFError
    size, = struct.unpack("<I", header)
    if not 0 < size <= MAX:
        raise ValueError
    raw = pipe.read(size)
    if len(raw) != size:
        raise EOFError
    msg = json.loads(raw)
    if (not isinstance(msg, dict) or set(msg) != {"version", "type", "request_id", "payload"}
            or msg["version"] != 1 or not isinstance(msg["payload"], dict)
            or not isinstance(msg["request_id"], str)):
        raise ValueError
    size = msg["payload"].get("audio_bytes", 0)
    if type(size) is not int or not 0 <= size <= MAX or size % 8:
        raise ValueError
    audio = pipe.read(size)
    if len(audio) != size:
        raise EOFError
    return msg, audio


class _WindowsJob:
    """Job-Handle mit KILL_ON_JOB_CLOSE; niemals fremde Prozesse aufnehmen."""
    def __init__(self, process):
        import ctypes as c
        from ctypes import wintypes as w

        class Basic(c.Structure):
            _fields_ = [("PerProcessUserTimeLimit", c.c_int64),
                        ("PerJobUserTimeLimit", c.c_int64),
                        ("LimitFlags", w.DWORD),
                        ("MinimumWorkingSetSize", c.c_size_t),
                        ("MaximumWorkingSetSize", c.c_size_t),
                        ("ActiveProcessLimit", w.DWORD),
                        ("Affinity", c.c_size_t),
                        ("PriorityClass", w.DWORD),
                        ("SchedulingClass", w.DWORD)]

        class IO(c.Structure):
            _fields_ = [(name, c.c_uint64) for name in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class Extended(c.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO),
                        ("ProcessMemoryLimit", c.c_size_t), ("JobMemoryLimit", c.c_size_t),
                        ("PeakProcessMemoryUsed", c.c_size_t), ("PeakJobMemoryUsed", c.c_size_t)]

        k = c.WinDLL("kernel32", use_last_error=True)
        k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.CloseHandle.argtypes = [w.HANDLE]
        self._kernel = k
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(c.get_last_error(), "JobObject fehlt")
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000
        if not (k.SetInformationJobObject(self.handle, 9, c.byref(info), c.sizeof(info))
                and k.AssignProcessToJobObject(self.handle, int(process._handle))):
            code = c.get_last_error()
            self.close()
            raise OSError(code, "Worker konnte JobObject nicht beitreten")

    def close(self):
        if self.handle:
            self._kernel.CloseHandle(self.handle)
            self.handle = None


class _Process:
    def __init__(self, command, cwd):
        self.process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        start_new_session=os.name != "nt")
        self.job = None
        self.last_heartbeat = time.monotonic()
        self.responses = queue.Queue(maxsize=2)
        self.closed = threading.Event()
        self.write_lock = threading.Lock()
        self.stop_lock = threading.Lock()
        try:
            if os.name == "nt":
                self.job = _WindowsJob(self.process)
        except OSError:
            self.process.kill()
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            raise
        self.reader = threading.Thread(target=self._reader, daemon=True)
        self.reader.start()
        self.monitor = threading.Thread(target=self._monitor, daemon=True)
        self.monitor.start()

    def _reader(self):
        try:
            while not self.closed.is_set():
                msg, audio = _read(self.process.stdout)
                if msg["type"] == "heartbeat":
                    self.last_heartbeat = time.monotonic()
                else:
                    self.responses.put_nowait((msg, audio))
        except (EOFError, OSError, ValueError, TypeError, queue.Full):
            self.closed.set()

    def _monitor(self):
        while not self.closed.wait(0.1):
            if self.process.poll() is not None or time.monotonic()-self.last_heartbeat > 3:
                break
        self.stop()

    def write(self, data):
        try:
            with self.write_lock:
                if not self.closed.is_set():
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
        except (OSError, ValueError):
            self.closed.set()

    def stop(self):
        with self.stop_lock:
            if self.process is None:
                return
            self.closed.set()
            p = self.process
            if self.job is not None:
                self.job.close()
            elif os.name != "nt":
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    p.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                p.kill()
            p.wait(timeout=3)
            p.stdin.close()
            p.stdout.close()
            self.process = None

    def alive(self):
        return not self.closed.is_set()


class WorkerSupervisor:
    """Ein persistenter Worker je Instanz; niemals automatisch Modellarbeit wiederholen."""
    def __init__(self, registry, name, *, gpu=None, profile="Performance", max_pending=None,
                 max_restarts=1):
        self.entry = registry.resolve(name)
        self.root = registry.root
        if profile not in PROFILES or type(max_restarts) is not int or max_restarts < 0:
            raise invalid("profile")
        self.profile = PROFILES[profile]
        limit = self.profile["max_pending"] if max_pending is None else max_pending
        if type(limit) is not int or not 1 <= limit <= 128:
            raise invalid("max_pending")
        self.slots = threading.BoundedSemaphore(limit)
        self.serial = threading.Lock()
        self.lifecycle = threading.RLock()
        self.gpu = gpu
        self.lease = None
        self.worker = None
        self.max_restarts = max_restarts
        self.restarts = 0
        self.started = False
        self.stopped = False
        self.deadline_misses = 0

    def _spawn(self):
        try:
            self.worker = _Process(self.entry["command"], self.root)
        except OSError:
            raise error("unavailable") from None

    def start(self, *, user_action=False, priority=Priority.INTERACTION, peak_bytes=None):
        if user_action is not True:
            raise error("unavailable")
        with self.lifecycle:
            if self.started or self.stopped:
                raise error("unavailable")
            cap = self.entry["capability"]
            if cap["device"] != "cpu":
                if self.gpu is None or not self.profile["max_gpu_workers"]:
                    raise error("busy_gpu")
                peak = cap["vram_peak_bytes"]
                if peak == "unknown":
                    peak = peak_bytes
                elif peak_bytes is not None:
                    peak = max(peak, peak_bytes)
                if type(peak) is not int or peak <= 0:
                    raise error("busy_gpu")
                self.lease = self.gpu.acquire(peak, priority, self._evict, user_action=True)
            try:
                self._spawn()
            except Exception:
                if self.lease:
                    self.gpu.release(self.lease)
                    self.lease = None
                raise
            self.started = True

    def _evict(self):
        # GPUManager hält seinen Lock; kein blockierender Gegenlock.
        if not self.lifecycle.acquire(blocking=False):
            return False
        try:
            self.stopped = True
            if self.worker:
                self.worker.stop()
            self.lease = None
            return True
        finally:
            self.lifecycle.release()

    def _current(self):
        with self.lifecycle:
            if not self.started or self.stopped:
                raise error("unavailable")
            if self.worker.alive():
                return self.worker
            self.worker.stop()
            # GPU-Worker nur nach neuer Nutzeraktion und neuer Lease starten.
            if self.entry["capability"]["device"] != "cpu" or self.restarts >= self.max_restarts:
                raise error("unavailable")
            self.restarts += 1
            self._spawn()
            return self.worker

    def request(self, kind, payload=None, *, audio=b"", timeout=5):
        if kind not in {"probe", "load", "warmup", "process", "health", "unload"}:
            raise invalid("type")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise invalid("timeout")
        payload = {} if payload is None else payload
        if not isinstance(payload, dict) or not isinstance(audio, bytes) or len(audio) % 8:
            raise invalid("payload")
        allowed = {"load": {"gain", "delay_frames"},
                   "process": {"delay_seconds", "crash", "memory_bytes", "memory_limit_bytes"}} if self.entry["capability"]["mock"] else {}
        if set(payload) - allowed.get(kind, set()) or (audio and kind != "process"):
            raise invalid("payload")
        if kind == "process":
            payload = {**payload, "audio_bytes": len(audio)}
        rid = uuid4().hex
        data = _frame(kind, rid, payload, audio)
        if not self.slots.acquire(blocking=False):
            raise error("unavailable")
        deadline = time.monotonic() + timeout
        try:
            if not self.serial.acquire(timeout=max(0, deadline-time.monotonic())):
                self.deadline_misses += 1
                raise error("deadline_missed")
            try:
                worker = self._current()
                threading.Thread(target=worker.write, args=(data,), daemon=True).start()
                while True:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        self.deadline_misses += 1
                        worker.stop()
                        raise error("deadline_missed")
                    try:
                        msg, raw = worker.responses.get(timeout=min(remaining, 0.05))
                    except queue.Empty:
                        if not worker.alive():
                            worker.stop()
                            raise error("unavailable")
                        continue
                    if msg["request_id"] != rid:
                        worker.stop()
                        raise error("unavailable")
                    if msg["type"] == "error":
                        code = msg["payload"].get("code")
                        raise error(code if code in ERRORS else "unavailable")
                    if msg["type"] != "result":
                        worker.stop()
                        raise error("unavailable")
                    return (msg["payload"], raw) if kind == "process" else msg["payload"]
            finally:
                self.serial.release()
        finally:
            self.slots.release()

    def cancel(self):
        # Kooperatives Cancel anstoßen, dann den eigenen Prozessbaum sicher beenden.
        worker = self.worker
        if worker and worker.alive():
            threading.Thread(target=worker.write,
                             args=(_frame("cancel", uuid4().hex, {}),), daemon=True).start()
        self.close()

    def close(self):
        with self.lifecycle:
            self.stopped = True
            if self.worker:
                self.worker.stop()
            lease, self.lease = self.lease, None
        if lease is not None:
            self.gpu.release(lease)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
