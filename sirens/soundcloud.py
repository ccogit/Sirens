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
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

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


def _zugang(env_datei=None):
    """SoundCloud-Token ausschließlich lokal lesen; nie in Fehlermeldungen ausgeben."""
    eigene = EIGEN / ".env"
    try:
        zeilen = (env_datei or (eigene if eigene.exists() else PROJEKT / ".env")).read_text(
            encoding="utf-8-sig").splitlines()
    except OSError:
        return ""
    werte = dict(z.split("=", 1) for z in zeilen if "=" in z and not z.lstrip().startswith("#"))
    return werte.get("SOUNDCLOUD_ACCESS_TOKEN", "").strip().strip('"').strip("'")


class _NurSoundCloud(HTTPRedirectHandler):
    """Redirects nur an die SoundCloud-API zulassen, niemals zu fremden Hosts."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urlparse(newurl)
        if host.scheme != "https" or host.hostname != "api.soundcloud.com":
            raise ValueError("SoundCloud hat auf eine fremde Adresse verwiesen.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def metadaten_ersetzen(link, beschreibung, tags):
    """Bestehenden Track aktualisieren, nie einen neuen Upload starten. Fehlertext oder leer."""
    url = urlparse(link)
    if url.scheme != "https" or url.hostname not in ("soundcloud.com", "www.soundcloud.com"):
        return "Kein gültiger SoundCloud-Tracklink."
    token = _zugang()
    if not token or token == "change-me":
        return "SoundCloud ist nicht verbunden. Bitte Authentifizierung erneuern."
    opener = build_opener(_NurSoundCloud())
    headers = {"Authorization": "OAuth " + token, "Accept": "application/json"}
    try:
        resolve = "https://api.soundcloud.com/resolve?" + urlencode({"url": link})
        with opener.open(Request(resolve, headers=headers), timeout=20) as antwort:
            track = json.load(antwort)
        nummer = track.get("id")
        if not isinstance(nummer, int) or track.get("kind") != "track":
            return "Der SoundCloud-Link verweist nicht auf einen einzelnen Track."
        tag_liste = " ".join('"' + t + '"' if " " in t else t for t in tags)
        daten = json.dumps({"track": {"description": beschreibung, "tag_list": tag_liste}},
                           ensure_ascii=False).encode("utf-8")
        request = Request("https://api.soundcloud.com/tracks/" + quote(str(nummer)),
                          data=daten, method="PUT",
                          headers={**headers, "Content-Type": "application/json"})
        with opener.open(request, timeout=30) as antwort:
            if not 200 <= antwort.status < 300:
                return f"SoundCloud antwortet mit HTTP {antwort.status}."
        return ""
    except HTTPError as exc:
        if exc.code == 401:
            return "SoundCloud-Token abgelaufen. Bitte erneut verbinden und dann wiederholen."
        return f"SoundCloud antwortet mit HTTP {exc.code}. Es wurde kein neuer Track angelegt."
    except (URLError, TimeoutError, ValueError, OSError, TypeError, json.JSONDecodeError):
        return "Die Aktualisierung konnte nicht bestätigt werden. Bitte SoundCloud prüfen und erneut versuchen."
