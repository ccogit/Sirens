"""Backend-neutral, synchronous production orchestration.

The caller provides stage adapters (lazy, no model imports); CLI never silently
selects the synthetic test backend. Render results must already exist under run.
"""
from .contracts import (ContractError, expected_frames, read_manifest, safe_path,
                        validate_assets, validate_brief, validate_mix_report,
                        validate_plan, validate_report, validate_stems, validate_wav)
from .jobs import Cancelled, RunStore
from ..store import write_json_atomic


class Runner:
    def __init__(self, cfg, backend):
        self.store = RunStore(cfg)
        self.backend = backend

    def render(self, brief, plan, mode="full", *, parent=None):
        validate_brief(brief)
        validate_plan(plan)
        if mode not in ("preview", "full"):
            raise ContractError("invalid mode")
        run_id, root = self.store.create(parent)
        stage = "prepare"

        def checkpoint(name, progress):
            nonlocal stage
            stage = name
            self.store.check_cancel(run_id)
            self.store.status(run_id, "running", name, progress)

        def manifest(name, result, validator, **kwargs):
            validator(result, **kwargs)
            write_json_atomic(safe_path(root, name + ".json"), result)
            return result

        def cancelled():
            self.store.check_cancel(run_id)

        try:
            checkpoint("prepare", 0)
            manifest("brief", brief, validate_brief)
            manifest("plan", plan, validate_plan)
            checkpoint("assets", 0.2)
            assets = manifest("assets", self.backend.assets(brief, plan, root, cancelled),
                              validate_assets, plan=plan, root=root)
            if any(a.get("error") is not None for a in assets["assets"]):
                raise ContractError("asset generation failed")
            checkpoint("stems", 0.4)
            stems = manifest("stems", self.backend.stems(plan, assets, root, cancelled),
                             validate_stems, plan=plan, root=root)
            checkpoint("mix", 0.6)
            mix = self.backend.mix(plan, stems, root, cancelled)
            for name in ("mix.wav", "master.wav"):
                validate_wav(safe_path(root, name), frames=expected_frames(plan))
            manifest("mix_report", mix, validate_mix_report)
            checkpoint("report", 0.8)
            manifest("report", self.backend.report(brief, plan, assets, stems, mix, root, cancelled),
                     validate_report)
            cancelled()
            self.store.status(run_id, "succeeded", "complete", 1)
        except Cancelled:
            self.store.status(run_id, "cancelled", stage, error=None)
        except Exception as exc:
            # Never persist arbitrary exception text (could contain private paths or secrets).
            self.store.status(run_id, "failed", stage, error=type(exc).__name__)
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
