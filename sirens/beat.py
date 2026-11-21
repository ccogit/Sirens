"""Leichtgewichtige Beatgrid-Schätzung für den lokalen Auto-DJ.

Maximal 360 Sekunden werden mit ffmpeg auf 4 kHz/mono heruntergerechnet.
Kein ML-Modell, keine Datenbank und keine Änderung an Songdateien.
"""
from array import array
import math
import os
import subprocess
import sys
import threading
from pathlib import Path

from .contracts import Ablehnung, safe_audio_path
from .dramaturgie import analyse_abschnitte

HOP = 40                   # 10 ms bei 4 kHz
HZ = 100
MAX_SECONDS = 360
BEAT_WINDOW = 90


def beatgrid(onset, hz=HZ):
    """Aus einem Onset-Verlauf BPM und Beatphase gewinnen (4/4-Bar-Annahme)."""
    if len(onset) < 8 * hz:
        raise ValueError("Zu wenig Musik für die Tempoerkennung.")
    signal = [max(0.0, float(v)) for v in onset]
    peak = max(signal)
    if peak < 1e-6:
        raise ValueError("Keine deutlichen rhythmischen Impulse gefunden.")
    signal = [s / peak if s / peak >= 0.07 else 0.0 for s in signal]
    e = sum(v * v for v in signal)
    if e < 0.1:
        raise ValueError("Kein auswertbarer Rhythmus vorhanden.")
    kandidaten = []
    for lag in range(round(60 * hz / 185), round(60 * hz / 65) + 1):
        bpm = 60 * hz / lag
        korrelation = sum(a * b for a, b in zip(signal[:-lag], signal[lag:]))
        # Bei Halb-/Doppeltempo ist das Ergebnis mehrdeutig. Sanfte DJ-Priorisierung.
        bevorzugung = max(0.5, 1 - 0.000035 * (bpm - 116) ** 2)
        score = korrelation / (len(signal) - lag) * bevorzugung
        kandidaten.append((score, lag))
    score, lag = max(kandidaten)
    if score <= 0:
        raise ValueError("Kein regelmäßiger Beat gefunden.")
    phasen = [0.0] * lag
    for i, v in enumerate(signal):
        phasen[i % lag] += v
    phase = max(range(lag), key=phasen.__getitem__)
    phase_anteil = phasen[phase] / max(sum(phasen), 1e-9)
    bpm = 60 * hz / lag
    # Konfidenz ist eine Schätzung, kein Beweis für Taktart/Downbeat.
    staerke = min(1.0, score * (len(signal) - lag) / max(e, 1e-9) * 1.3)
    sicherheit = round(min(0.99, max(0.05, staerke * 0.8 + phase_anteil * 0.2)), 2)
    return {"bpm": round(bpm, 2), "beat0": round(phase / hz, 3),
            "confidence": sicherheit, "meter": 4, "method": "onset-autocorrelation"}


def _merkmale(pcm):
    """RMS, Onsets und Hochfrequenz-Proxy pro 10 ms, ohne große FFT-Modelle."""
    samples = array("h")
    samples.frombytes(pcm[:len(pcm) - len(pcm) % 2])
    if sys.byteorder != "little":
        samples.byteswap()
    energie, brillanz = [], []
    for i in range(0, len(samples) - HOP + 1, HOP):
        teil = samples[i:i + HOP]
        rms = math.sqrt(sum(v * v for v in teil) / HOP)
        energie.append(rms)
        differenz = sum(abs(teil[k] - teil[k-1]) for k in range(1,HOP))
        brillanz.append(differenz / max(1, HOP-1) / max(1,rms))
    # Onset = positiver Energieanstieg gegenüber kurzem Grundpegel.
    onset = [0.0] * len(energie)
    for i in range(5, len(energie)):
        baseline = sum(energie[i-5:i]) / 5
        onset[i] = max(0.0, energie[i] - baseline)
    return onset, energie, brillanz


def _bar0(onsets, beat0, bpm):
    """Probabler 4er-Downbeat, über den langen Rhythmus geschätzt."""
    period = 60 / bpm
    bar = period * 4
    scores = []
    for offset in range(4):
        start = beat0 + offset * period
        score = 0.0
        for k in range(max(1, int(min(len(onsets)/HZ, 65)/bar))):
            pos = round((start + k*bar)*HZ)
            score += sum(onsets[max(0,pos-3):min(len(onsets),pos+5)])
        scores.append(score)
    return round((beat0 + max(range(4),key=scores.__getitem__)*period) % bar,3)


def analysieren(datei, ffmpeg="ffmpeg"):
    """Audio kurz decodieren. Die Auswertung bleibt CPU-schonend und lokal."""
    cmd = [str(ffmpeg), "-nostdin", "-v", "error", "-i", str(datei),
           "-t", str(MAX_SECONDS), "-vn", "-ac", "1", "-ar", "4000",
           "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1"]
    try:
        lauf = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Ablehnung("beat_unavailable", "Tempoanalyse nicht verfügbar (ffmpeg prüfen).",
                        status=503) from exc
    if lauf.returncode != 0:
        raise Ablehnung("beat_decode", "Die Audiodatei konnte nicht analysiert werden.", status=422)
    try:
        onsets, energie, brillanz = _merkmale(lauf.stdout)
        # Ein rhythmischer Ausschnitt reicht für das Tempo. Die volle Länge
        # wird dagegen für Intro, Breakdown, Drop und Outro benötigt.
        # Auch nach langen ruhigen Intros einen Abschnitt mit stabilem
        # Rhythmus suchen. Fenster überlappen; die höchste Konfidenz gewinnt.
        analysefenster = []
        for versatz in (0, 45, 90, 150, 210):
            anfang = versatz * HZ
            teil = onsets[anfang:anfang + BEAT_WINDOW * HZ]
            if len(teil) < 8 * HZ:
                continue
            try:
                auswertung = beatgrid(teil)
            except ValueError:
                continue
            auswertung["beat0"] = round((auswertung["beat0"] + versatz)
                % (60 / auswertung["bpm"]), 3)
            analysefenster.append(auswertung)
        if not analysefenster:
            raise ValueError("Kein ausreichend regelmäßiger Rhythmus erkennbar.")
        grid = max(analysefenster,key=lambda v:v["confidence"])
        dauer = len(onsets) / HZ
        bar0 = _bar0(onsets, grid["beat0"], grid["bpm"])
        grid["bar0"] = bar0
        grid["duration"] = round(dauer,2)
        grid["energy"] = round(min(1.0,max(0.0,
            sum(onsets)/max(len(onsets),1)/2100)),2)
        grid.update(analyse_abschnitte(energie,onsets,brillanz,
                                      grid["bpm"],bar0,dauer,HZ))
        return grid
    except ValueError as exc:
        raise Ablehnung("beat_missing", str(exc), status=422) from exc


class BeatCache:
    """Einfacher, begrenzter RAM-Cache nach Dateigröße und Änderungszeit."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.daten = {}

    def holen(self, pfad):
        datei = safe_audio_path(self.cfg.music_root, pfad)
        if not datei.is_file():
            raise Ablehnung("not_found", "Dieser Song existiert nicht.", "pfad", 404)
        stat = datei.stat()
        schluessel = (str(Path(datei)), stat.st_mtime_ns, stat.st_size)
        with self.lock:
            if schluessel in self.daten:
                return dict(self.daten[schluessel])
        info = analysieren(datei, os.environ.get("SIRENS_FFMPEG") or "ffmpeg")
        with self.lock:
            if len(self.daten) >= 128:
                self.daten.pop(next(iter(self.daten)))
            self.daten[schluessel] = info
        return dict(info)
