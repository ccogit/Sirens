"""Kick-Tausch: die Kick eines Songs durch die eines anderen ersetzen. Eigener Prozess; braucht numpy, scipy, soundfile.

Aufruf: python kick_dsp.py <drums_ziel> <rest_ziel> <drums_spender> <ausgabe.wav>      (Bericht als JSON auf stdout)

Es wird nicht nur der Takt getroffen, sondern die Entwicklung des Zielsongs übernommen:
- Jeder Schlag sitzt genau dort, wo die Kick des Zielsongs saß (Groove, Fills, Pausen und Breaks bleiben).
- Jeder Schlag ist so stark wie der ersetzte (leises Intro, lauter Refrain, Steigerungen bleiben).
- Der Spender liefert bis zu drei Kick-Muster (leise, mittel, laut); leise Stellen bekommen das leise Muster.
- Die fremde Kick wird auf den Grundton der bisherigen gestimmt, damit sie zum Bass des Zielsongs passt.
Der Bass bleibt unberührt, weil nur der Tiefton der Schlagzeugspur entfernt wird.
"""
import json
import sys
from fractions import Fraction

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

GRENZE = 150.0      # Hz; darunter liegt in der Schlagzeugspur fast nur die Kick
RASTER = 400        # Hüllkurve mit 400 Werten je Sekunde
VOR = 0.004         # s; so viel vor dem Einsatz beginnt ein Muster (Anschlag bleibt ganz)


def laden(pfad, rate=None):
    daten, sr = sf.read(pfad, dtype="float32", always_2d=True)
    daten = np.repeat(daten, 2, axis=1) if daten.shape[1] == 1 else daten[:, :2]
    if rate and sr != rate:
        teiler = np.gcd(int(sr), int(rate))
        daten, sr = signal.resample_poly(daten, rate // teiler, sr // teiler, axis=0).astype(np.float32), rate
    return daten, sr


def tief(x, sr, grenze=GRENZE):
    return signal.sosfiltfilt(signal.butter(4, grenze, "lowpass", fs=sr, output="sos"), x, axis=0).astype(np.float32)


def huellkurve(mono_tief, sr):
    schritt = max(1, sr // RASTER)
    n = len(mono_tief) // schritt
    if not n:
        return np.zeros(0, np.float32), schritt
    h = np.sqrt(np.mean(mono_tief[: n * schritt].reshape(n, schritt) ** 2, axis=1))
    return np.convolve(h, np.ones(4) / 4, mode="same"), schritt


def treffer(drums, sr):
    """Kick-Schläge einer Schlagzeugspur: Einsätze (Samples) und Stärken. Die Schwelle läuft mit, damit leise Passagen ihre Schläge behalten."""
    h, schritt = huellkurve(tief(drums.mean(axis=1), sr), sr)
    if not len(h) or h.max() < 1e-4:
        return np.zeros(0, int), np.zeros(0)
    schwelle = np.maximum(0.3 * ndimage.maximum_filter1d(h, 4 * RASTER), 0.06 * np.percentile(h, 99))
    spitzen, _ = signal.find_peaks(h, height=schwelle, distance=int(0.09 * RASTER), prominence=0.5 * schwelle)
    einsaetze = []
    for s in spitzen:  # vom Gipfel zurück bis dorthin, wo der Schlag beginnt
        i = s
        while i > max(0, s - int(0.04 * RASTER)) and h[i - 1] > 0.15 * h[s]:
            i -= 1
        einsaetze.append(i * schritt)
    return np.array(einsaetze, int), h[spitzen]


def staerke_von(stueck, sr):
    h, _ = huellkurve(tief(stueck.mean(axis=1), sr), sr)
    return float(h.max()) if len(h) else 0.0


def muster(drums, sr, ein, staerke, klassen):
    """Kick-Muster aus den frei stehenden Schlägen: je Stärkeklasse der Median über ausgerichtete Schläge (das drängt Hi-Hats und Snare heraus)."""
    vor = int(VOR * sr)
    abstand = np.diff(np.append(ein, len(drums)))
    laenge = int(min(0.45, 0.95 * float(np.median(abstand)) / sr) * sr) if len(ein) > 1 else int(0.3 * sr)
    frei = [i for i in range(len(ein)) if abstand[i] >= 0.6 * laenge and ein[i] >= vor and ein[i] + laenge <= len(drums)]
    if not frei:
        return []
    frei.sort(key=lambda i: staerke[i])
    anzahl = klassen if len(frei) >= 4 * klassen else 1
    ergebnis = []
    for gruppe in np.array_split(np.array(frei), anzahl):
        stuecke = np.stack([drums[ein[i] - vor: ein[i] + laenge] for i in gruppe[-24:]])  # höchstens 24 Schläge je Klasse
        bezug = tief(stuecke[len(stuecke) // 2].mean(axis=1), sr)
        spanne = int(0.002 * sr)
        for k in range(len(stuecke)):  # Schläge auf wenige Samples genau übereinanderlegen
            eigen = tief(stuecke[k].mean(axis=1), sr)
            versatz = max(range(-spanne, spanne + 1), key=lambda v: float(np.dot(np.roll(eigen, v), bezug)))
            stuecke[k] = np.roll(stuecke[k], versatz, axis=0)
        m = np.median(stuecke, axis=0).astype(np.float32)
        unten = tief(m, sr, 200.0)
        zeit = np.arange(len(m)) / sr
        m = unten + (m - unten) * np.exp(-zeit / 0.03)[:, None]      # über 200 Hz nur der Anschlag, kein Becken-Ausklang
        m[-int(0.015 * sr):] *= np.linspace(1, 0, int(0.015 * sr))[:, None]
        m[: int(0.001 * sr)] *= np.linspace(0, 1, int(0.001 * sr))[:, None]
        ergebnis.append({"klang": m, "staerke": staerke_von(m, sr)})
    return [m for m in ergebnis if m["staerke"] > 0]


def grundton(klang, sr):
    """Grundton einer Kick (35–120 Hz) aus ihrem Körper nach dem Anschlag; 0, wenn keiner deutlich ist."""
    stueck = tief(klang.mean(axis=1), sr)[int(0.02 * sr): int(0.22 * sr)]
    if len(stueck) < int(0.08 * sr):
        return 0.0
    spektrum = np.abs(np.fft.rfft(stueck * np.hanning(len(stueck)), 1 << 16))
    frequenz = np.fft.rfftfreq(1 << 16, 1 / sr)
    band = (frequenz >= 35) & (frequenz <= 120)
    return float(frequenz[band][np.argmax(spektrum[band])]) if spektrum[band].max() > 0 else 0.0


def stimmen(klang, verhaeltnis):
    """Muster um `verhaeltnis` höher (>1) oder tiefer stimmen; dabei wird es entsprechend kürzer oder länger."""
    bruch = Fraction(1 / verhaeltnis).limit_denominator(200)
    return signal.resample_poly(klang, bruch.numerator, bruch.denominator, axis=0).astype(np.float32)


def begrenzen(x, sr, decke=0.98):
    """Spitzen abfangen, ohne den ganzen Song leiser zu machen: kurz vor und nach einer Spitze sinkt der Pegel weich ab."""
    spitze = np.abs(x).max(axis=1)
    if spitze.max() <= decke:
        return x
    noetig = np.minimum(1.0, decke / np.maximum(spitze, 1e-9))
    pegel = ndimage.minimum_filter1d(noetig, int(0.03 * sr))       # 15 ms davor und danach gehalten
    pegel = ndimage.uniform_filter1d(pegel, int(0.01 * sr))        # weiche Kanten, innerhalb der gehaltenen Strecke
    return x * pegel[:, None].astype(np.float32)


def tauschen(drums_ziel, rest_ziel, drums_spender, sr):
    ein_z, st_z = treffer(drums_ziel, sr)
    ein_s, st_s = treffer(drums_spender, sr)
    if not len(ein_z):
        raise ValueError("Im Zielsong wurde keine Kick gefunden.")
    if not len(ein_s):
        raise ValueError("Im Spendersong wurde keine Kick gefunden.")
    spender = muster(drums_spender, sr, ein_s, st_s, 3)
    eigene = muster(drums_ziel, sr, ein_z, st_z, 1)
    if not spender:
        raise ValueError("Im Spendersong steht keine Kick frei genug, um sie herauszulösen.")

    # Stimmen: Grundton der fremden Kick auf den der bisherigen, höchstens fünf Halbtöne
    ton_z = grundton(eigene[0]["klang"], sr) if eigene else 0.0
    ton_s = grundton(spender[-1]["klang"], sr)
    halbtoene = 12 * np.log2(ton_z / ton_s) if ton_z and ton_s else 0.0
    if 0.3 <= abs(halbtoene) <= 5:
        for m in spender:
            m["klang"] = stimmen(m["klang"], ton_z / ton_s)
            m["staerke"] = staerke_von(m["klang"], sr)
    else:
        halbtoene = 0.0

    # Alte Kick heraus: Tiefton der Schlagzeugspur, nur dort, wo ein Schlag klingt
    vor = int(VOR * sr)
    naechster = np.append(ein_z[1:], len(drums_ziel))
    maske = np.zeros(len(drums_ziel), np.float32)
    for a, n in zip(ein_z, naechster):
        maske[max(0, a - 2 * vor): min(n, a + int(0.5 * sr))] = 1
    maske = np.convolve(maske, np.hanning(2 * vor) / np.hanning(2 * vor).sum(), mode="same")
    aus = rest_ziel + drums_ziel - tief(drums_ziel, sr) * maske[:, None]

    # Neue Kick hinein: Ort und Stärke vom Zielsong, Klang vom Spender (Muster mit der ähnlichsten relativen Stärke)
    mitte_z = float(np.median(st_z))
    mitte_s = float(np.median([m["staerke"] for m in spender]))
    gewaehlt = []
    for a, n, s in zip(ein_z, naechster, st_z):
        k = min(range(len(spender)), key=lambda j: abs(np.log((s / mitte_z) / (spender[j]["staerke"] / mitte_s))))
        gewaehlt.append(k)
        klang = spender[k]["klang"] * float(np.clip(s / spender[k]["staerke"], 0.15, 3.0))
        start = max(0, a - vor)
        ende = min(start + len(klang), n - vor if n < len(aus) else len(aus), len(aus))
        if ende <= start:
            continue
        stueck = klang[: ende - start].copy()
        if len(stueck) < len(klang):  # der nächste Schlag kommt: ausblenden statt übereinanderlegen
            blende = min(len(stueck), int(0.006 * sr))
            stueck[-blende:] *= np.linspace(1, 0, blende)[:, None]
        aus[start:ende] += stueck
    aus = begrenzen(aus, sr)

    abstand = np.diff(ein_z) / sr
    takt = float(np.median(abstand)) if len(abstand) else 0.0
    pausen = [[round(float(ein_z[i] / sr), 1), round(float(ein_z[i + 1] / sr), 1)]
              for i in range(len(abstand)) if abstand[i] > max(4 * takt, 2.0)]
    bericht = {"treffer_ziel": int(len(ein_z)), "treffer_spender": int(len(ein_s)), "muster": len(spender),
               "muster_genutzt": [int(gewaehlt.count(k)) for k in range(len(spender))],
               "grundton_ziel": round(ton_z, 1), "grundton_spender": round(ton_s, 1), "halbtoene": round(float(halbtoene), 1),
               "pausen": pausen, "dauer": round(len(aus) / sr, 1)}
    return aus.astype(np.float32), bericht


def main(argv):
    if len(argv) != 5:
        print(json.dumps({"error": "Aufruf: kick_dsp.py <drums_ziel> <rest_ziel> <drums_spender> <ausgabe.wav>"}))
        return 2
    try:
        drums_ziel, sr = laden(argv[1])
        rest_ziel, _ = laden(argv[2], sr)
        drums_spender, _ = laden(argv[3], sr)
        n = min(len(drums_ziel), len(rest_ziel))
        aus, bericht = tauschen(drums_ziel[:n], rest_ziel[:n], drums_spender, sr)
        sf.write(argv[4], aus, sr, subtype="PCM_16")
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(bericht, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
