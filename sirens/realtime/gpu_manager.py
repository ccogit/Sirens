"""Konservative VRAM-Zuteilung; nur eigene Leases dürfen entladen werden."""
from dataclasses import dataclass
from enum import IntEnum
from threading import RLock
from uuid import uuid4

from .contracts import error, invalid
from ..contracts import Ablehnung
from ..starter import ClaudeStarter, jetzt
from .telemetry import read_gpu
from .model_registry import PROFILES

GIB = 1024**3


class Priority(IntEnum):
    VISUALS = 0
    BACKGROUND = 1
    INTERACTION = 2
    NEXT_SECTION = 3
    AUDIO = 4


@dataclass(frozen=True)
class Lease:
    id: str
    peak_bytes: int
    priority: Priority
    owner: str = "worker"


class GPUManager:
    def __init__(self, telemetry=read_gpu, reserve_bytes=5*GIB//2, profile="Performance"):
        if type(reserve_bytes) is not int or reserve_bytes < 0:
            raise invalid("reserve_bytes")
        self.reserve_bytes = reserve_bytes
        self._telemetry = telemetry
        self._lock = RLock()
        self._leases = {}
        self._profile = "Performance"
        self.set_profile(profile)

    @property
    def profile(self):
        with self._lock:
            return self._profile

    def set_profile(self, profile):
        if type(profile) is not str or profile not in PROFILES:
            raise invalid("profile")
        with self._lock:
            # Kein überraschender Abbruch laufender Audio-Worker beim Profilwechsel.
            if sum(l.owner == "worker" for l, _ in self._leases.values()) > PROFILES[profile]["max_gpu_workers"]:
                raise error("busy_gpu")
            self._profile = profile
            return profile

    @property
    def leases(self):
        with self._lock:
            return tuple(item[0] for item in self._leases.values())

    def lease_snapshot(self):
        """Separat vom eingefrorenen Telemetrievertrag v1."""
        with self._lock:
            return [dict(id=l.id, owner=l.owner, peak_bytes=l.peak_bytes,
                         priority=l.priority.name) for l, _ in self._leases.values()]

    def acquire_claude(self):
        """Unbekannter Peak: Claude exklusiv, nicht durch den Manager beenden.

        Ohne Telemetrie bleibt die Exklusivsperre aktiv. Keine behauptete Messung.
        """
        return self.acquire_external("claude")

    def acquire_external(self, owner):
        if owner not in ("claude", "legacy_cuda"):
            raise invalid("owner")
        with self._lock:
            if self._leases:
                raise error("busy_gpu")
            snapshot = self._telemetry()
            if snapshot.available and (snapshot.free is None or
                    snapshot.free < self.reserve_bytes + 8*GIB):
                raise error("busy_gpu")
            lease = Lease(uuid4().hex, 8*GIB, Priority.BACKGROUND, owner)
            self._leases[lease.id] = (lease, lambda: False)
            return lease

    def _free(self):
        snapshot = self._telemetry()
        if not snapshot.available or snapshot.free is None:
            return -1
        # Peak zusätzlich zum gemeldeten Verbrauch zählen: bewusst konservativ,
        # da nvidia-smi keine sichere Zuordnung zu eigenen Leases garantiert.
        return snapshot.free - self.reserve_bytes - sum(
            lease.peak_bytes for lease, _ in self._leases.values())

    def _evict(self, priority=None):
        candidates = sorted(self._leases.values(), key=lambda item: item[0].priority)
        for lease, unload in candidates:
            if priority is None or lease.priority < priority:
                # Vertrag: erst nach bestätigter Freigabe True zurückgeben.
                try:
                    released = unload() is True
                except Exception:
                    released = False
                if released:
                    self._leases.pop(lease.id, None)
                    return True
        return False

    def acquire(self, peak_bytes, priority, unload, *, user_action=False, max_leases=None):
        if (type(peak_bytes) is not int or peak_bytes <= 0 or
                not isinstance(priority, Priority) or not callable(unload)):
            raise invalid("lease")
        if max_leases is not None and (type(max_leases) is not int or max_leases <= 0):
            raise invalid("max_leases")
        if user_action is not True:
            raise error("unavailable")
        with self._lock:
            if any(l.owner != "worker" for l, _ in self._leases.values()):
                raise error("busy_gpu")
            limit = PROFILES[self._profile]["max_gpu_workers"]
            if max_leases is not None:
                limit = min(limit, max_leases)
            if limit == 0:
                raise error("busy_gpu")
            while self._free() < peak_bytes or len(self._leases) >= limit:
                if not self._evict(priority):
                    raise error("busy_gpu")
            lease = Lease(uuid4().hex, peak_bytes, priority)
            self._leases[lease.id] = (lease, unload)
            return lease

    def release(self, lease):
        """Nur aufrufen, nachdem der eigene Worker seine Ressourcen freigegeben hat."""
        with self._lock:
            current = self._leases.get(lease.id)
            if current and current[0] is lease:
                self._leases.pop(lease.id)

    def reconcile(self):
        """Bei externer Last oder Telemetrieverlust niedrigste Priorität zuerst entladen."""
        with self._lock:
            while self._free() < 0:
                if not self._evict():
                    return False
            return True


class ManagedClaudeStarter(ClaudeStarter):
    """Exklusive Lease über eine Sitzung einschließlich vorgemerkter Folgeläufe."""
    def __init__(self, cfg, manager, admission_lock, **kwargs):
        super().__init__(cfg, **kwargs)
        self.manager = manager
        self.admission_lock = admission_lock
        self._gpu_lease = None
        self._lease_manager = None

    def starten(self, grund=""):
        with self.admission_lock:
            return super().starten(grund)

    def _release_gpu(self):
        if self._gpu_lease is not None:
            self._lease_manager.release(self._gpu_lease)
            self._gpu_lease = self._lease_manager = None

    def _los(self, grund):
        if self._gpu_lease is None:
            manager = self.manager()
            try:
                self._gpu_lease = manager.acquire_claude()
            except Ablehnung as exc:
                self.letzter = {"beendet_am": jetzt(), "exit_code": None,
                                "protokoll": "", "fehler": str(exc)}
                return
            self._lease_manager = manager
        try:
            super()._los(grund)
        finally:
            if self.prozess is None:
                self._release_gpu()

    def _warten(self, prozess, datei):
        code = prozess.wait()
        with self.sperre:
            self.prozess, self.gestartet_am = None, None
            self.letzter = {"beendet_am": jetzt(), "exit_code": code,
                            "protokoll": str(datei),
                            "fehler": "" if code == 0 else f"Claude Code endete mit Code {code}."}
            try:
                if self.nochmal and code == 0:
                    self._los("Neues kam während der letzten Sitzung dazu.")
            finally:
                self.nochmal = False
                if self.prozess is None:
                    self._release_gpu()
