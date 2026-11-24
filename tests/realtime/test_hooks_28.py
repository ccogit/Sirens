"""Hook-Diagnose und Mock-Lebenszyklus; keine Modelle, kein Netzwerk außer Loopback."""
from dataclasses import replace
import time

from hilfe import ServerFall


class Hooks28(ServerFall):
    prefix = "/api/rt/v1/"

    def request(self, method, path, body=None, expected=200):
        code, value, _ = self.http(method, self.prefix + path, body)
        self.assertEqual(code, expected, value)
        return value

    def test_diagnose_und_mock_verlassen(self):
        self.request("GET", "hook-status", expected=503)
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)
        self.assertEqual(self.http("GET", self.prefix + "hook-status",
                                   headers={"Origin": "https://example.invalid"})[0], 403)
        caps = {c["id"]: c for c in self.request("GET", "capabilities")["capabilities"]}
        models = self.request("GET", "hook-status")["models"]
        self.assertIn("separation", models)
        self.assertIn("stable_audio", models)
        for key, model in models.items():
            self.assertEqual(set(model), {"interpreter_present", "gate_report_present", "available"})
            self.assertEqual(model["available"], caps.get(key, {}).get("available") is True)
            self.assertTrue(all(type(value) is bool for value in model.values()))
        self.assertIsNone(getattr(self.server.app, "rt_sessions", None))
        s = self.request("POST", "sessions", {"capability_id": "mock", "sample_rate": 48000}, 201)
        endpoint = "sessions/" + s["id"]

        def command(current, name, args=None):
            return self.request("POST", endpoint + "/commands", {
                "command": name, "args": args or {}, "epoch": current["epoch"],
                "seq": 0 if current["seq"] is None else current["seq"] + 1})

        s = command(s, "load", {"asset_id": "33333333333333333333333333333333"})
        deadline = time.monotonic() + 12
        while s["state"] != "ready":
            self.assertNotIn(s["state"], ("closed", "error"), s)
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.05)
            s = self.request("GET", endpoint)
        s = command(s, "play")
        s = command(s, "bypass", {"enabled": True})
        instance = self.server.app.rt_sessions.get(s["id"])
        worker = instance.worker.worker.process
        sidecar = instance.sidecar.process
        self.assertEqual(self.request("POST", endpoint + "/close", {})["state"], "closed")
        self.assertIsNotNone(worker.poll())
        self.assertIsNotNone(sidecar.poll())
        self.request("GET", "hook-status")
        self.assertIsNotNone(worker.poll())
        self.assertIsNotNone(sidecar.poll())
