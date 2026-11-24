"""WP01: Verträge, Schemata, PCM, Mock und HTTP ohne GPU."""
import ast
import json
import struct
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from hilfe import ServerFall
from sirens.config import load
from sirens.contracts import Ablehnung
from sirens.realtime import contracts as c, pcm
from sirens.realtime.mock import MockAdapter
from sirens.realtime.schemas import SCHEMAS, validate

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs/realtime/examples"
EXAMPLE = json.loads((EXAMPLES / "json.json").read_text(encoding="utf-8"))

class Schemas(unittest.TestCase):
    def test_all_examples(self):
        self.assertEqual(set(EXAMPLE["schemas"]), {p.name.split(".")[0] for p in SCHEMAS.glob("*.schema.json")})
        for name, sample in EXAMPLE["schemas"].items():
            with self.subTest(name=name):
                validate(name, sample["valid"])
                with self.assertRaises(Ablehnung):
                    validate(name, sample["invalid"])
        for endpoint in EXAMPLE["http"]:
            with self.subTest(path=endpoint["path"], method=endpoint["method"]):
                validate(endpoint["request_schema"], endpoint["request"])
                validate(endpoint["response_schema"], endpoint["response"])
        self.assertEqual(len(EXAMPLE["http"]), 9)
        self.assertEqual(MockAdapter().probe(), EXAMPLE["schemas"]["capability"]["valid"])

    def test_invalid_fields(self):
        for name, key, value in (("capability", "channels", 1), ("session", "epoch", True),
                                 ("command", "command", "shell"), ("asset", "id", "../a"),
                                 ("beatgrid", "confidence", 1.1), ("telemetry", "queue_depth", -1)):
            with self.subTest(name=name):
                with self.assertRaises(Ablehnung):
                    validate(name, {**EXAMPLE["schemas"][name]["valid"], key: value})

class Contracts(unittest.TestCase):
    def test_transitions(self):
        expected_session = {"created": ["loading","stopping","error"], "loading": ["ready","stopping","error"],
                            "ready": ["playing","stopping","error"], "playing": ["paused","stopping","error"],
                            "paused": ["playing","stopping","error"], "stopping": ["closed","error"],
                            "error": ["stopping"], "closed": []}
        expected_job = {"queued": ["running","cancelled","error"], "running": ["ready","error","cancelled"],
                        "ready": [], "error": [], "cancelled": []}
        for table, expected in ((c.SESSION_TRANSITIONS, expected_session), (c.JOB_TRANSITIONS, expected_job)):
            self.assertEqual(set(table), set(expected))
            for src in expected:
                for dst in [*expected, "unknown"]:
                    with self.subTest(src=src, dst=dst):
                        if dst in expected[src]:
                            self.assertEqual(c.transition(table, src, dst), dst)
                        else:
                            with self.assertRaises(Ablehnung):
                                c.transition(table, src, dst)

    def test_commands(self):
        command = EXAMPLE["schemas"]["command"]["valid"]
        self.assertEqual(c.validate_command(command, 0), command)
        for sample, epoch, seq, code in ((command,1,-1,"stale_epoch"),
                                        ({**command,"command":"unknown"},0,-1,"invalid"),
                                        (command,0,0,"invalid"),
                                        ({**command,"args":[]},0,-1,"invalid")):
            with self.assertRaises(Ablehnung) as exc:
                c.validate_command(sample, epoch, seq)
            self.assertEqual(exc.exception.code, code)
        for name,args in (("play",{}),("pause",{}),("seek",{"source_frame":5}),
                          ("set_param",{"name":"gain","value":0.5}),("bypass",{"enabled":True}),
                          ("schedule",{"output_frame":256,"command":{"command":"play","args":{}}})):
            sample = {"command":name,"args":args,"epoch":0,"seq":1}
            validate("command",sample)
            c.validate_command(sample,0,0)

    def test_paths_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            identifier = c.new_id()
            self.assertEqual(c.cache_path(root, "sessions", identifier), root / "sessions" / identifier)
            for bad in ("../bad", "a/b", "C:\\bad"):
                with self.assertRaises(Ablehnung):
                    c.cache_path(root, "cache", bad)
            with self.assertRaises(Ablehnung):
                c.source_path(root, "../bad.wav")
        self.assertFalse(load({}).rt_enabled)
        cfg = load({"SIRENS_RT_ENABLED":"an","SIRENS_RT_DIR":"rt","SIRENS_RT_MOCK":"1"})
        self.assertTrue(cfg.rt_enabled and cfg.rt_mock)
        self.assertEqual(cfg.realtime_dir, Path("rt"))

    def test_stdlib_imports_recursively(self):
        legacy_workers = {"kick_dsp": {"numpy", "scipy", "soundfile"},
                          "stem_transcribe": {"basic_pitch"}}
        for path in (ROOT / "sirens").rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    module = name.split(".")[0]
                    # Zwei unveränderte Bestands-CLIs laufen nur als Unterprozess.
                    if path.parent == ROOT / "sirens" and module in legacy_workers.get(path.stem, ()):
                        continue
                    self.assertIn(module, sys.stdlib_module_names | {"sirens"}, str(path))
                    self.assertFalse(any(name == f"sirens.{worker}" or name.startswith(f"sirens.{worker}.")
                                         or name == worker for worker in legacy_workers), str(path))
                if isinstance(node, ast.ImportFrom) and (node.level or node.module == "sirens"):
                    self.assertNotIn(node.module, legacy_workers, str(path))
                    self.assertTrue(set(alias.name for alias in node.names).isdisjoint(legacy_workers), str(path))

class PCM(unittest.TestCase):
    def test_fixtures_and_roundtrip(self):
        for name, stream, seq, start, rate, samples in (
            ("pcm-python.hex",7,3,9007199254740993,48000,(0.5,-0.25)),
            ("pcm-js.hex",8,4,9007199254740994,44100,(-0.25,0.5))):
            block = bytes.fromhex((EXAMPLES / name).read_text())
            h = {"protocol_version":1,"stream_id":stream,"epoch":2,"seq":seq,"start_frame":start,
                 "nframes":256,"channels":2,"sample_rate":rate,"flags":0}
            payload = struct.pack("<ff", *samples) * 256
            self.assertEqual(pcm.pack(h,payload),block)
            self.assertEqual(pcm.unpack(block),(h,payload))
            self.assertEqual(pcm.pack(*pcm.unpack(block)), block)

    def test_invalid(self):
        block = bytes.fromhex((EXAMPLES / "pcm-python.hex").read_text())
        for offset, value in ((0,2),(26,1),(24,0),(25,9),(27,1)):
            mutated = bytearray(block)
            mutated[offset] = value
            if offset == 24:
                mutated[25] = 0
            with self.assertRaises(Ablehnung):
                pcm.unpack(mutated)
        for bad in (block[:-1],block[:31],block+b"\x00"):
            with self.assertRaises(Ablehnung):
                pcm.unpack(bad)

class Mock(unittest.TestCase):
    def test_gain_delay(self):
        def run():
            adapter = MockAdapter()
            adapter.load(gain=0.5,delay_frames=1)
            adapter.warmup()
            result = adapter.process([1,-1])+adapter.process([0.5,-0.5,0,0])
            adapter.cancel()
            with self.assertRaises(Ablehnung):
                adapter.process([0,0])
            adapter.unload()
            self.assertFalse(adapter.health()["loaded"])
            return result
        self.assertEqual(run(),[0,0,0.5,-0.5,0.25,-0.25])
        self.assertEqual(run(),run())

class HTTP(ServerFall):
    def test_switch_and_security(self):
        path = "/api/rt/v1/capabilities"
        status, body, _ = self.http("GET",path)
        self.assertEqual((status,body["error"]),(503,"unavailable"))
        validate("error",body)
        self.server.app.cfg = replace(self.cfg,rt_enabled=True)
        status, body, _ = self.http("GET",path)
        # Ohne installierte Worker: echte Modelle stehen nur als nicht verfügbar da, kein Mock.
        self.assertEqual((status,body["protocol_version"]),(200,1))
        self.assertTrue(all(not c["mock"] and not c["available"] for c in body["capabilities"]))
        validate("capabilities",body)
        self.server.app.cfg = replace(self.cfg,rt_enabled=True,rt_mock=True)
        status, body, _ = self.http("GET",path)
        # Mock eingeschaltet: das Beispiel aus den Verträgen steht vorn, nicht installierte echte Worker folgen.
        beispiel = EXAMPLE["schemas"]["capabilities"]["valid"]
        self.assertEqual((status,body["protocol_version"]),(200,beispiel["protocol_version"]))
        mocks = [c for c in body["capabilities"] if c["mock"]]
        self.assertEqual(mocks, beispiel["capabilities"])
        self.assertTrue(all(not c["available"] for c in body["capabilities"] if not c["mock"]))
        validate("capabilities",body)
        for headers, code in (({"Origin":"https://example.invalid"},"forbidden_origin"),
                              ({"Host":"example.invalid"},"forbidden_host")):
            for method, endpoint, data in (("GET",path,None),("POST","/api/rt/v1/sessions",{})):
                status,body,_ = self.http(method,endpoint,data,headers=headers)
                self.assertEqual((status,body["error"]),(403,code))
        status, body = self.http("GET","/api/rt/v1/gpu")[:2]
        self.assertEqual(status, 200)
        validate("telemetry", body)
        # WP06 implementiert sessions: leerer Body verletzt session_create.
        status, body, _ = self.http("POST", "/api/rt/v1/sessions", {})
        self.assertEqual((status, body["error"]), (400, "invalid"))
        self.assertEqual(self.http("GET","/api/health")[1]["status"],"ok")
        self.assertEqual(self.http("GET","/api/unbekannt")[0],404)
