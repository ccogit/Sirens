"""WP15: expliziter Offline-Langlauf mit lokaler synthetischer Referenz."""
import argparse
import math
from pathlib import Path
import struct
import time
import uuid
import wave

from benchmarks import baseline, result
from benchmarks.spikes import common, runner
from workers.magenta.adapter import Companion, RATE, HOP


def reference(freq):
    # Zwei Sekunden Stereo, unterhalb der IPC-Grenze; keine Kundendaten.
    return b"".join(struct.pack("<ff", x, x) for x in
                    (.15 * math.sin(2 * math.pi * freq * n / RATE) for n in range(2 * RATE)))


def run(factory, directory, seconds=600):
    if type(seconds) is not int or not 1 <= seconds <= 600:
        raise ValueError("Dauer muss 1–600 Sekunden sein")
    directory.mkdir(parents=True, exist_ok=False)
    adapter = Companion(factory)
    refs = [reference(220), reference(330)]
    samples = []
    count = seconds * RATE // HOP
    start = time.perf_counter()
    try:
        with runner.Sampler() as cold_gpu:
            _, load = common.timed(adapter.load)
            first, first_s = common.timed(lambda: adapter.process(refs[0]))
        cold = common.summarize([(load + first_s, HOP / RATE)], cold_gpu.proc_peak)
        cold.update(load_ms=load * 1000, first_ms=first_s * 1000,
                    gpu_total_sampled_peak_mib=cold_gpu.gpu_peak)
        with runner.Sampler() as warm_gpu, wave.open(str(directory / "companion.wav"), "wb") as wav:
            wav.setparams((2, 2, RATE, 0, "NONE", "not compressed"))

            def write(raw):
                wav.writeframesraw(b"".join(struct.pack("<h", round(max(-1, min(1, v[0])) * 32767))
                                             for v in struct.iter_unpack("<f", raw)))
            write(first)
            for i in range(1, count):
                ref = refs[1] if i == count // 2 else b""
                raw, elapsed = common.timed(lambda: adapter.process(ref))
                samples.append((elapsed, HOP / RATE))
                write(raw)
        warm = common.summarize(samples, warm_gpu.proc_peak)
        warm["gpu_total_sampled_peak_mib"] = warm_gpu.gpu_peak
        adapter.cancel()
        try:
            adapter.process()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Stop fehlgeschlagen")
        data = common.make_result("magenta", "offline", baseline.collect(), cold, warm,
                                  "python -m benchmarks.companion.messen --echt --seconds " + str(seconds),
                                  ["Offline-Langlauf; kein Nachweis für Beatbindung oder Echtzeit.",
                                   "Stilreferenz nach halber Dauer gewechselt; Hörurteil separat.",
                                   "Kein Browser: Underruns, Audio-End-to-End-Latenz nicht gemessen.",
                                   "VRAM per nvidia-smi abgetastet; Prozesswerte in WSL ggf. null."])
        data["wp"] = "WP15"
        data["profil"] = dict(audio_seconds=seconds, blocks=count, wall_seconds=time.perf_counter()-start,
                              rate=RATE, channels=2, stop_ok=True)
        result.write(directory / "result.json", data)
        (directory / "result.md").write_text(result.markdown(data), encoding="utf-8")
        return data
    finally:
        adapter.unload()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--echt", action="store_true", help="Bewusster lokaler Modelllauf")
    p.add_argument("--seconds", type=int, default=600)
    args = p.parse_args(argv)
    if not args.echt:
        print("Kein Modelllauf ohne --echt; Gate nicht_gemessen")
        return 0
    if not 1 <= args.seconds <= 600:
        p.error("Dauer muss 1–600 Sekunden sein")
    from workers.magenta.backend import MagentaBackend
    directory = Path(__file__).resolve().parents[1] / "results" / "local" / ("companion-" + uuid.uuid4().hex)
    run(MagentaBackend, directory, args.seconds)
    print("Ergebnis:", directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
