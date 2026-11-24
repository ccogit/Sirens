"""Konservative VRAM-Zuteilung; nur eigene Leases dürfen entladen werden."""
from dataclasses import dataclass
from enum import IntEnum
from threading import RLock
from uuid import uuid4

from .contracts import error, invalid
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
            if len(self._leases) > PROFILES[profile]["max_gpu_workers"]:
                raise error("busy_gpu")
            self._profile = profile
            return profile

    @property
    def leases(self):
        with self._lock:
            return tuple(item[0] for item in self._leases.values())

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
