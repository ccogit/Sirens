"""CPU-Analyse für WP10; keine Inferenz, keine Veränderung der Quelle."""
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import tempfile
import threading

from .. import beat
from ..dramaturgie import analyse_abschnitte
from .contracts import invalid, error, uint, finite
from .schema import validate

MIN_CONFIDENCE = .5
NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _rate(rate):
    if type(rate) is not int or not 8000 <= rate <= 192000:
        raise invalid("sample_rate")
    return rate


def source_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _unknown():
    return {"grid": None, "confidence": 0.0, "key": "unsicher",
            "key_confidence": 0.0, "onsets": [], "sections": {}}


def _fit(onsets, hz):
    """Bestands-Tempo als Hypothese; Impulszeiten entdriften per Regression."""
    if len(onsets) < 8 * hz:
        return None
    peak = max(onsets, default=0)
    if peak <= 1e-6:
        return None
    floor = median(onsets)
    threshold = max(peak * .18, floor * 4)
    events = []
    for i, val in enumerate(onsets):
        if val >= threshold and (i == 0 or val > onsets[i-1]) and (
                i == len(onsets)-1 or val >= onsets[i+1]):
            if events and i-events[-1][0] < hz*.08:
                if val > events[-1][1]:
                    events[-1] = (i, val)
            else:
                events.append((i, val))
    if len(events) < 12:
        return None
    try:
        coarse = beat.beatgrid(onsets, hz)
    except ValueError:
        return None
    # Regelmäßige lokale Abstände vermeiden das Langzeit-Driften des 10-ms-Lags.
    intervals = [b[0]-a[0] for a, b in zip(events, events[1:])]
    typical = median(intervals)
    period = hz*60/coarse["bpm"]
    if abs(typical-period) > period*.15:
        return None
    indices = [round((t-events[0][0])/typical) for t, _ in events]
    if len(set(indices)) != len(indices):
        return None
    xm, ym = sum(indices)/len(indices), sum(t for t, _ in events)/len(events)
    denom = sum((x-xm)**2 for x in indices)
    period = sum((x-xm)*(t-ym) for x, (t, _) in zip(indices, events))/denom
    origin = ym-period*xm
    residual = [abs(t-origin-x*period) for x, (t, _) in zip(indices, events)]
    coverage = len(events)/(indices[-1]+1)
    if period <= 0 or not 65 <= 60*hz/period <= 185 or coverage < .8:
        return None
    if sum(v <= hz*.02 for v in residual)/len(residual) < .95:
        return None
    phase = origin % period
    if min(phase, period-phase) < .5:
        phase = 0.0
    # Accent-Verteilung über alle Schläge, kein willkürlicher sicherer Downbeat.
    scores = [[] for _ in range(4)]
    for x, (t, val) in zip(indices, events):
        scores[round((origin+x*period-phase)/period)%4].append(val)
    means = [sum(s)/len(s) if s else 0 for s in scores]
    ranking = sorted(range(4), key=means.__getitem__, reverse=True)
    accent = (means[ranking[0]]-means[ranking[1]])/max(means[ranking[0]], 1e-9)
    confidence = min(.95, coverage*(1-median(residual)/max(1, period)))
    if accent < .12:
        confidence = min(confidence, .49)
    return (60*hz/period, phase/hz, (phase+ranking[0]*period)/hz,
            confidence, [t/hz for t, _ in events])


def chroma_key(samples, rate):
    """Konservative Dur/Moll-Schätzung mit Goertzel, maximal 30 Sekunden."""
    size = round(rate*.25)
    if size < 1 or len(samples) < size:
        return "unsicher", 0.0
    chroma = [0.0]*12
    window = [.5-.5*math.cos(math.tau*i/size) for i in range(size)]
    coeffs = [2*math.cos(math.tau*440*2**((n-69)/12)/rate) for n in range(45, 85)]
    tonal = total = 0
    for start in range(0, min(len(samples), rate*30)-size+1, size):
        block = [float(v)*w for v,w in zip(samples[start:start+size], window)]
        energy = sum(v*v for v in block)
        if energy < 1e-9:
            continue
        powers = []
        for coef in coeffs:
            a = b = 0.
            for value in block:
                a, b = value+coef*a-b, a
            powers.append(max(0., a*a+b*b-coef*a*b))
        peaks = [(i,p) for i,p in enumerate(powers)
                 if p > (powers[i-1] if i else 0) and p > (powers[i+1] if i+1<len(powers) else 0)]
        strength = sum(p for _,p in peaks)/(size*energy)
        total += 1
        if strength < .12:
            continue
        tonal += 1
        maximum = max(powers)
        for i,p in peaks:
            if p >= maximum*.08:
                chroma[(i+45)%12] += p
    s = sum(chroma)
    if not s or not total or tonal/total < .6 or sum(v > .08*s for v in chroma) < 3:
        return "unsicher", 0.0
    candidates = []
    for root in range(12):
        for mode, third, scale in (("Dur", 4, (0,2,4,5,7,9,11)),
                                   ("Moll", 3, (0,2,3,5,7,8,10))):
            score = (.6*sum(chroma[(root+x)%12] for x in (0,third,7))
                     + .25*sum(chroma[(root+x)%12] for x in scale)
                     + .15*chroma[root])/s
            candidates.append((score, root, mode))
    candidates.sort(reverse=True)
    score, root, mode = candidates[0]
    margin = score-candidates[1][0]
    confidence = min(.9, margin*5, score)
    return (f"{NAMES[root]} {mode}", confidence) if confidence >= .5 else ("unsicher", confidence)


def analyse_pcm(samples, analysis_rate=4000, sample_rate=48000):
    """Mono-Floats mit 4 kHz; BeatGrid-Frames beziehen sich auf sample_rate."""
    _rate(sample_rate)
    if analysis_rate != 4000:
        raise invalid("analysis_rate")
    samples = list(samples)
    if not all(finite(v) and -1 <= v <= 1 for v in samples):
        raise invalid("samples")
    pcm = array("h", (round(v*32767) for v in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    onset, energy, brightness = beat._merkmale(pcm.tobytes())
    # Bestandsanalyse ignoriert die ersten fünf Hops; Klick am Anfang erhalten.
    for i in range(min(5, len(onset))):
        onset[i] = max(0, energy[i]-sum(energy[:i])/max(1, i))
    result = _unknown()
    result["key"], result["key_confidence"] = chroma_key(samples, analysis_rate)
    fit = _fit(onset, beat.HZ)
    if fit is None:
        return result
    bpm, beat0, bar0, confidence, events = fit
    result["confidence"] = confidence
    result["onsets"] = [round(t*sample_rate) for t in events]
    if confidence < MIN_CONFIDENCE:
        return result
    result["grid"] = validate("beatgrid", {"bpm": bpm, "beat0": round(beat0*sample_rate),
        "bar0": round(bar0*sample_rate), "confidence": confidence})
    result["sections"] = analyse_abschnitte(energy, onset, brightness, bpm, bar0,
                                            len(onset)/beat.HZ, beat.HZ)
    return result


def analyse_file(path, sample_rate=48000, ffmpeg="ffmpeg"):
    """Nur bereits serverseitig validierte lokale Pfade; ffmpeg aus Konfiguration."""
    _rate(sample_rate)
    try:
        run = subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-i", str(path),
                              "-t", str(beat.MAX_SECONDS), "-vn", "-ac", "1", "-ar", "4000",
                              "-f", "s16le", "pipe:1"], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise error("unavailable") from exc
    if run.returncode or len(run.stdout)%2:
        raise invalid("audio")
    pcm = array("h")
    pcm.frombytes(run.stdout)
    if sys.byteorder != "little":
        pcm.byteswap()
    return analyse_pcm([v/32768 for v in pcm], sample_rate=sample_rate)


def correct_grid(grid, rate, action, value=None):
    """Explizite manuelle Korrektur; confidence=1 bezeichnet Benutzervorgabe."""
    _rate(rate)
    if grid is None:
        if action != "tap":
            raise invalid("grid")
        grid = {"beat0": 0, "bar0": 0, "bpm": 120, "confidence": 0}
    grid = dict(validate("beatgrid", grid))
    if grid.get("tempo_map"):
        raise invalid("tempo_map")  # manuelle Korrekturen nur am konstanten Raster
    if action in ("half", "double"):
        grid["bpm"] *= .5 if action == "half" else 2
        period = 60*rate/grid["bpm"]
        grid["bar0"] = round(grid["beat0"]+round((grid["bar0"]-grid["beat0"])/period)*period)
    elif action == "bar":
        if type(value) is not int:
            raise invalid("bar")
        grid["bar0"] = round((grid["bar0"]+value*60*rate/grid["bpm"])%(240*rate/grid["bpm"]))
    elif action == "phase":
        if type(value) is not int:
            raise invalid("phase")
        period = 60*rate/grid["bpm"]
        grid["beat0"] = round((grid["beat0"]+value)%period)
        grid["bar0"] = round((grid["bar0"]+value)%(4*period))
    elif action == "tap":
        if not isinstance(value, (tuple,list)) or not 3 <= len(value) <= 64:
            raise invalid("tap")
        for v in value:
            uint(v, "tap")
        intervals = [b-a for a,b in zip(value,value[1:])]
        period = median(intervals)
        if period <= 0 or any(abs(v-period) > .25*period for v in intervals):
            raise invalid("tap")
        grid["bpm"] = 60*rate/period
        grid["beat0"] = round(value[0]%period)
        grid["bar0"] = round(value[0]%(4*period))
    else:
        raise invalid("action")
    grid["confidence"] = 1.0
    return validate("beatgrid", grid)


class CorrectionStore:
    """Je SHA-256 ein atomarer Cache-Eintrag; keine vom Client gewählten Pfade."""
    def __init__(self, directory):
        self.root = Path(directory)
        self.lock = threading.RLock()

    def _path(self, digest):
        if not isinstance(digest, str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise invalid("source_hash")
        return self.root / (digest+".json")

    def load(self, digest, rate):
        _rate(rate)
        with self.lock:
            try:
                data = json.loads(self._path(digest).read_text(encoding="utf-8"))
            except FileNotFoundError:
                return None
            stored_rate = _rate(data["rate"])
            grid = validate("beatgrid", data["grid"])
            grid = dict(grid)
            for key in ("beat0", "bar0"):
                grid[key] = round(grid[key]*rate/stored_rate)
            if "tempo_map" in grid:
                grid["tempo_map"] = [{**p, "source_frame": round(p["source_frame"]*rate/stored_rate)}
                                     for p in grid["tempo_map"]]
            return validate("beatgrid", grid)

    def apply(self, digest, grid, rate, action, value=None):
        with self.lock:
            path = self._path(digest)
            corrected = correct_grid(self.load(digest, rate) or grid, rate, action, value)
            self.root.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=self.root, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump({"rate": rate, "grid": corrected}, stream, allow_nan=False)
                os.replace(name, path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
            return corrected


def notes_to_frames(notes, sample_rate):
    """Vorhandene Basic-Pitch-JSON-Noten; kein Import/Start des Modellworkers."""
    _rate(sample_rate)
    if not isinstance(notes, list) or len(notes)>12000:
        raise invalid("notes")
    result = []
    for note in notes:
        if not isinstance(note, list) or len(note)!=4 or not all(finite(v) for v in note):
            raise invalid("notes")
        start,end,pitch,amplitude = note
        if not 0<=start<end<=7200 or type(pitch) is not int or not 0<=pitch<=127 or not 0<=amplitude<=1:
            raise invalid("notes")
        result.append({"start_frame": round(start*sample_rate), "end_frame": round(end*sample_rate),
                       "pitch": pitch, "amplitude": amplitude})
    return sorted(result, key=lambda n:(n["start_frame"],n["pitch"]))
