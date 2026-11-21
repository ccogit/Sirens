"""Pfade und Port: aus Umgebungsvariablen, sonst Standardwerte."""
import os
from dataclasses import dataclass
from pathlib import Path

LOOPBACK = "127.0.0.1"


@dataclass(frozen=True)
class Config:
    music_root: Path
    data_dir: Path
    port: int = 8093
    host: str = LOOPBACK
    claude_start: bool = False

    @property
    def orders_dir(self):
        return self.data_dir / "auftraege"

    @property
    def catalog_ratings_file(self):
        return self.data_dir / "katalog-bewertungen.json"

    @property
    def direction_words_file(self):
        return self.data_dir / "richtungswoerter.json"


def load(env=None):
    env = os.environ if env is None else env

    def wert(name, standard):
        """Einstellung SIRENS_<name>; der frühere Name SONG_AUFTRAG_<name> gilt weiter."""
        return env.get(f"SIRENS_{name}", env.get(f"SONG_AUFTRAG_{name}", standard))
    return Config(
        music_root=Path(wert("MUSIC_ROOT", r"E:\AMM\generated-music")),
        data_dir=Path(wert("DATA_DIR", r"E:\AMM\song-auftraege")),  # Ablage behält ihren Ort, auch nach der Umbenennung
        port=int(wert("PORT", "8093")),
        host=wert("HOST", LOOPBACK),
        claude_start=wert("CLAUDE", "an").strip().lower() not in ("aus", "0", "nein", "off"),
    )
