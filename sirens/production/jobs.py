"""Isolated run directories and atomic status using the existing Sirens store."""
from pathlib import Path
from uuid import UUID, uuid4

from ..store import write_json_atomic, jetzt
from .contracts import ContractError, read_manifest, safe_path, validate_status

TERMINAL = {"succeeded", "failed", "cancelled"}


class Cancelled(Exception):
    pass


class RunStore:
    def __init__(self, cfg):
        data = Path(cfg.data_dir)
        data.mkdir(parents=True, exist_ok=True)
        self.root = safe_path(data, "production")
        self.root.mkdir(exist_ok=True)
        self.runs = safe_path(self.root, "runs")
        self.runs.mkdir(exist_ok=True)

    def create(self, parent=None):
        if parent is not None:
            self.get(parent)
        run_id = uuid4().hex
        path = self.get(run_id, exists=False)
        path.mkdir()
        status = dict(schema_version=1, status="queued", stage=None, progress=None,
                      error=None, timestamps={"queued": jetzt()}, run_id=run_id,
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

    def status(self, run_id, state, stage=None, progress=None, error=None):
        path = self.get(run_id)
        old = self.inspect(run_id)
        if old["status"] in TERMINAL:
            raise ContractError("terminal run is immutable")
        if state not in {"running", *TERMINAL}:
            raise ContractError("invalid transition")
        if old["status"] == "queued" and state == "succeeded":
            raise ContractError("queued run cannot succeed")
        old.update(status=state, stage=stage, progress=progress, error=error)
        old["timestamps"][state] = jetzt()
        validate_status(old)
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
