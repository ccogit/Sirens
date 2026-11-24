"""Isolated run directories and atomic status using the existing Sirens store."""
import math
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from ..store import write_json_atomic
from .contracts import ContractError, read_manifest, safe_path, validate_status

TERMINAL = {"succeeded", "failed", "cancelled"}


class Cancelled(Exception):
    pass


class RunStore:
    def __init__(self, cfg, *, clock=None):
        self.clock = clock if clock is not None else time.time
        data = Path(cfg.data_dir)
        data.mkdir(parents=True, exist_ok=True)
        self.root = safe_path(data, "production")
        self.root.mkdir(exist_ok=True)
        self.runs = safe_path(self.root, "runs")
        self.runs.mkdir(exist_ok=True)

    def _now(self):
        return datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    @staticmethod
    def _seconds(started, finished):
        # Persisted UTC timestamps also work after process restart/recovery.
        # A backwards wall-clock correction must not create negative durations.
        return max(0.0, (datetime.fromisoformat(finished) -
                         datetime.fromisoformat(started)).total_seconds())

    def create(self, parent=None):
        if parent is not None:
            self.get(parent)
        run_id = uuid4().hex
        path = self.get(run_id, exists=False)
        path.mkdir()
        status = dict(schema_version=1, status="queued", stage=None, progress=None,
                      error=None, timestamps={"queued": self._now()}, run_id=run_id,
                      stages=[], total_seconds=None,
                      parent_run_id=parent)
        write_json_atomic(path / "status.json", status)
        return run_id, path

    def get(self, run_id, *, exists=True):
        try:
            if not isinstance(run_id, str) or UUID(run_id).hex != run_id:
                raise ValueError()
        except (ValueError, AttributeError):
            raise ContractError("invalid run ID") from None
        path = safe_path(self.runs, run_id)
        if exists and not path.is_dir():
            raise ContractError("run not found")
        return path

    def inspect(self, run_id):
        return validate_status(read_manifest(safe_path(self.get(run_id), "status.json")))

    def status(self, run_id, state, stage=None, progress=None, error=None, *, before_write=None):
        path = self.get(run_id)
        old = self.inspect(run_id)
        if old["status"] in TERMINAL:
            raise ContractError("terminal run is immutable")
        if state not in {"running", *TERMINAL}:
            raise ContractError("invalid transition")
        if old["status"] == "queued" and state == "succeeded":
            raise ContractError("queued run cannot succeed")
        now = self._now()
        stages = old.setdefault("stages", [])
        # Only an actual running stage is timed. Repeated progress updates
        # preserve its start; a terminal transition never starts a new stage.
        active = stages[-1] if stages and stages[-1]["finished"] is None else None
        if active is not None and (state in TERMINAL or active["stage"] != stage):
            active["finished"] = now
            active["seconds"] = self._seconds(active["started"], now)
            active = None
        if state == "running" and stage is not None and active is None:
            stages.append(dict(stage=stage, started=now, finished=None, seconds=None))
        old.update(status=state, stage=stage, progress=progress, error=error)
        if state == "running":
            old["timestamps"].setdefault("running", now)
        else:
            old["timestamps"][state] = now
        # Total is elapsed execution time (not queue wait). Old manifests
        # remain readable; their unavailable historical stages are not invented.
        started = old["timestamps"].get("running")
        old["total_seconds"] = self._seconds(started, now) if started else (
            0.0 if state in TERMINAL else None)
        validate_status(old)
        if before_write is not None:
            before_write(old)
        write_json_atomic(path / "status.json", old)
        return old

    def cancel(self, run_id):
        path = self.get(run_id)
        if self.inspect(run_id)["status"] in TERMINAL:
            raise ContractError("terminal run is immutable")
        # Cancellation is a request, not a claim that the process has stopped.
        flag = safe_path(path, "cancel.request")
        flag.touch(exist_ok=True)

    def check_cancel(self, run_id):
        if safe_path(self.get(run_id), "cancel.request").exists():
            raise Cancelled("cancel requested")

    def recover(self, run_id):
        """Explicit recovery after the caller has confirmed the worker is gone."""
        status = self.inspect(run_id)
        if status["status"] not in TERMINAL:
            return self.status(run_id, "failed", status["stage"], error="interrupted; resume as new run")
        return status


# The program is a trusted installed worker, not a command supplied in a brief
# or plan. Limits are set before loading any worker/model code, in the child.
_BOOTSTRAP = """
import resource
import runpy
import sys
cpu, ram, script, run = sys.argv[1:]
resource.setrlimit(resource.RLIMIT_CPU, (int(cpu), int(cpu)))
resource.setrlimit(resource.RLIMIT_AS, (int(ram), int(ram)))
sys.argv = [script, run]
sys.path.insert(0, __import__('os').path.dirname(script))
runpy.run_path(script, run_name='__main__')
"""


def run_file_worker(workers_root, worker_name, interpreter_relative, script_relative,
                    run_dir, *, timeout, cpu_seconds, memory_bytes, check_cancel):
    """Bounded POSIX file-job process; fail closed where hard limits are unavailable.

    Only installed interpreters/scripts within the trusted worker directory are
    accepted. Worker receives only the run directory, not agent-provided code.
    Limits apply per process and are inherited by children, not an aggregate
    cgroup. On Windows a bounded JobObject is still required.
    """
    if os.name != "posix":
        raise ContractError("bounded production file workers unavailable on this platform")
    if (type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0
            or type(cpu_seconds) is not int or cpu_seconds <= 0
            or type(memory_bytes) is not int or memory_bytes <= 0
            or not callable(check_cancel)):
        raise ContractError("invalid worker limits")
    if "/" in worker_name or "\\" in worker_name:
        raise ContractError("invalid worker name")
    worker = safe_path(workers_root, worker_name)
    # Venv Python is normally a symlink on POSIX. Do not accept symlinked
    # worker directories/scripts; the trusted interpreter can be a venv link.
    from .contracts import validate_relative_path
    validate_relative_path(interpreter_relative)
    parts = interpreter_relative.split("/")
    interpreter = safe_path(worker, "/".join(parts[:-1])) / parts[-1] if len(parts) > 1 else worker / parts[-1]
    script = safe_path(worker, script_relative)
    if not interpreter.is_file() or not script.is_file():
        raise ContractError("worker not installed")
    run_dir = Path(run_dir).resolve(strict=True)
    check_cancel()
    # Do not inherit credentials or model download settings from the service.
    env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG")
           if key in os.environ}
    env.update(PYTHONNOUSERSITE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    process = subprocess.Popen([str(interpreter), "-I", "-c", _BOOTSTRAP,
                                str(cpu_seconds), str(memory_bytes), str(script), str(run_dir)],
                               cwd=worker, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            check_cancel()
            if time.monotonic() >= deadline:
                raise ContractError("worker deadline exceeded")
            time.sleep(0.05)
        if process.returncode != 0:
            raise ContractError("worker exit code " + str(process.returncode))
        check_cancel()
    finally:
        # Reap the whole worker group even if the leader has already exited.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)
