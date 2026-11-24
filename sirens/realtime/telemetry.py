"""GPU-Telemetrie ohne Modellbibliotheken; fehlende Werte sperren GPU-Jobs."""
import csv
import subprocess
from dataclasses import dataclass

MIB = 1024**2
COMMAND = ("nvidia-smi", "--id=0",
           "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
           "--format=csv,noheader,nounits")


@dataclass(frozen=True)
class Telemetry:
    device: str | None = None
    total: int | None = None
    used: int | None = None
    free: int | None = None
    compute: int | None = None
    temperature: int | None = None

    @property
    def available(self):
        return self.device is not None

    def as_dict(self, queue_depth=0, deadline_misses=0, underruns=0):
        # Freier VRAM bleibt intern; v1 kennt nur total und used.
        return dict(available=self.available, device=self.device,
                    vram_total_bytes=self.total, vram_used_bytes=self.used,
                    compute_percent=self.compute, temperature_c=self.temperature,
                    queue_depth=queue_depth, deadline_misses=deadline_misses,
                    underruns=underruns)


def read_gpu(run=subprocess.run):
    try:
        result = run(COMMAND, capture_output=True, text=True, timeout=2, check=True)
        rows = list(csv.reader(result.stdout.splitlines(), skipinitialspace=True))
        if len(rows) != 1 or len(rows[0]) != 6:
            return Telemetry()
        name, total, used, free, compute, temp = rows[0]
        total, used, free, compute, temp = map(int, (total, used, free, compute, temp))
        if (not 0 < len(name.strip()) <= 256 or not 0 < total * MIB <= 2**53-1
                or not 0 <= used <= total or not 0 <= free <= total-used
                or not 0 <= compute <= 100 or not -50 <= temp <= 150):
            return Telemetry()
        return Telemetry(name.strip(), total*MIB, used*MIB, free*MIB, compute, temp)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, csv.Error):
        return Telemetry()


if __name__ == "__main__":
    import json
    snapshot = read_gpu()
    print(json.dumps({**snapshot.as_dict(), "vram_free_bytes": snapshot.free}, ensure_ascii=False))
