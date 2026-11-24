"""WP07 lokaler Engine-Lauf: eigener WAV-Ausschnitt, drei Transformationen."""
import argparse
import array
import datetime
from pathlib import Path
import sys
import time
import wave

from benchmarks import baseline, result
from benchmarks.spikes import common
from benchmarks.spikes.runner import Sampler
from workers.demon.adapter import Adapter, MAX_FRAMES

PROFILES = (("instrumental electronic drums", 0.35, 1),
            ("ambient synth texture", 0.65, 2),
            ("acoustic jazz ensemble", 0.85, 3))


def source(path):
    with wave.open(str(path), "rb") as f:
        if (f.getframerate(), f.getnchannels(), f.getsampwidth()) != (48000, 2, 2):
            raise ValueError("WAV muss 48 kHz, Stereo, PCM16 sein")
        raw = f.readframes(MAX_FRAMES)
    samples = array.array("h", raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) < 48000 * 2:
        raise ValueError("Mindestens eine Sekunde Quellaudio nötig")
    return [x/32768 for x in samples]


def write_audio(path, samples):
    pcm = array.array("h", (max(-32768, min(32767, round(x*32768))) for x in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as f:
        f.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
        f.writeframes(pcm.tobytes())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path)
    p.add_argument("--output", type=Path, help="Neuer lokaler Ergebnisordner außerhalb des Repos")
    p.add_argument("--seconds", type=float, default=1800)
    p.add_argument("--deadline-ms", type=float, help="Nur hypothetische Rechenfrist, kein Playback-Nachweis")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.dry_run:
        print("Dry-Run: drei Profile; kein Modell, keine Ausgabe, Gate nicht_gemessen")
        return 0
    if not args.source or not args.output or not 0 < args.seconds <= 7200 or (
            args.deadline_ms is not None and not 0 < args.deadline_ms):
        p.error("Quelle, neuer Ergebnisordner und positive Dauer/Frist erforderlich")
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output == root or root in output.parents:
        p.error("Ergebnisordner muss außerhalb des Repos liegen")
    samples = source(args.source)
    output.mkdir(parents=True, exist_ok=False)
    a = Adapter()
    warm, failures, played = [], [], set()
    cold = {key: None for key in result.METRICS}
    try:
        start = time.perf_counter()
        with Sampler() as cold_gpu:
            prompt, strength, seed = PROFILES[0]
            a.load(epoch=0, prompt=prompt, strength=strength, seed=seed)
            audio = a.process(samples, epoch=0)
        elapsed = time.perf_counter()-start
        cold = common.summarize([(elapsed, len(audio)/96000)], cold_gpu.proc_peak)
        write_audio(output / "cold.wav", audio)
        started = time.perf_counter()
        n = 0
        with Sampler() as gpu:
            while n < len(PROFILES) or time.perf_counter()-started < args.seconds:
                i = n % len(PROFILES)
                prompt, strength, seed = PROFILES[i]
                t = time.perf_counter()
                try:
                    a.load(epoch=n+1, prompt=prompt, strength=strength, seed=seed)
                    audio = a.process(samples, epoch=n+1)
                    warm.append((time.perf_counter()-t, len(audio)/96000))
                    if i not in played:
                        write_audio(output / ("profil-%d.wav" % i), audio)
                        played.add(i)
                except Exception as exc:
                    failures.append(str(exc))
                    break
                n += 1
        duration = time.perf_counter()-started
    finally:
        a.unload()
    measured = common.summarize(warm, gpu.proc_peak) if warm else {key: None for key in result.METRICS}
    measured["underruns"] = None
    cold["underruns"] = None
    notes = ["Engine-Mikrobenchmark, kein Browser/Playback. Keine Gate-Freigabe.",
             "Drei Profile mit Prompt, Denoise und Seed; Hörurteil offen.",
             "Vollständige Laufzeit: %.3f s; erfolgreiche Ausgaben: %d" % (duration, len(warm)),
             "Fehler: " + str(failures)]
    data = dict(wp="WP07", kandidat="demon", zeitpunkt=datetime.datetime.now().astimezone().isoformat(),
                befehl="python -m benchmarks.demon.messen --source <WAV> --output <neuer Ordner> --seconds %s" % args.seconds,
                gate="nicht_gemessen", modus="unbekannt", rechner=baseline.collect(),
                messwerte={"kalt": cold, "warm": measured}, notizen=notes)
    if args.deadline_ms and warm:
        data["rechenfrist_quote"] = sum(t*1000 <= args.deadline_ms for t, _ in warm)/len(warm)
        notes.append("Rechenfristquote ist ausdrücklich keine rechtzeitige Insert-Quote.")
    result.write(output / "result.json", data)
    (output / "result.md").write_text(result.markdown(data), encoding="utf-8")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
