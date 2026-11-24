"""Modellunabhängiger Companion-Lebenszyklus; keine Downloads oder Imports von ML."""
import math
import struct
import threading

RATE = 48000
HOP = 1920
MAX_BYTES = 1024 * 1024


class Companion:
    """Backend-Vertrag: embed(pcm), generate(conditioning, state), close()."""

    def __init__(self, factory):
        self.factory = factory
        self.lock = threading.RLock()
        self.backend = None
        self.state = None
        self.conditioning = None
        self.epoch = 0
        self.gain = 1.0
        self.bypass = False
        self.active = False
        self.busy = False

    def load(self, *, gain=1.0, bypass=0):
        if (type(gain) not in (int, float) or not math.isfinite(gain)
                or not 0 <= gain <= 2 or type(bypass) not in (int, float)
                or bypass not in (0, 1)):
            raise ValueError("Ungültiger Regler")
        with self.lock:
            if self.busy:
                raise RuntimeError("Modell beschäftigt")
            self.unload()
            self.backend = self.factory()
            self.active = True
            self.gain = gain
            self.bypass = bool(bypass)

    def process(self, pcm=b""):
        if not isinstance(pcm, bytes) or len(pcm) > MAX_BYTES or len(pcm) % 8:
            raise ValueError("Ungültige Stereo-Referenz")
        if pcm and any(not math.isfinite(x[0]) or abs(x[0]) > 1
                       for x in struct.iter_unpack("<f", pcm)):
            raise ValueError("Ungültige Referenzsamples")
        with self.lock:
            if not self.active or self.busy:
                raise RuntimeError("Companion nicht bereit")
            if self.bypass:
                return bytes(HOP * 8)
            self.busy = True
            backend, epoch = self.backend, self.epoch
            conditioning, state = self.conditioning, self.state
        try:
            if pcm or conditioning is None:
                conditioning = backend.embed(pcm or bytes(HOP * 8))
            raw, state = backend.generate(conditioning, state)
            if not isinstance(raw, bytes) or len(raw) != HOP * 8:
                raise ValueError("Ungültige Modellausgabe")
            samples = [x[0] for x in struct.iter_unpack("<f", raw)]
            if any(not math.isfinite(x) for x in samples):
                raise ValueError("Nichtendliche Modellausgabe")
            with self.lock:
                if not self.active or epoch != self.epoch:
                    raise RuntimeError("Companion gestoppt")
                self.conditioning, self.state = conditioning, state
                return struct.pack("<" + "f" * len(samples),
                                   *(max(-1, min(1, x * self.gain)) for x in samples))
        finally:
            with self.lock:
                self.busy = False

    def cancel(self):
        with self.lock:
            self.epoch += 1
            self.active = False
            self.state = self.conditioning = None

    def unload(self):
        with self.lock:
            self.cancel()
            if self.busy:
                raise RuntimeError("Inferenz läuft; Supervisor muss Prozess stoppen")
            backend, self.backend = self.backend, None
            if backend is not None:
                backend.close()

    def health(self):
        with self.lock:
            return {"loaded": self.active, "busy": self.busy}
