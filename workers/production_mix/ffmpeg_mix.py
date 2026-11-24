"""Offline PCM24 mixing using existing ffmpeg filters, no audio library imports."""
import json
import math
import re
import subprocess
import wave
from pathlib import Path

RATE = 48000


def db(value):
    return 10 ** (value / 20)


def run(exe, args):
    result = subprocess.run([exe, "-hide_banner", "-nostdin", "-nostats",
                             "-threads", "1", *map(str, args)],
                            capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise RuntimeError("ffmpeg failed: " + result.stderr[-2000:])
    return result.stderr


def finite(value):
    number = float(value)
    return number if math.isfinite(number) else None


def loudness(exe, path):
    log = run(exe, ["-i", path, "-af",
                    "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                    "-f", "null", "-"])
    m = json.loads(re.findall(r"\{[^{}]*\}", log)[-1])
    return dict(lufs=finite(m["input_i"]), true_peak_dbtp=finite(m["input_tp"]),
                lra=finite(m["input_lra"]))


def rms(exe, path, filters):
    log = run(exe, ["-i", path, "-af", filters +
                    ",aformat=sample_fmts=flt,astats=metadata=0",
                    "-f", "null", "-"])
    overall = log.rsplit("Overall", 1)[-1]
    match = re.search(r"RMS level dB:\s*(\S+)", overall)
    if not match:
        raise RuntimeError("ffmpeg astats RMS missing")
    return finite(match.group(1))


def measure(exe, path):
    result = loudness(exe, path)
    result["bands_dbfs"] = {
        "sub_20_120": rms(exe, path, "highpass=f=20,lowpass=f=120"),
        "low_120_500": rms(exe, path, "highpass=f=120,lowpass=f=500"),
        "mid_500_4000": rms(exe, path, "highpass=f=500,lowpass=f=4000"),
        "high_4000_20000": rms(exe, path, "highpass=f=4000,lowpass=f=20000"),
    }
    mid = rms(exe, path, "lowpass=f=80,pan=mono|c0=0.5*c0+0.5*c1")
    side = rms(exe, path, "lowpass=f=80,pan=mono|c0=0.5*c0-0.5*c1")
    result["sub_side_mid_db"] = side - mid if side is not None and mid is not None else None
    result["sub_mid_dbfs"] = mid
    result["sub_side_dbfs"] = side
    count = 0
    with wave.open(str(path), "rb") as wav:
        while chunk := wav.readframes(65536):
            count += sum(chunk[i:i+3] in (b"\xff\xff\x7f", b"\x00\x00\x80")
                         for i in range(0, len(chunk), 3))
    result["clipped_samples"] = count
    return result


def encode(exe, source, destination, frames, gain=0):
    run(exe, ["-i", source, "-af", f"volume={gain:.8f}dB,apad,atrim=end_sample={frames}",
              "-ar", RATE, "-ac", 2, "-c:a", "pcm_s24le", "-n", destination])


def sum_filter(labels, output):
    if len(labels) == 1:
        return f"[{labels[0]}]anull[{output}]"
    return "".join(f"[{name}]" for name in labels) + (
        f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0[{output}]")


def render_graph(exe, paths, settings, frames, destination, *, dry=False):
    graph, labels = [], []
    kick = next((i for i, s in enumerate(settings) if s["kick"]), None)
    bass = [i for i, s in enumerate(settings) if s["sub"] and i != kick]
    for i, s in enumerate(settings):
        label = f"track{i}"
        pan = 0 if dry or s["sub"] or s["kick"] else s["pan"]
        left = math.sqrt(1 - max(0, pan))
        right = math.sqrt(1 + min(0, pan))
        filters = ["aformat=sample_fmts=fltp:channel_layouts=stereo",
                   f"pan=stereo|c0={left:.8f}*c0|c1={right:.8f}*c1"]
        if not dry:
            filters += [f"volume={s['gain_db']}dB", f"highpass=f={s['highpass_hz']}"]
            if s["eq_db"]:
                filters += [f"equalizer=f={s['eq_hz']}:t=q:w=1:g={s['eq_db']}"]
            if s["sub"] or s["kick"]:
                filters += ["pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"]
        graph.append(f"[{i}:a]" + ",".join(filters) + f"[{label}]")
    if not dry and kick is not None and bass:
        graph.append(f"[track{kick}]asplit={len(bass)+1}[kickmain]" +
                     "".join(f"[key{i}]" for i in bass))
    for i, s in enumerate(settings):
        label = f"track{i}"
        if not dry and kick is not None and bass:
            if i == kick:
                label = "kickmain"
            elif i in bass:
                graph.append(f"[{label}][key{i}]sidechaincompress=threshold=0.06:"
                             f"ratio=2:attack=5:release=110[duck{i}]")
                label = f"duck{i}"
        # Separate wet returns: delayed taps, never a second dry signal.
        taps = [] if dry else [(17, s["reverb_send"]*.45),
                               (37, s["reverb_send"]*.30),
                               (71, s["reverb_send"]*.20),
                               (240, s["delay_send"]*.7),
                               (480, s["delay_send"]*.3)]
        taps = [(delay, gain) for delay, gain in taps if gain > 0]
        if taps:
            graph.append(f"[{label}]asplit={len(taps)+1}[main{i}]" +
                         "".join(f"[tap{i}_{j}]" for j in range(len(taps))))
            label = f"main{i}"
            for j, (delay, gain) in enumerate(taps):
                wet = f"wet{i}_{j}"
                graph.append(f"[tap{i}_{j}]highpass=f=250,lowpass=f=6000,"
                             f"adelay={delay}|{delay},volume={gain:.8f}[{wet}]")
                labels.append(wet)
        labels.append(label)
    graph.append(sum_filter(labels, "summed"))
    if not dry:
        graph += ["[summed]acrossover=split=120:order=4th[low][high]",
                  "[low]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1[mono]",
                  sum_filter(["mono", "high"], "combined")]
    else:
        graph.append("[summed]anull[combined]")
    fade = min(240, frames // 4)
    graph.append(f"[combined]apad,atrim=end_sample={frames},"
                 f"afade=t=in:ss=0:ns={fade},"
                 f"afade=t=out:ss={frames-fade}:ns={fade}[out]")
    args = []
    for path in paths:
        args.extend(["-i", path])
    run(exe, [*args, "-filter_complex_threads", 1, "-filter_complex", ";".join(graph),
              "-map", "[out]", "-ar", RATE, "-ac", 2, "-c:a", "pcm_f32le",
              "-n", destination])
