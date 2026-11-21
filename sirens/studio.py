"""Mastering-Studio: Regler → ffmpeg-Filterkette (EQ, Kompressor, Stereo-Breite, Lautheit mit Pegeldecke).

Startwerte liefert die Analyse (analyse.py). Zweites Werkzeug: Matchering gleicht Klang und Lautheit an einen Referenzsong an (wenn installiert).
Geschrieben wird immer eine neue WAV-Datei neben dem Favoriten; vorhandene Dateien bleiben unberührt.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import analyse
from .contracts import Ablehnung, safe_audio_path

# Regler: Name -> (kleinster, größter, Standardwert)
GRENZEN = {
    "eq_sub": (-12, 12, 0), "eq_bass": (-12, 12, 0), "eq_tiefmitten": (-12, 12, 0), "eq_praesenz": (-12, 12, 0),
    "eq_luft": (-12, 12, 0),
    "komp_schwelle": (-40, 0, -16), "komp_tief": (1, 4, 1.5), "komp_mitte": (1, 4, 1.5), "komp_hoch": (1, 4, 1.5),
    "saettigung": (0, 6, 0),
    "breite": (0, 200, 100), "lautheit": (-20, -8, -14), "decke": (-3, -0.1, -1),
}
STANDARD = {**{name: g[2] for name, g in GRENZEN.items()}, "komp_an": False}
TIMEOUT = 900
# Rendern mit der mastering_engine: Regler → MasteringProfile → dsp_chain.render (eigener Prozess).
_ENGINE = """
import json, sys
import numpy as np, pedalboard as pb, soundfile as sf
from mastering_engine import dsp_chain as d, recommendation as r
w = json.loads(sys.argv[3])
data, sr = sf.read(sys.argv[1], always_2d=True)
if data.shape[1] == 1:
    data = np.repeat(data, 2, axis=1)
stereo = data.T.astype(np.float32)
baender = (("sub", "eq_sub"), ("bass", "eq_bass"), ("low_mid", "eq_tiefmitten"), ("high_mid", "eq_praesenz"), ("air", "eq_luft"))
# Luft-Kuhschwanz bei 5 kHz statt 10 kHz: Erst so kommt die Anhebung im ganzen Band 6-20 kHz an (gemessen 14.11.2026).
mitte = dict(r.BAND_CENTER_HZ, air=5000)
eq = [r.EqBand(band=b, center_hz=mitte[b], gain_db=w[k], kind=r.BAND_KIND[b]) for b, k in baender if abs(w[k]) >= 0.1]
mid, side = d._ms_encode(stereo)
mid, side = d._apply_eq(mid, side, eq, sr)
stereo = d._ms_decode(mid, side)
if w["komp_an"]:
    s = w["komp_schwelle"]
    mb = r.MultibandSettings(crossover_low_hz=200.0, crossover_high_hz=2000.0, low_threshold_db=s - 2.0, low_ratio=w["komp_tief"],
                             mid_threshold_db=s, mid_ratio=w["komp_mitte"], high_threshold_db=s + 2.0, high_ratio=w["komp_hoch"])
    stereo = d._apply_multiband(stereo, sr, mb, preserve_band_balance=True)
if w["saettigung"] > 0:
    stereo = d._oversampled_nonlinear(stereo, sr, 4, w["saettigung"], -0.1)
stereo = d._apply_stereo_width(stereo, w["breite"] / 100.0)
sf.write(sys.argv[2], stereo.T, sr, subtype="PCM_24")
"""
_ANGLEICHEN = ("import sys, matchering as mg\n"
               "mg.log(print)\n"
               "mg.process(target=sys.argv[1], reference=sys.argv[2], results=[mg.pcm24(sys.argv[3])])\n")


def ffmpeg(cfg):
    return os.environ.get("SIRENS_FFMPEG") or shutil.which("ffmpeg")


def werkzeuge(cfg):
    return {"ffmpeg": bool(ffmpeg(cfg)), "matchering": importlib.util.find_spec("matchering") is not None,
            "analyse": analyse.verfuegbar(),
            "engine": analyse.verfuegbar() and importlib.util.find_spec("pedalboard") is not None,
            "phaselimiter": phaselimiter(cfg) is not None}


def einstellungen(data):
    """Reglerwerte prüfen und auf die erlaubten Bereiche festlegen. Fehlendes bekommt den Standardwert."""
    if data is None:
        data = {}
    if not isinstance(data, dict) or set(data) - set(STANDARD):
        raise Ablehnung("invalid", "Die Studio-Einstellungen enthalten unbekannte Regler.", "einstellungen")
    werte = {}
    for name, (unten, oben, standard) in GRENZEN.items():
        wert = data.get(name, standard)
        if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not unten <= wert <= oben:
            raise Ablehnung("invalid", f"„{name}“ muss zwischen {unten} und {oben} liegen.", "einstellungen")
        werte[name] = round(float(wert), 2)
    werte["komp_an"] = data.get("komp_an", False) is True
    return werte


def kette(w):
    """ffmpeg-Filter vor der Lautheitsstufe (Ersatzweg ohne Engine: ein Kompressor, keine Sättigung)."""
    teile = []
    # Dieselben Bänder wie die Analyse (mastering_engine): Sub 40 Hz, Bass 120, Tiefmitten 350, Präsenz 3500, Luft 10000.
    if w["eq_sub"]:
        teile.append(f"bass=g={w['eq_sub']}:f=40:t=q:w=0.7")
    for name, frequenz in (("eq_bass", 120), ("eq_tiefmitten", 350), ("eq_praesenz", 3500)):
        if w[name]:
            teile.append(f"equalizer=f={frequenz}:t=q:w=1:g={w[name]}")
    if w["eq_luft"]:
        teile.append(f"treble=g={w['eq_luft']}:f=10000:t=q:w=0.7")
    if w["komp_an"]:
        teile.append("acompressor=threshold={:.5f}:ratio={}:attack=20:release=250".format(
            10 ** (w["komp_schwelle"] / 20), w["komp_mitte"]))
    if w["breite"] != 100:
        teile.append(f"extrastereo=m={w['breite'] / 100}:c=0")
    return teile


def _lauf(befehl):
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise Ablehnung("timeout", "Das Rendern hat zu lange gedauert.", status=500) from None
    if lauf.returncode != 0:
        raise Ablehnung("render_failed", "Das Rendern ist gescheitert: " + lauf.stderr.strip()[-300:], status=500)
    return lauf.stderr + lauf.stdout


def messen(exe, datei, filter_davor=(), ziel=-14.0, decke=-1.0):
    """Lautheit messen (EBU R128). Liefert die Werte des loudnorm-Messlaufs."""
    stufe = f"loudnorm=I={ziel}:TP={decke}:LRA=11:print_format=json"
    aus = _lauf([exe, "-hide_banner", "-nostats", "-i", str(datei), "-af", ",".join([*filter_davor, stufe]),
                 "-f", "null", "-"])
    treffer = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", aus, re.S)
    if not treffer:
        raise Ablehnung("render_failed", "Die Lautheit ließ sich nicht messen.", status=500)
    return json.loads(treffer[-1])


def _ziel(quelle, zusatz):
    """Freier Dateiname neben der Quelle; vorhandene Dateien werden nie überschrieben."""
    for nr in range(1, 100):
        ziel = quelle.with_name(f"{quelle.stem} ({zusatz}{'' if nr == 1 else f' {nr}'}).wav")
        if not ziel.exists():
            return ziel
    raise Ablehnung("limit", "Zu diesem Song gibt es schon zu viele Master-Entwürfe.", status=409)


def _entwurf(cfg, ziel, weg, werte, exe):
    m = messen(exe, ziel)
    return {"datei": ziel.relative_to(cfg.music_root.resolve()).as_posix(), "weg": weg, "einstellungen": werte,
            "lufs": float(m["input_i"]), "spitze": float(m["input_tp"]), "spanne": float(m["input_lra"])}


def _exe(cfg):
    exe = ffmpeg(cfg)
    if not exe:
        raise Ablehnung("no_ffmpeg", "ffmpeg ist nicht installiert; das Studio kann nicht rendern.", status=503)
    return exe


def _schreiben(exe, quelle, filter_, ziel):
    """Über eine Zwischendatei schreiben; ein vorhandenes Ziel wird nie ersetzt."""
    halb = ziel.with_name(ziel.name + ".teil")
    try:
        _lauf([exe, "-hide_banner", "-nostats", "-y", "-i", str(quelle), "-af", ",".join(filter_),
               "-ar", "48000", "-c:a", "pcm_s24le", "-f", "wav", str(halb)])
        os.rename(halb, ziel)  # scheitert unter Windows, wenn es das Ziel inzwischen gibt
    finally:
        if halb.exists():
            halb.unlink()  # nur die eigene, unfertige Zwischendatei


def _ausgang(werte, anhebung):
    """Lautheitsstufe wie am Pult: Pegel anheben, dann Limiter knapp unter der Pegeldecke."""
    # Der Limiter läuft vierfach überabgetastet, damit auch Spitzen zwischen den Abtastwerten unter der Decke bleiben.
    return [f"volume={anhebung:.2f}dB", "aresample=192000",
            "alimiter=limit={:.5f}:attack=5:release=60:level=disabled".format(10 ** ((werte["decke"] - 0.2) / 20)),
            "aresample=48000"]


def _formen(quelle, werte, ziel):
    """Klang mit der mastering_engine formen: Mid/Side-EQ, Kompression in drei Bändern, Sättigung, Breite."""
    try:
        lauf = subprocess.run([sys.executable, "-c", _ENGINE, str(quelle), str(ziel), json.dumps(werte)], cwd=analyse.REPO,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise Ablehnung("timeout", "Das Rendern hat zu lange gedauert.", status=500) from None
    if lauf.returncode != 0 or not ziel.is_file():
        raise Ablehnung("render_failed", "Das Rendern ist gescheitert: " + lauf.stderr.strip()[-300:], status=500)


def _auf_lautheit(exe, quelle, davor, werte, ziel):
    """Ausgangsstufe: auf die Ziel-Lautheit anheben, Limiter unter der Pegeldecke, einmal nachmessen und ausgleichen."""
    anhebung = werte["lautheit"] - float(messen(exe, quelle, davor)["input_i"])
    probe = float(messen(exe, quelle, [*davor, *_ausgang(werte, anhebung)])["input_i"])
    anhebung += min(max(werte["lautheit"] - probe, 0.0), 3.0)  # der Limiter nimmt etwas Lautheit weg
    _schreiben(exe, quelle, [*davor, *_ausgang(werte, anhebung)], ziel)


def rendern(cfg, favorit, data):
    """Studio-Master als 24-Bit-WAV schreiben und nachmessen. Klang mit der Engine, sonst mit ffmpeg allein."""
    werte, exe = einstellungen(data), _exe(cfg)
    quelle = safe_audio_path(cfg.music_root, favorit)
    ziel = _ziel(quelle, "Studio Master")
    if not werkzeuge(cfg)["engine"]:
        _auf_lautheit(exe, quelle, kette(werte), werte, ziel)
        return _entwurf(cfg, ziel, "Studio", werte, exe)
    with tempfile.TemporaryDirectory() as tmp:
        geformt = Path(tmp) / "geformt.wav"
        _formen(quelle, werte, geformt)
        _auf_lautheit(exe, geformt, [], werte, ziel)
    return _entwurf(cfg, ziel, "Studio (Engine)", werte, exe)


def phaselimiter(cfg):
    ordner = Path(os.environ.get("SIRENS_PHASELIMITER", r"E:\AMM\tools\phaselimiter\phaselimiter"))
    return ordner if (ordner / "bin" / "phase_limiter.exe").is_file() else None


def automatik(cfg, favorit, lautheit=-10.5):
    """Vollautomatisch mastern mit phaselimiter (Open Source, MIT): sucht Klang und Dynamik selbst, dann Limiter."""
    exe, ordner = _exe(cfg), phaselimiter(cfg)
    if ordner is None:
        raise Ablehnung("no_phaselimiter", "phaselimiter ist auf diesem Rechner nicht eingerichtet.", status=503)
    if isinstance(lautheit, bool) or not isinstance(lautheit, (int, float)) or not -20 <= lautheit <= -8:
        raise Ablehnung("invalid", "„lautheit“ muss zwischen -20 und -8 liegen.", "lautheit")
    quelle = safe_audio_path(cfg.music_root, favorit)
    ziel = _ziel(quelle, "Auto Master")
    with tempfile.TemporaryDirectory() as tmp:
        ein, aus = Path(tmp) / "ein.wav", Path(tmp) / "aus.wav"
        _lauf([exe, "-hide_banner", "-nostats", "-y", "-i", str(quelle), "-ar", "44100", "-ac", "2", "-c:a", "pcm_s24le", str(ein)])
        _lauf([str(ordner / "bin" / "phase_limiter.exe"), "--input", str(ein), "--output", str(aus), "--mastering", "true",
               "--mastering_mode=mastering5", "--sound_quality2_cache", str(ordner / "resource" / "sound_quality2_cache"),
               "--reference", str(float(lautheit))])
        _schreiben(exe, aus, ["volume=-1.0dB"], ziel)  # phaselimiter begrenzt auf 0 dBFS; 1 dB Reserve für die Pegeldecke
    return _entwurf(cfg, ziel, "Automatik (phaselimiter)", {"lautheit": float(lautheit)}, exe)


def angleichen(cfg, favorit, referenz):
    """Klang und Lautheit an einen Referenzsong angleichen (Matchering, Open Source)."""
    exe = _exe(cfg)
    if not werkzeuge(cfg)["matchering"]:
        raise Ablehnung("no_matchering", "Matchering ist nicht installiert (pip install matchering).", status=503)
    quelle = safe_audio_path(cfg.music_root, favorit)
    vorbild = safe_audio_path(cfg.music_root, referenz, "referenz")
    if not vorbild.is_file() or vorbild == quelle:
        raise Ablehnung("invalid_path", "Die Referenz muss ein anderer vorhandener Song sein.", "referenz")
    ziel = _ziel(quelle, "Angeglichen")
    with tempfile.TemporaryDirectory() as tmp:
        wavs = []
        for nr, datei in enumerate((quelle, vorbild)):
            wav = Path(tmp) / f"{nr}.wav"
            _lauf([exe, "-hide_banner", "-nostats", "-y", "-i", str(datei), "-ar", "44100", "-ac", "2", str(wav)])
            wavs.append(str(wav))
        aus = Path(tmp) / "aus.wav"
        _lauf([sys.executable, "-c", _ANGLEICHEN, *wavs, str(aus)])
        _schreiben(exe, aus, ["volume=-1.2dB"], ziel)  # Reserve, weil Matchering nur Abtastspitzen begrenzt
    return _entwurf(cfg, ziel, f"Angeglichen an {vorbild.stem}", {"referenz": referenz}, exe)
