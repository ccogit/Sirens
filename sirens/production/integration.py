"""Composition root for existing production adapters; no audio/model imports."""
from pathlib import Path
from uuid import uuid4
import shutil
import tempfile

from ..config import umgebung
from ..store import write_json_atomic
from .contracts import (ContractError, read_manifest, safe_path, sha256_file,
                        validate_brief, validate_plan, validate_wav)
from .jobs import RunStore


def settings():
    path = umgebung().get("SIRENS_PRODUCTION_CONFIG")
    if not path:
        return {}
    value = read_manifest(path)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ContractError("Configure a schema_version=1 SIRENS_PRODUCTION_CONFIG file")
    return value


def plan_for(brief, mode):
    from .arrangement import clear_head_plan
    validate_brief(brief)
    if brief["title"].casefold() not in ("clear head", "clear head, broken heart"):
        raise ContractError("Supply --plan with an agent-authored validated song plan")
    if mode == "preview" and not 30 <= (brief["target_seconds"] or 0) <= 60:
        raise ContractError("Supply a 30–60 second preview brief or --plan")
    return clear_head_plan(brief)


class RealBackend:
    """Use verified local selections; generation requires an injected shared-lease stage.

    Deliberately no Runner whole-stage cache identity: K04/K03 cache after checking
    source rights, patch metadata and worker revisions.
    """
    require_technical_pass = True

    def __init__(self, cfg, options=None, *, asset_stage=None):
        self.options = settings() if options is None else options
        self.store = RunStore(cfg)
        self.asset_stage = asset_stage

    def assets(self, brief, plan, root, cancelled):
        from .assets import AssetStage, Worker, local_candidate
        if self.asset_stage is not None:
            return self.asset_stage.assets(brief, plan, root, cancelled)
        options = self.options
        selections = options.get("assets", {})

        def resolve(request):
            selected = selections.get(request["id"])
            if selected is None:
                return None
            return local_candidate(options["asset_root"], selected["file"],
                                   selected["source"], selected.get("measured"))

        def factory(check):
            return Worker(options["asset_python"], cancelled=check)

        stage = AssetStage(resolve=resolve,
                           worker_factory=factory if options.get("asset_python") else None,
                           cache_dir=self.store.root)
        return stage.assets(brief, plan, root, cancelled)

    def stems(self, plan, assets, root, cancelled):
        from .instruments import WBWorker, render_stems
        options = self.options
        backend = None
        if any(t["backend"] == "instrument" for t in plan["tracks"]):
            if not all(options.get(key) for key in
                       ("instrument_python", "amm_backend", "instrument_revision", "patches")):
                raise ContractError("Configure the verified local instrument worker and patches")
            backend = WBWorker(options["instrument_python"], options["amm_backend"],
                               options["instrument_revision"])
        return render_stems(plan, assets, root, patches=options.get("patches", {}),
                            backend=backend, cache_dir=self.store.root, cancelled=cancelled)

    def mix(self, plan, stems, root, cancelled):
        from .mixing import mix
        options = self.options
        return mix(plan, stems, root, cancelled, ffmpeg=options.get("ffmpeg"),
                   worker_python=options.get("mix_python"), amm_python=options.get("amm_python"),
                   amm_root=options.get("amm_root"))

    def report(self, brief, plan, assets, stems, mix, root, cancelled):
        from .quality import inspect_run, mastering_analyzer
        cancelled()
        options = self.options
        analyzer = None
        if options.get("analysis_python") and options.get("analysis_root"):
            analyzer = mastering_analyzer(options["analysis_python"], options["analysis_root"])
        result = inspect_run(root, analyzer)
        cancelled()
        return result


def references(cfg, brief, options=None):
    from .references import collect, build_references, validate_references
    options = settings() if options is None else options
    validate_brief(brief)
    projection = read_manifest(options["amm_export"]) if options.get("amm_export") else None
    tracks, coverage = collect(cfg, amm_export=projection)
    result = build_references(tracks, coverage, brief)
    validate_references(result)
    return result


def successful_run(store, run_id):
    root = store.get(run_id)
    if store.inspect(run_id)["status"] != "succeeded":
        raise ContractError("Select a successful run")
    return root


def export_master(store, run_id, destination, options=None):
    """Explicit archive export, never overwrite a previous version."""
    options = settings() if options is None else options
    root = successful_run(store, run_id)
    source = safe_path(root, "master.wav")
    validate_wav(source)
    if not options.get("export_root"):
        raise ContractError("Configure export_root")
    approved = Path(options["export_root"]).resolve(strict=True)
    folder = safe_path(approved, destination)
    folder.mkdir(parents=True, exist_ok=True)
    export_id = uuid4().hex
    target = safe_path(folder, export_id)
    digest = sha256_file(source)
    with tempfile.TemporaryDirectory(prefix=".export-", dir=folder) as pending:
        stage = Path(pending)
        shutil.copyfile(source, stage / "master.wav")
        if sha256_file(stage / "master.wav") != digest:
            raise ContractError("Source changed; inspect run before exporting again")
        receipt = dict(schema_version=1, run_id=run_id, export_id=export_id,
                       file="master.wav", sha256=digest, commercial_clearance=False)
        write_json_atomic(stage / "export.json", receipt)
        # UUID namespace and exclusive directory creation; never replace an existing version.
        target.mkdir()
        try:
            for name in ("master.wav", "export.json"):
                (stage / name).rename(target / name)
        except BaseException:
            shutil.rmtree(target)
            raise
    return receipt


def ableton_root(store):
    root = safe_path(store.root, "ableton")
    root.mkdir(exist_ok=True)
    return root


def export_ableton(store, run_id, options=None, *, midi_writer=None):
    from .ableton import export_bundle, wb_writer
    options = settings() if options is None else options
    root = successful_run(store, run_id)
    if midi_writer is None and options.get("amm_checkout"):
        midi_writer = wb_writer(options["amm_checkout"])
    return export_bundle(root, ableton_root(store), run_id, midi_writer=midi_writer)


def import_ableton(store, export_id, confirm):
    from .ableton import import_return
    from .quality import measure_wav
    receipt = import_return(ableton_root(store), export_id, store.runs, confirm=confirm)
    run_id = receipt["run_id"]
    root = store.get(run_id)
    store.status(run_id, "running", "ableton_return", 0)
    try:
        technical = measure_wav(safe_path(root, "master.wav"))
        errors = ["clipping"] if technical["clipped_samples"] else []
        report = dict(schema_version=1, technical={"master": technical, "errors": errors},
                      music={}, production={}, gates={}, missing=["listening", "LUFS / true peak"],
                      provenance={"source": "ableton_return"},
                      listening={"blind_pairs": [], "results": []})
        write_json_atomic(root / "report.json", report)
        store.status(run_id, "failed" if errors else "succeeded", "ableton_return", 1,
                     error="clipping" if errors else None)
    except Exception:
        store.status(run_id, "failed", "ableton_return", error="Inspect returned WAV")
    return store.inspect(run_id)
