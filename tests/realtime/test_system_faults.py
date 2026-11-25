"""WP19: ergänzende synthetische Protokoll-/Störfallregression."""
import math
import struct
import unittest

from sirens.contracts import Ablehnung
from sirens.realtime import pcm
from sirens.realtime.mock import MockAdapter


class SystemFaults(unittest.TestCase):
    def test_generated_pcm_mock_gain_and_seek_epoch(self):
        adapter = MockAdapter()
        adapter.load(gain=.5)
        for epoch, start, count, rate in [(0, 0, 256, 48000), (1, 8192, 2048, 44100)]:
            # Stereo mit verschiedenen Frequenzen, keine Musikdatei.
            samples = [v for i in range(start, start + count)
                       for v in (.5 * math.sin(2 * math.pi * 440 * i / rate),
                                 .25 * math.sin(2 * math.pi * 880 * i / rate))]
            raw = struct.pack("<" + "f" * len(samples), *samples)
            header = dict(protocol_version=1, stream_id=1, epoch=epoch, seq=0,
                          start_frame=start, nframes=count, channels=2, flags=0, sample_rate=rate)
            received, payload = pcm.unpack(pcm.pack(header, raw))
            self.assertEqual(received, dict(header, seek=False))
            decoded = struct.unpack("<" + "f" * len(samples), payload)
            self.assertEqual(adapter.process(decoded), [x * .5 for x in decoded])
            with self.assertRaises(Ablehnung):
                pcm.unpack(pcm.pack(header, raw)[:-1])
        adapter.cancel()
        with self.assertRaises(Ablehnung):
            adapter.process([0., 0.])
        adapter.unload()
        self.assertFalse(adapter.health()["loaded"])
