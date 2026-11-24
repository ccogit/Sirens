"""Deterministische synthetische Signale; keine Dateien als Eingabe erforderlich."""
import argparse
import json
import math
import wave
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

SIGNALS = ("impuls", "sinus440", "sinus1000", "stereo", "click120", "click140", "click150", "stille")


@dataclass
class Fixture:
    samples: list[float]  # interleaved: Frame 0 Kanal 0, Frame 0 Kanal 1, ...
    truth: dict


def generate(signal: str, rate: int = 48000, duration: float = 4.0,
             channels: int = 1) -> Fixture:
    if signal not in SIGNALS:
        raise ValueError(f"Unbekanntes Signal: {signal}")
    if type(rate) is not int or rate <= 0 or type(channels) is not int or channels not in (1, 2):
        raise ValueError("Rate muss positiv sein; Kanäle: 1 oder 2")
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Dauer muss positiv und endlich sein")
    frames = round(Fraction(str(duration)) * rate)
    if frames < 1:
        raise ValueError("Dauer ergibt keinen Frame")
    if signal == "stereo" and channels != 2:
        raise ValueError("Stereo-Sinus benötigt zwei Kanäle")
    truth = {"signal": signal, "rate": rate, "channels": channels, "frames": frames}
    samples = [0.0] * (frames * channels)
    if signal == "impuls":
        samples[0] = 1.0
        truth.update(impulse_frame=0, impulse_channel=0)
    elif signal.startswith("sinus") or signal == "stereo":
        freqs = [440, 1000] if signal == "stereo" else [int(signal[5:])] * channels
        if max(freqs) * 2 >= rate:
            raise ValueError("Rate muss über der doppelten Sinusfrequenz liegen")
        truth.update(frequencies_hz=freqs, amplitude=0.5)
        samples = [0.5 * math.sin(math.tau * f * frame / rate)
                   for frame in range(frames) for f in freqs]
    elif signal.startswith("click"):
        bpm = int(signal[5:])
        step = Fraction(rate * 60, bpm)
        if step < 1:
            raise ValueError("Rate zu niedrig für die Klickspur")
        beats = []
        i = 0
        while (frame := round(i * step)) < frames:
            beats.append(frame)
            amp = 1.0 if i % 4 == 0 else 0.5
            for channel in range(channels):
                samples[frame * channels + channel] = amp
            i += 1
        truth.update(bpm=bpm, beat_frames=beats, downbeat_frames=beats[::4],
                     meter=[4, 4], downbeat_amplitude=1.0, beat_amplitude=0.5)
    return Fixture(samples, truth)


def write_wav(path: Path, fixture: Fixture) -> None:
    """PCM signed 24-bit, little endian; +1 wird auf den größten Integer begrenzt."""
    data = bytearray()
    for sample in fixture.samples:
        if not math.isfinite(sample) or abs(sample) > 1:
            raise ValueError("Abtastwert außerhalb [-1, 1]")
        value = min(8388607, round(sample * 8388608))
        data.extend(value.to_bytes(3, "little", signed=True))
    if len(fixture.samples) != fixture.truth["frames"] * fixture.truth["channels"]:
        raise ValueError("Anzahl Abtastwerte passt nicht zur Framezahl")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(fixture.truth["channels"])
        wav.setsampwidth(3)
        wav.setframerate(fixture.truth["rate"])
        wav.writeframes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--rate", type=int, default=48000)
    parser.add_argument("--duration", type=float, default=4.0, help="Sekunden")
    parser.add_argument("--channels", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for signal in SIGNALS:
        fixture = generate(signal, args.rate, args.duration, 2 if signal == "stereo" else args.channels)
        write_wav(args.out / f"{signal}.wav", fixture)
        (args.out / f"{signal}.json").write_text(json.dumps(fixture.truth, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
