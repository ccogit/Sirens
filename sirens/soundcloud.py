"""SoundCloud: Ist der Zugang eingerichtet, und das Cover eines schon hochgeladenen Songs ersetzen.

Den Upload selbst macht Claude (Skill sirens im umgebenden Projekt). Das Ersetzen des Covers ist ein einzelner, fester Aufruf von
scripts/soundcloud_upload.py und braucht deshalb keine Claude-Sitzung. Promotion lässt sich über die Schnittstelle
von SoundCloud nicht einschalten; die Seite verweist dafür auf SoundCloud selbst.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from .starter import PROJEKT

SKRIPT = PROJEKT / "scripts" / "soundcloud_upload.py"
EIGEN = Path(__file__).resolve().parents[1]  # Ordner von Sirens


def bereit(env_datei=None):
    """Ist SoundCloud eingerichtet? (Zugangstoken in der .env neben diesem Paket, sonst in der .env des Projekts)"""
    eigene = EIGEN / ".env"
    try:
        zeilen = (env_datei or (eigene if eigene.exists() else PROJEKT / ".env")).read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return False
    werte = dict(z.split("=", 1) for z in zeilen if "=" in z and not z.lstrip().startswith("#"))
    return werte.get("SOUNDCLOUD_ACCESS_TOKEN", "").strip() not in ("", "change-me")


def cover_ersetzen(cfg, link, cover):
    """Lädt `cover` (relativ zum Musikordner) als neues Bild zum Song unter `link`. Liefert "" oder den Grund des Scheiterns."""
    datei = cfg.music_root.joinpath(*cover.split("/"))
    eigen = os.environ.get("SIRENS_SOUNDCLOUD_CMD")  # für Tests: JSON-Liste statt des echten Skripts
    try:
        befehl = json.loads(eigen) if eigen else [sys.executable, str(SKRIPT)]
        lauf = subprocess.run([*befehl, str(datei.parent), "--replace-cover", link, "--cover", str(datei)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return f"Das Upload-Skript ließ sich nicht ausführen: {exc}"
    try:
        ergebnis = json.loads(lauf.stdout[lauf.stdout.index("{"):])
    except ValueError:
        return (lauf.stderr or lauf.stdout or "Keine Antwort vom Upload-Skript.").strip()[-400:]
    if lauf.returncode == 0 and ergebnis.get("status") == "artwork_replaced":
        return ""
    if ergebnis.get("http_status"):
        return f"SoundCloud antwortet mit {ergebnis['http_status']}: {str(ergebnis.get('response', ''))[:300]}"
    return str(ergebnis.get("error") or ergebnis)[:400]
