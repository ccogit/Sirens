import struct
import tempfile
import unittest
from pathlib import Path

from sirens.production.contracts import ContractError, open_pcm_wav, validate_wav
from sirens.production.assets import inspect_wav


def riff_pcm(channels=1, extensible=False, floating=False, frames=3):
    def chunk(name, data):
        return name + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")
    align = channels * 3
    fmt = struct.pack("<HHIIHH", 0xfffe if extensible else (3 if floating else 1),
                      channels, 48000, 48000 * align, align, 24)
    if extensible:
        fmt += struct.pack("<HHI", 22, 24, 4 if channels == 1 else 3)
        fmt += bytes.fromhex(("03" if floating else "01") + "00000000001000800000aa00389b71")
    data = (120000).to_bytes(3, "little", signed=True) * channels * frames
    body = b"WAVE" + chunk(b"fmt ", fmt) + chunk(b"JUNK", b"x") + chunk(b"data", data)
    return b"RIFF" + struct.pack("<I", len(body)) + body


class PCM24Tests(unittest.TestCase):
    def test_formats_and_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.wav"
            for channels in (1, 2):
                for extensible in (False, True):
                    with self.subTest(channels=channels, extensible=extensible):
                        path.write_bytes(riff_pcm(channels, extensible))
                        validate_wav(path, channels=channels, frames=3)
                        with open_pcm_wav(path) as wav:
                            self.assertEqual(wav.getsampwidth(), 3)
                            self.assertEqual(len(wav.readframes(1)), channels * 3)
                            self.assertEqual(len(wav.readframes(9)), channels * 6)
                            self.assertEqual(wav.readframes(1), b"")
                        info = inspect_wav(path)
                        self.assertEqual(info["channels"], channels)
                        self.assertEqual(info["frames"], 3)
                        self.assertEqual(info["measured"]["duration_seconds"], 3 / 48000)

    def test_float_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.wav"
            for extensible in (False, True):
                path.write_bytes(riff_pcm(extensible=extensible, floating=True))
                with self.assertRaisesRegex(ContractError, "float"):
                    validate_wav(path)
            good = riff_pcm(extensible=True)
            for bad in (b"", b"RIFX" + good[4:], good[:-2], good[:12],
                        good[:16] + struct.pack("<I", 9999) + good[20:]):
                path.write_bytes(bad)
                with self.assertRaises(ContractError):
                    validate_wav(path)
