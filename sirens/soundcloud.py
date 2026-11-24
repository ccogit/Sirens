"""SoundCloud: Ist der Zugang eingerichtet, und das Cover eines schon hochgeladenen Songs ersetzen.

Den Upload selbst macht Claude (Skill sirens im umgebenden Projekt). Cover, Beschreibung und Tags eines schon
hochgeladenen Songs ersetzt ein fester Aufruf von scripts/soundcloud_upload.py; dafür braucht es keine Claude-Sitzung.
Das Skript erneuert ein abgelaufenes Zugangstoken selbst. Promotion lässt sich über die Schnittstelle
von SoundCloud nicht einschalten; die Seite verweist dafür auf SoundCloud selbst.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .starter import PROJEKT

SKRIPT = PROJEKT / "scripts" / "soundcloud_upload.py"
EIGEN = Path(__file__).resolve().parents[1]  # Ordner von Sirens


def _projekt():
    pfad = os.environ.get("SIRENS_SOUNDCLOUD_PROJECT")
    return Path(pfad) if pfad else PROJEKT


def bereit(env_datei=None):
    """Prüft das Zugangstoken an denselben Orten wie das konfigurierte Upload-Skript."""
    basis = _projekt()
    kandidaten = [basis / "sirens" / ".env", basis / "song-auftrag" / ".env", basis / ".env"]
    if not os.environ.get("SIRENS_SOUNDCLOUD_PROJECT"):
        kandidaten.insert(0, EIGEN / ".env")
    datei = Path(env_datei) if env_datei else next((p for p in kandidaten if p.is_file()), kandidaten[-1])
    try:
        zeilen = datei.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return False
    werte = {name.strip(): wert.strip() for z in zeilen if "=" in z and not z.lstrip().startswith("#")
             for name, wert in [z.split("=", 1)]}
    return werte.get("SOUNDCLOUD_ACCESS_TOKEN", "") not in ("", "change-me")


def _skript(ordner, *argumente, erfolg):
    """Upload-Skript ausführen. Liefert "" oder den Grund des Scheiterns."""
    eigen = os.environ.get("SIRENS_SOUNDCLOUD_CMD")  # für Tests: JSON-Liste statt des echten Skripts
    try:
        upload = _projekt() / "scripts" / SKRIPT.name
        befehl = json.loads(eigen) if eigen else [sys.executable, str(upload)]
        lauf = subprocess.run([*befehl, str(ordner), *argumente],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return f"Das Upload-Skript ließ sich nicht ausführen: {exc}"
    try:
        ergebnis = json.loads(lauf.stdout[lauf.stdout.index("{"):])
    except ValueError:
        return (lauf.stderr or lauf.stdout or "Keine Antwort vom Upload-Skript.").strip()[-400:]
    if lauf.returncode == 0 and ergebnis.get("status") == erfolg:
        return ""
    if ergebnis.get("http_status"):
        return f"SoundCloud antwortet mit {ergebnis['http_status']}: {str(ergebnis.get('response', ''))[:300]}"
    return str(ergebnis.get("error") or ergebnis)[:400]


def cover_ersetzen(cfg, link, cover):
    """Lädt `cover` (relativ zum Musikordner) als neues Bild zum Song unter `link`."""
    datei = cfg.music_root.joinpath(*cover.split("/"))
    return _skript(datei.parent, "--replace-cover", link, "--cover", str(datei), erfolg="artwork_replaced")


def metadaten_ersetzen(link, beschreibung, tags):
    """Beschreibung und Tags des bestehenden Tracks ersetzen, nie ein neuer Upload. Leere Angaben ändern nichts."""
    if not beschreibung.strip():
        return "Die Beschreibung ist leer; bei SoundCloud wurde nichts geändert."
    tag_liste = " ".join(f'"{t}"' if " " in t else t for t in tags)
    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "beschreibung.txt"
        datei.write_text(beschreibung, encoding="utf-8")
        return _skript(ordner, "--update-metadata", link, "--description-file", str(datei),
                       *(("--tags", tag_liste) if tag_liste else ()), erfolg="metadata_updated")
