"""CPU-Mock: deterministischer Gain und Delay, keine KI."""
import math
from collections import deque
from .contracts import invalid, error

CAPABILITY = {"id": "mock", "mock": True, "available": True, "mode": "offline",
              "sample_rates": [48000], "channels": 2, "context_frames": 0,
              "hop_frames": 256, "latency_frames": 0,
              "controls": [{"name": "gain", "min": 0, "max": 2, "default": 1},
                           {"name": "delay_frames", "min": 0, "max": 48000, "default": 0}],
              "vram_peak_bytes": "unknown", "device": "cpu", "license": "repository",
              "model_revision": "mock-v1"}

class MockAdapter:
    def __init__(self):
        self.loaded = False
        self.cancelled = False
        self.buffer = deque()

    def probe(self):
        return {**CAPABILITY, "controls": [dict(c) for c in CAPABILITY["controls"]],
                "sample_rates": list(CAPABILITY["sample_rates"])}

    def load(self, gain=1.0, delay_frames=0):
        if type(gain) not in (int, float) or not 0 <= gain <= 2 or type(delay_frames) is not int or not 0 <= delay_frames <= 48000:
            raise invalid("controls")
        self.gain = gain
        self.delay_frames = delay_frames
        self.buffer = deque([0.0] * (2 * delay_frames))
        self.loaded = True
        self.cancelled = False
        return {**self.probe(), "latency_frames": delay_frames}

    def warmup(self):
        self._check()

    def _check(self):
        if not self.loaded or self.cancelled:
            raise error("unavailable")

    def process(self, samples):
        self._check()
        if len(samples) % 2 or any(type(s) not in (float, int) or not -1 <= s <= 1 or not math.isfinite(s) for s in samples):
            raise invalid("samples")
        result = []
        for sample in samples:
            self.buffer.append(sample * self.gain)
            result.append(self.buffer.popleft())
        return result

    def cancel(self):
        self.cancelled = True

    def unload(self):
        self.buffer.clear()
        self.loaded = False

    def health(self):
        return {"mock": True, "loaded": self.loaded, "cancelled": self.cancelled}
