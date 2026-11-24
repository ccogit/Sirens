"""K03 offline instrument rendering; main process uses only stdlib."""
from __future__ import annotations

import hashlib
import json
import wave
from fractions import Fraction
from pathlib import Path

SAMPLE_RATE = 48000
PPQ = 960


def tick_to_sample(tick, bpm):
    return round(Fraction(tick * SAMPLE_RATE * 60, PPQ) / Fraction(str(bpm)))


def expected_frames(plan):
    return round((Fraction(plan["total_bars"] * 240, 1) / Fraction(str(plan["bpm"]))
                  + Fraction(str(plan["tail_seconds"]))) * SAMPLE_RATE)


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cache_key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def read_pcm(path):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        frames = wav.getnframes()
        if wav.getframerate() != SAMPLE_RATE or wav.getsampwidth() != 3 or channels not in (1, 2):
            raise ValueError("Expected 48 kHz mono/stereo PCM24")
        data = wav.readframes(frames)
    if len(data) != frames * channels * 3:
        raise ValueError("Truncated WAV")
    return channels, data


def write_pcm(path, channels, data):
    if channels not in (1, 2) or len(data) % (channels * 3):
        raise ValueError("Invalid PCM24 data")
    path = Path(path)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(3)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data)
