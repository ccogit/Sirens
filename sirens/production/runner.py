"""Backend-neutral, synchronous production orchestration.

The caller provides stage adapters (lazy, no model imports); CLI never silently
selects the synthetic test backend. Render results must already exist under run.
"""
from .contracts import (ContractError, expected_frames, read_manifest, safe_path,
                        validate_assets, validate_brief, validate_mix_report,
                        validate_plan, validate_report, validate_stems, validate_wav)
from .jobs import Cancelled, RunStore
from .cache import HashCache, cache_key
from ..store import write_json_atomic


class Runner:
    def __init__(self, cfg, backend):
        self.store = RunStore(cfg)
        self.backend = backend
        self.cache = HashCache(self.store.root)

    def render(self, brief, plan, mode="full", *, parent=None, run_id=None,
               additional_cancel=lambda: None):
        validate_brief(brief)
        validate_plan(plan)
        if mode not in ("preview", "full"):
            raise ContractError("invalid mode")
        if run_id is None:
            run_id, root = self.store.create(parent)
        else:
            root = self.store.get(run_id)
            state = self.store.inspect(run_id)
            if state["status"] not in ("queued", "running") or state["parent_run_id"] != parent:
                raise ContractError("invalid prepared run")
        stage = "prepare"

        def checkpoint(name, progress):
            nonlocal stage
            stage = name
            cancelled()
            self.store.status(run_id, "running", name, progress)

        def manifest(name, result, validator, **kwargs):
            validator(result, **kwargs)
            write_json_atomic(safe_path(root, name + ".json"), result)
            return result

        def cancelled():
            additional_cancel()
            self.store.check_cancel(run_id)

        def cached_stage(name, inputs, compute, validator, **kwargs):
            # Opt-in only for adapters declaring stable backend identity/revision.
            backend_name = getattr(self.backend, "name", None)
            revision = getattr(self.backend, "revision", None)
            if not isinstance(backend_name, str) or not isinstance(revision, str):
                return manifest(name, compute(), validator, **kwargs)
            key = cache_key(name, inputs, backend_name, revision, plan["seed"])
            if self.cache.restore(key, root):
                return validator(read_manifest(safe_path(root, name + ".json")), **kwargs)
            result = manifest(name, compute(), validator, **kwargs)
            items = result[name]
            if any(item.get("error") is not None for item in items):
                return result
            self.cache.publish(key, root, [name + ".json", *(item["file"] for item in items)])
            return result

        def independent_stems(assets):
            """Opt-in adapter guarantees each track depends only on declared inputs."""
            from .contracts import SAMPLE_RATE
            items = []
            for track in plan["tracks"]:
                cancelled()
                dependencies = {event["asset_id"] for event in track["events"] if "asset_id" in event}
                selected = [item for item in assets["assets"] if item["id"] in dependencies]
                timeline = {key: plan[key] for key in ("bpm", "meter", "ppq", "total_bars", "tail_seconds", "key")}
                inputs = {"track": track, "timeline": timeline, "assets": selected, "mode": mode}
                key = cache_key("stem", inputs, self.backend.name, self.backend.revision, plan["seed"])
                entry_path = "track_cache/" + track["id"] + ".json"
                if self.cache.restore(key, root):
                    item = read_manifest(safe_path(root, entry_path))
                else:
                    item = self.backend.stem(plan, assets, track, root, cancelled)
                    validate_stems({"schema_version": 1, "sample_rate": SAMPLE_RATE,
                                    "frames": expected_frames(plan), "stems": [item]}, root=root)
                    if item["track_id"] != track["id"]:
                        raise ContractError("track ID mismatch")
                    target = safe_path(root, entry_path)
                    target.parent.mkdir(exist_ok=True)
                    write_json_atomic(target, item)
                    self.cache.publish(key, root, [entry_path, item["file"]])
                items.append(item)
            return {"schema_version": 1, "sample_rate": SAMPLE_RATE,
                    "frames": expected_frames(plan), "stems": items}

        try:
            # Persist inputs before checking cancellation so a cancelled run can resume.
            manifest("brief", brief, validate_brief)
            manifest("plan", plan, validate_plan)
            write_json_atomic(root / "run.json", {"schema_version": 1, "mode": mode,
                                                   "seed": plan["seed"], "parent_run_id": parent,
                                                   "backend": getattr(self.backend, "name", None),
                                                   "revision": getattr(self.backend, "revision", None)})
            checkpoint("prepare", 0)
            checkpoint("assets", 0.2)
            assets = cached_stage("assets", {"brief": brief, "plan": plan, "mode": mode},
                                  lambda: self.backend.assets(brief, plan, root, cancelled),
                                  validate_assets, plan=plan, root=root)
            if any(a.get("error") is not None for a in assets["assets"]):
                raise ContractError("asset generation failed")
            checkpoint("stems", 0.4)
            if (getattr(self.backend, "independent_tracks", False) is True
                    and isinstance(getattr(self.backend, "name", None), str)
                    and isinstance(getattr(self.backend, "revision", None), str)):
                stems = manifest("stems", independent_stems(assets), validate_stems, plan=plan, root=root)
            else:
                stems = cached_stage("stems", {"plan": plan, "assets": assets, "mode": mode},
                                     lambda: self.backend.stems(plan, assets, root, cancelled),
                                     validate_stems, plan=plan, root=root)
            checkpoint("mix", 0.6)
            mix = self.backend.mix(plan, stems, root, cancelled)
            for name in ("mix.wav", "master.wav"):
                validate_wav(safe_path(root, name), frames=expected_frames(plan))
            manifest("mix_report", mix, validate_mix_report)
            checkpoint("report", 0.8)
            report = manifest("report", self.backend.report(brief, plan, assets, stems, mix, root, cancelled),
                              validate_report)
            if (getattr(self.backend, "require_technical_pass", False) is True
                    and report["technical"].get("errors")):
                raise ContractError("Inspect technical errors in report.json")
            cancelled()
            self.store.status(run_id, "succeeded", "complete", 1)
        except Cancelled:
            self.store.status(run_id, "cancelled", stage, error=None)
        except Exception as exc:
            # Never persist arbitrary exception text (could contain private paths or secrets).
            action = getattr(self.backend, "next_action", None)
            self.store.status(run_id, "failed", stage,
                              error={"type": type(exc).__name__, "next_action": action(stage)}
                              if callable(action) else type(exc).__name__)
        return self.store.inspect(run_id)

    def revise(self, run_id, plan, mode="full"):
        old = self.store.get(run_id)
        if self.store.inspect(run_id)["status"] != "succeeded":
            raise ContractError("revision requires a successful parent")
        brief = read_manifest(safe_path(old, "brief.json"))
        return self.render(brief, plan, mode, parent=run_id)

    def resume(self, run_id, mode="full"):
        old = self.store.get(run_id)
        if self.store.inspect(run_id)["status"] not in ("failed", "cancelled"):
            raise ContractError("resume requires failed or cancelled parent")
        brief = read_manifest(safe_path(old, "brief.json"))
        plan = read_manifest(safe_path(old, "plan.json"))
        return self.render(brief, plan, mode, parent=run_id)


class LocalServices:
    """Read-only facade for the existing SecondRoom and WB endpoints.

    No Live writer, generation retry, download, database or own service.
    The transport is injectable for offline tests. Local service writes are
    intentionally left to authorized K04/K07/P08 adapters.
    """
    def __init__(self, secondroom_port=8099, wb_port=8000, *, transport=None):
        for port in (secondroom_port, wb_port):
            if type(port) is not int or not 1 <= port <= 65535:
                raise ContractError("invalid local service port")
        self.secondroom_port = secondroom_port
        self.wb_port = wb_port
        self.transport = transport or self._get

    @staticmethod
    def _get(port, path):
        import http.client
        import json
        # Direct loopback HTTP: no proxy, redirects, credentials or user URLs.
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request("GET", path, headers={"Accept": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise ContractError("local service rejected read")
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ContractError("local service response too large")
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, (dict, list)):
                raise ContractError("invalid local service response")
            return value
        except (OSError, UnicodeError, ValueError, http.client.HTTPException) as exc:
            raise ContractError("local service unavailable") from exc
        finally:
            connection.close()

    def status(self):
        return self.transport(self.secondroom_port, "/api/status")

    def guard(self):
        return self.transport(self.wb_port, "/api/live-delivery/guard")

    def chain(self, role):
        if role not in ("vocals", "drums", "bass", "synths", "bus", "plate", "delay", "master"):
            raise ContractError("invalid chain role")
        return self.transport(self.secondroom_port, "/api/chains/" + role)

    def job(self, job_id):
        import re
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", job_id):
            raise ContractError("invalid delivery job ID")
        return self.transport(self.secondroom_port, "/api/jobs/" + job_id)
