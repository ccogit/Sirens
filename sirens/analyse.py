"""Analyse des Favoriten und daraus abgeleitete Voreinstellungen für das Studio.

Gemessen wird mit der vorhandenen `mastering_engine` des Projekts (eigener Prozess, damit der Dienst ohne ihre
Bibliotheken startet). Die Empfehlung stützt sich auf die Klangvorlage `klangvorlage.json`: gemessene Paare aus
unbearbeitetem Original und eMastered-Fassung desselben Songs. Bewertungen des Nutzers sind keine Klangvorlage –
sie meinen die Musik, nicht den Klang (Nutzer, 14.11.2026). Die Genre-Zielbilder der Engine bleiben als
zusätzliche, ausdrücklich geschätzte Voreinstellungen erhalten.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from .contracts import Ablehnung, safe_audio_path

REPO = Path(__file__).resolve().parents[2]
VORLAGE = json.loads((Path(__file__).with_name("klangvorlage.json")).read_text(encoding="utf-8"))
BAENDER = (("sub", "eq_sub", "Sub"), ("bass", "eq_bass", "Bass"), ("low_mid", "eq_tiefmitten", "Tiefmitten"),
           ("high_mid", "eq_praesenz", "Präsenz"), ("air", "eq_luft", "Luft"))
STILE = (("balanced", "Genre-Zielbild", "Schätzwert der Engine für das Genre", -14.0),
         ("warm", "Warm", "Schätzwert: mehr Wärme, weichere Höhen", -14.0),
         ("open", "Offen", "Schätzwert: luftiger und breiter", -14.0),
         ("loud", "Laut", "Schätzwert: dichter und lauter", -10.0))
SCHON_GENUG = 3.0  # liegt ein Band schon so weit über (unter) den Vorlagen, wird es nicht weiter angehoben (abgesenkt)
_LAUF = """
import dataclasses, json, sys
from mastering_engine import analysis, recommendation
f = analysis.analyze(sys.argv[1])
tags = json.loads(sys.argv[2])
cluster = recommendation._CLUSTERS[recommendation.resolve_genre_cluster(tags)]
profile = {s: dataclasses.asdict(recommendation.recommend(f, genre_tags=tags, style=s)) for s in json.loads(sys.argv[3])}
print(json.dumps({"f": dataclasses.asdict(f), "cluster": cluster, "profile": profile}))
"""


def verfuegbar():
    return (REPO / "mastering_engine" / "analysis.py").is_file() and all(
        importlib.util.find_spec(m) is not None for m in ("librosa", "soundfile", "numpy", "imageio_ffmpeg"))


def _halb(wert):
    return round(wert * 2) / 2


def _zahl(wert):
    return f"{wert:.1f}".replace(".", ",").replace("-", "−")


def _preset(profil, lautheit):
    """Empfehlung der Engine auf die Regler des Studios legen (dieselben Bänder, dieselben drei Kompressorbänder)."""
    werte = {regler: 0.0 for _, regler, _ in BAENDER}
    namen = {band: regler for band, regler, _ in BAENDER}
    for band in profil["eq_bands"]:
        if band["band"] in namen:
            werte[namen[band["band"]]] = _halb(band["gain_db"])
    mb = profil["multiband"]
    ratio = lambda name: round(min(max(mb[name], 1.0), 4.0), 1)  # noqa: E731
    werte.update(komp_an=max(mb["low_ratio"], mb["mid_ratio"], mb["high_ratio"]) > 1.05,
                 komp_tief=ratio("low_ratio"), komp_mitte=ratio("mid_ratio"), komp_hoch=ratio("high_ratio"),
                 komp_schwelle=_halb(mb["mid_threshold_db"]), saettigung=_halb(profil["saturation_drive_db"]),
                 breite=float(min(max(round(profil["stereo_width_target"] * 20) * 5, 0), 200)),
                 lautheit=lautheit, decke=profil["limiter_ceiling_dbtp"])
    return werte


def _vorlage_preset(f, baender, lautheit):
    """Was eMastered im Mittel verändert, auf die Regler gelegt. Kompressorwerte sind eine vorsichtige Näherung."""
    werte = {}
    for band in baender:
        schritt = VORLAGE["veraenderung"]["baender"][band["band"]]
        zu_viel = band["abstand"] >= SCHON_GENUG if schritt > 0 else band["abstand"] <= -SCHON_GENUG
        werte[band["name"]] = 0.0 if zu_viel else _halb(schritt)
    ueber = f["crest_factor_db"] - VORLAGE["master_median"]["crest"]
    mitte = round(1.0 + min(max(ueber, 0.0), 3.0) * 0.25, 1)
    werte.update(komp_an=ueber > 0.5, komp_schwelle=-16.0, komp_tief=round(mitte + 0.1, 1), komp_mitte=mitte,
                 komp_hoch=round(max(mitte - 0.1, 1.0), 1), saettigung=0.0, breite=100.0, lautheit=lautheit, decke=-1.0)
    return werte


def _empfehlungen(f, baender, preset):
    v, m = VORLAGE["veraenderung"], VORLAGE["master_median"]
    lufs, spitze, crest = f["integrated_lufs"], f["true_peak_dbtp"], f["crest_factor_db"]
    saetze = [f"Lautheit {_zahl(lufs)} LUFS. Die eMastered-Fassungen liegen bei {_zahl(m['lufs'])} LUFS; "
              f"die Empfehlung zielt auf {_zahl(preset['lautheit'])}."]
    if spitze > -1.0:
        saetze.append(f"Spitzen bis {_zahl(spitze)} dBTP: Die Pegeldecke bei −1 dBTP fängt das ab. "
                      f"(eMastered selbst lässt Spitzen bis {_zahl(m['spitze'])} dBTP zu; das übernehmen wir nicht.)")
    if preset["komp_an"]:
        saetze.append(f"Dynamik: Spitze zu Mittel {_zahl(crest)} dB, eMastered-Fassungen {_zahl(m['crest'])} dB. "
                      "Leichte Kompression in drei Bändern bringt den Song dorthin.")
    else:
        saetze.append(f"Dynamik: Spitze zu Mittel {_zahl(crest)} dB, schon so dicht wie die eMastered-Fassungen "
                      f"({_zahl(m['crest'])} dB). Kompressor bleibt aus.")
    b = v["baender"]
    saetze.append(f"Klang: eMastered hebt die Luft um rund {_zahl(b['air'])} dB an, Präsenz und Bass um knapp 1 dB "
                  f"und nimmt den Sub um etwa {_zahl(abs(b['sub']))} dB zurück. Die Empfehlung übernimmt das.")
    for band in baender:
        if preset[band["name"]] == 0.0 and abs(_halb(b[band["band"]])) > 0:
            saetze.append(f"{band['titel']} liegt hier schon {_zahl(abs(band['abstand']))} dB "
                          f"{'über' if band['abstand'] > 0 else 'unter'} den eMastered-Fassungen: bleibt unverändert.")
    if f["stereo_correlation"] < 0.3:
        saetze.append(f"Stereo-Korrelation {_zahl(f['stereo_correlation'])}: Phasenrisiko, nicht verbreitern.")
    else:
        saetze.append("Stereo: eMastered verändert die Breite praktisch nicht; die Empfehlung lässt sie bei 100 %.")
    saetze += list(f["warnings"])
    saetze.append(f"Grundlage: {VORLAGE['paare']} gemessene Paare aus Original und eMastered-Fassung, alle aus einem "
                  "Album. Für andere Stile ist das ein Startpunkt; entscheidend ist dein Ohr. Die Voreinstellungen "
                  "„Genre-Zielbild“, „Warm“, „Offen“ und „Laut“ beruhen auf Schätzwerten.")
    return saetze


def auswerten(roh):
    """Rohdaten der Engine → Messwerte, Empfehlungen und Voreinstellungen für die Seite."""
    f, profile = roh["f"], roh["profile"]
    ist, vergleich = f["spectral_bands_relative_to_mid_db"], VORLAGE["master_median"]["baender"]
    baender = [{"name": regler, "band": band, "titel": titel, "abstand": round(ist[band] - vergleich[band], 1)}
               for band, regler, titel in BAENDER if ist.get(band) is not None]
    ziel = _halb(VORLAGE["master_median"]["lufs"])
    empfehlung = _vorlage_preset(f, baender, ziel)
    presets = [{"name": "vorlage", "titel": "Empfehlung", "beschreibung": "aus den eMastered-Fassungen abgeleitet",
                "einstellungen": empfehlung},
               {"name": "vorlage_leise", "titel": "Streaming −14", "beschreibung": "wie die Empfehlung, aber −14 LUFS",
                "einstellungen": {**empfehlung, "lautheit": -14.0}}]
    presets += [{"name": stil, "titel": titel, "beschreibung": text, "einstellungen": _preset(profile[stil], lautheit)}
                for stil, titel, text, lautheit in STILE]
    return {
        "messwerte": {"lufs": round(f["integrated_lufs"], 1), "spitze": round(f["true_peak_dbtp"], 1),
                      "spanne": round(f["loudness_range_lu"], 1), "crest": round(f["crest_factor_db"], 1),
                      "korrelation": round(f["stereo_correlation"], 2), "breite": round(f["stereo_width_ratio"], 2),
                      "dauer": round(f["duration_seconds"])},
        "vergleich": f"{VORLAGE['master']} eMastered-Fassungen", "baender": baender,
        "empfehlungen": _empfehlungen(f, baender, empfehlung), "presets": presets,
    }


def analysieren(cfg, favorit, tags=()):
    if not verfuegbar():
        raise Ablehnung("no_analysis", "Die Analyse ist auf diesem Rechner nicht eingerichtet "
                        "(mastering_engine, librosa, soundfile, imageio-ffmpeg).", status=503)
    datei = safe_audio_path(cfg.music_root, favorit)
    befehl = [sys.executable, "-c", _LAUF, str(datei), json.dumps(list(tags)), json.dumps([s[0] for s in STILE])]
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO,
                              timeout=600, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise Ablehnung("timeout", "Die Analyse hat zu lange gedauert.", status=500) from None
    if lauf.returncode != 0:
        raise Ablehnung("analysis_failed", "Die Analyse ist gescheitert: " + lauf.stderr.strip()[-300:], status=500)
    return auswerten(json.loads(lauf.stdout.strip().splitlines()[-1]))
