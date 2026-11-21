"""Tests für Rhythmus, Energieverlauf, Phrasen-Cues und Übergangswahl."""
from array import array
import math
import unittest

from sirens.beat import _bar0, _merkmale, beatgrid
from sirens.dramaturgie import analyse_abschnitte, paar_uebergang


class TaktErkennung(unittest.TestCase):
    def test_120_bpm_mit_downbeat(self):
        impulse = [0.0] * 9000
        for i in range(18 * 10):
            index = 5 + i * 50
            if index < len(impulse):
                impulse[index] = 1.0 if i % 4 == 0 else 0.62
        grid = beatgrid(impulse)
        self.assertAlmostEqual(grid["bpm"], 120, delta=2)
        self.assertAlmostEqual(grid["beat0"], 0.05, delta=0.06)
        bar0 = _bar0(impulse, grid["beat0"], grid["bpm"])
        self.assertAlmostEqual(bar0, 0.05, delta=0.07)

    def test_kein_beat(self):
        with self.assertRaises(ValueError):
            beatgrid([0.0] * 5000)
        with self.assertRaises(ValueError):
            beatgrid([1.0] * 300)

    def test_pcm_merkmale(self):
        samples = array("h")
        for k in range(4000 * 12):
            amp = 16000 if k % 2000 < 80 else 0
            samples.append(round(amp * math.sin(k * 0.15)))
        onset, energy, bright = _merkmale(samples.tobytes())
        self.assertEqual((len(onset),len(energy),len(bright)), (1200,1200,1200))
        self.assertGreater(max(onset),100)
        self.assertGreater(max(energy),100)
        self.assertTrue(all(v >= 0 for v in bright))


class Dramaturgie(unittest.TestCase):
    @staticmethod
    def kurve():
        def energy(t):
            if t < 16: return 0.15
            if t < 44: return 0.15 + 0.7*(t-16)/28
            if t < 80: return 0.83
            if t < 100: return 0.22
            if t < 146: return 0.75
            if t < 162: return 0.75 - 0.55*(t-146)/16
            return 0.17
        e = [energy(k/100) for k in range(20000)]
        trans = [0.05 if k % 50 < 4 else 0.005 for k in range(20000)]
        return analyse_abschnitte(e,trans,[0.3]*len(e),120,0,200)

    def test_energiestruktur_und_phrasen(self):
        result=self.kurve()
        self.assertGreater(len(result["timeline"]),10)
        self.assertGreater(len(result["cues_in"]),0)
        self.assertGreater(len(result["cues_out"]),0)
        self.assertTrue(all(int(c["zeit"]) % 8 == 0 for c in result["cues_out"]))
        self.assertTrue(any("Break" in row["phase"] or "Aufbau" in row["phase"]
                            for row in result["timeline"]))
        self.assertTrue(all(0 <= row["energie"] <= 1 for row in result["timeline"]))

    def test_dramaturgisches_cue_paar(self):
        kurve=self.kurve()
        a={"bpm":120,"duration":200,"confidence":0.75,**kurve}
        b={"bpm":124,"duration":200,"confidence":0.84,**kurve}
        cue=paar_uebergang(a,b,8,jetzt=20)
        self.assertIsNotNone(cue)
        self.assertGreater(cue["start_a"],20)
        self.assertLess(cue["start_a"]+cue["seconds"],200)
        self.assertLess(abs(cue["rate_b"]-1),0.1)
        self.assertIn("ausgang",cue)
        self.assertIn("eingang",cue)
        self.assertIsNone(paar_uebergang(a,{**b,"bpm":220},8,20))


if __name__ == "__main__":
    unittest.main()
