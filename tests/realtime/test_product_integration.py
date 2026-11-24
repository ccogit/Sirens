"""Sitzungsgebundene Export-Quellen, ohne GPU und ohne Modell."""
from dataclasses import replace
from types import SimpleNamespace
from threading import RLock
from pathlib import Path
from tempfile import TemporaryDirectory
import wave
import struct
from sirens.realtime.sessions import Sources
from sirens.contracts import Ablehnung
from unittest.mock import patch

from hilfe import ServerFall


class ProductIntegration(ServerFall):
    def test_export_source_requires_feature_and_loaded_session(self):
        sid = "a" * 32
        aid = "b" * 32
        path = f"/api/rt/v1/sessions/{sid}/export-source"
        self.assertEqual(self.http("GET", path)[0], 503)
        self.server.app.cfg = replace(self.cfg, rt_enabled=True)
        sources = SimpleNamespace(lock=RLock(), digests={aid: "c" * 64})
        session = SimpleNamespace(lock=RLock(), asset={"id": aid},
                                  data={"state": "loading"},
                                  manager=SimpleNamespace(sources=sources, recordings=None))
        service = SimpleNamespace(get=lambda _: session)
        with patch("sirens.realtime.routes.service", return_value=service):
            self.assertEqual(self.http("GET", path)[0], 503)
            session.data["state"] = "ready"
            status, body, _ = self.http("GET", path)
            self.assertEqual(status, 200)
            self.assertEqual(body, {"asset_id": aid, "sha256": "c" * 64})
            self.assertEqual(self.http("GET", path, headers={"Origin": "https://example.invalid"})[0], 403)
            sources.digests.clear()
            self.assertEqual(self.http("GET", path)[0], 503)

    def test_cached_stem_only_via_legacy_resolver(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            data, music = root / "data", root / "music"
            data.mkdir()
            music.mkdir()
            path = data / "vocals.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
                wav.writeframes(struct.pack("<h", 8192) * 441)
            cfg = SimpleNamespace(data_dir=data, music_root=music, realtime_dir=data / "rt")
            sources = Sources(cfg)
            requests = []

            def resolve(*args):
                requests.append(args)
                return path

            stems = SimpleNamespace(audiodatei=resolve)
            meta = sources.register_stem(stems, "song.wav", "htdemucs", "vocals")
            raw = sources.load(meta["id"])
            self.assertEqual(meta["sample_rate"], 48000)
            self.assertEqual(len(raw), meta["nframes"] * 8)
            self.assertEqual(struct.unpack_from("<ff", raw), (0.25, 0.25))
            self.assertEqual(requests, [("song.wav", "htdemucs", "vocals")] * 2)
            outside = SimpleNamespace(audiodatei=lambda *args: root / "outside.wav")
            with self.assertRaises(Ablehnung):
                sources.register_stem(outside, "song.wav", "htdemucs", "vocals")
