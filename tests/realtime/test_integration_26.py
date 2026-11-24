"""WP17: durchgehender HTTP-Referenzpfad mit synthetischen Cache-Stems."""
from dataclasses import replace
import hashlib
import struct
import time
import urllib.request
import wave
from unittest.mock import patch

from hilfe import ServerFall
from sirens.stems import MODELLE


class ProductFlow26(ServerFall):
    PREFIX = "/api/rt/v1/"

    def request(self, method, route, body=None, expected=200):
        code, value, _ = self.http(method, self.PREFIX + route, body)
        self.assertEqual(code, expected, value)
        return value

    def command(self, session, name, args=None):
        return self.request("POST", "sessions/" + session["id"] + "/commands",
                            {"command": name, "args": args or {}, "epoch": session["epoch"],
                             "seq": 0 if session["seq"] is None else session["seq"] + 1})

    @staticmethod
    def wav(path):
        with wave.open(str(path), "wb") as out:
            out.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
            out.writeframes(struct.pack("<hh", 8192, -4096) * 1024)

    def test_cache_stem_pad_record_export_stop(self):
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)
        rel = "test/fixture.wav"
        original = self.cfg.music_root / rel
        original.parent.mkdir()
        self.wav(original)
        before = hashlib.sha256(original.read_bytes()).hexdigest()
        _, cache = self.server.app.stems._eingabe(rel, "htdemucs")
        cache.mkdir(parents=True)
        for stem in MODELLE["htdemucs"]:
            self.wav(cache / (stem + ".wav"))
        (cache / ".ready").write_text("htdemucs", encoding="utf-8")
        asset = self.request("POST", "assets/cached-stem",
                             {"pfad": rel, "modell": "htdemucs", "stem": "drums"}, 201)
        s = self.request("POST", "sessions", {"capability_id": "mock", "sample_rate": 48000}, 201)
        endpoint = "sessions/" + s["id"]
        self.command(s, "load", {"asset_id": asset["id"]})
        deadline = time.monotonic() + 12
        while True:
            s = self.request("GET", endpoint)
            if s["state"] == "ready":
                break
            self.assertNotIn(s["state"], ("closed", "error"), s)
            self.assertLess(time.monotonic(), deadline, s)
            time.sleep(.05)
        self.assertEqual(self.http("GET", self.PREFIX + endpoint + "/dry", roh=True)[1][:8],
                         struct.pack("<ff", .25, -.125))
        s = self.command(s, "play")
        s = self.command(s, "set_param", {"name": "gain", "value": .5})
        s = self.command(s, "bypass", {"enabled": False})
        rec = self.request("POST", endpoint + "/recordings",
                           {"name": "mock", "sample_rate": 48000}, 201)
        recording = endpoint + "/recordings/" + rec["id"]
        req = urllib.request.Request(self.basis + self.PREFIX + recording + "/blocks/0",
                                     data=struct.pack("<ff", .125, -.0625) * 256,
                                     method="PUT", headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
        finished = self.request("POST", recording + "/close", {})
        self.assertEqual(finished["next_frame"], 256)
        source = self.request("GET", endpoint + "/export-source")
        self.assertEqual(source["asset_id"], asset["id"])
        value = {"version": 1, "sample_rate": 48000, "sources": [source],
                 "models": [{"name": "mock", "version": "mock-v1"}],
                 "presets": [{"name": "A/B", "version": "1"}],
                 "parameters": [{"name": "gain", "value": .5}],
                 "seeds": [], "timeline": [],
                 "assets": [entry["id"] for entry in finished["assets"]]}
        exported = self.request("POST", endpoint + "/exports", value, 201)
        self.assertEqual(self.request("GET", endpoint + "/exports/" + exported["id"]), value)
        instance = self.server.app.rt_sessions.get(s["id"])
        worker = instance.worker.worker.process
        sidecar = instance.sidecar.process
        self.assertEqual(self.request("POST", endpoint + "/close", {})["state"], "closed")
        self.assertIsNotNone(worker.poll())
        self.assertIsNotNone(sidecar.poll())
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), before)

    def test_legacy_cuda_sperre_bleibt_bis_zur_gpu_freigabe(self):
        with patch.object(self.server.app.starter, "zustand", return_value={"laeuft": True}), \
             patch.object(self.server.app.stems, "starten") as start:
            for enabled in (False, True):
                self.server.app.cfg = replace(self.cfg, rt_enabled=enabled)
                status, body, _ = self.http("POST", "/api/stems",
                                            {"pfad": "fixture.wav", "device": "cuda"})
                self.assertEqual(status, 409, body)
                self.assertEqual(body["error"], "busy_gpu")
            start.assert_not_called()

    def test_profile_flag_origin_and_manager(self):
        path = "profile"
        self.request("GET", path, expected=503)
        self.server.app.cfg = replace(self.cfg, rt_enabled=True, rt_mock=True)
        self.assertEqual(self.request("GET", path), {"profile": "Performance"})
        self.assertIsNone(getattr(self.server.app, "rt_sessions", None))
        self.request("POST", path, {"profile": []}, 400)
        self.assertEqual(self.http("POST", self.PREFIX + path, {"profile": "Neural"},
                                   headers={"Origin": "https://example.invalid"})[0], 403)
        for name in ("Eco", "Neural", "Training/Render", "Performance"):
            self.assertEqual(self.request("POST", path, {"profile": name}), {"profile": name})
            self.assertEqual(self.request("GET", path), {"profile": name})
            self.assertEqual(self.server.app.rt_sessions.gpu.profile, name)
