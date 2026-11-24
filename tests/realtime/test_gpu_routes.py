from dataclasses import replace
from unittest.mock import patch

from hilfe import ServerFall
from sirens.realtime.schema import validate
from sirens.realtime.telemetry import Telemetry


class GPURoutes(ServerFall):
    def test_gpu_without_gpu_and_flag(self):
        with patch("sirens.realtime.routes.read_gpu", return_value=Telemetry()):
            self.assertEqual(self.http("GET", "/api/rt/v1/gpu")[0], 503)
            self.server.app.cfg = replace(self.cfg, rt_enabled=True)
            status, body, _ = self.http("GET", "/api/rt/v1/gpu")
            self.assertEqual(status, 200)
            validate("telemetry", body)
            self.assertFalse(body["available"])
            self.assertEqual(self.http("GET", "/api/rt/v1/gpu",
                             headers={"Origin": "https://example.invalid"})[0], 403)

    def test_registry(self):
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)
        status, body, _ = self.http("GET", "/api/rt/v1/capabilities")
        self.assertEqual(status, 200)
        validate("capabilities", body)
        self.assertTrue(body["capabilities"][0]["mock"])
