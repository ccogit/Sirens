"""Sitzungsgebundene Export-Quellen, ohne GPU und ohne Modell."""
from dataclasses import replace
from types import SimpleNamespace
from threading import RLock
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
