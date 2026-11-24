"""Use the application-owned GPUManager and admission lock, never a private one."""
from contextlib import contextmanager

from .contracts import ContractError


class GPUAdapter:
    def __init__(self, manager, admission_lock):
        if manager is None or admission_lock is None:
            raise ContractError("shared GPU admission unavailable")
        self.manager = manager
        self.admission_lock = admission_lock

    @classmethod
    def from_app(cls, app):
        if not getattr(app.cfg, "rt_enabled", False):
            raise ContractError("shared GPU admission unavailable")
        return cls(app.rt_gpu_provider(), app.cuda_admission)

    @contextmanager
    def worker_lease(self, peak_bytes, *, user_action, stopped):
        """For a bounded standalone worker, not a WorkerSupervisor (which leases itself).

        The caller must terminate and reap its process before exiting. Failure to
        confirm termination retains the lease rather than allowing overlapping jobs.
        """
        from ..realtime.gpu_manager import Priority
        if user_action is not True or not callable(stopped):
            raise ContractError("explicit GPU authorization required")
        with self.admission_lock:
            lease = self.manager.acquire(peak_bytes, Priority.VISUALS, lambda: False,
                                         user_action=True, max_leases=1)
        try:
            yield lease
        finally:
            if stopped() is True:
                self.manager.release(lease)
            else:
                raise ContractError("worker termination not confirmed; lease retained")
