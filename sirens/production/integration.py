"""Composition root for existing production adapters; no audio/model imports."""
from pathlib import Path
from uuid import uuid4
import shutil
import tempfile
import threading


from ..config import umgebung
from ..store import write_json_atomic
from .contracts import (ContractError, read_manifest, safe_path, sha256_file,
                        validate_brief, validate_plan, validate_wav)
from .jobs import Cancelled, RunStore


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

    @staticmethod
    def next_action(stage):
        return {"assets": "Prüfe die freigegebenen Quellen und asset_provenance.json.",
                "stems": "Prüfe die lokale Instrument-/Patch-Konfiguration.",
                "mix": "Prüfe die lokale Mix-Worker-/ffmpeg-Konfiguration.",
                "report": "Prüfe report.json und die technische Messkonfiguration."}.get(
                    stage, "Prüfe Brief und Plan.")

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


class ProductionService:
    """Local Signal Room job facade; uses Runner rather than a second pipeline."""

    def __init__(self, cfg, *, backend_factory=None, options_factory=settings):
        self.cfg = cfg
        self.backend_factory = backend_factory or (lambda cfg, options: RealBackend(cfg, options))
        self.options_factory = options_factory
        self.lock = threading.Lock()
        self.active = None

    @property
    def store(self):
        return RunStore(self.cfg)

    def status(self, run_id):
        store = self.store
        result = dict(store.inspect(run_id))
        if result["status"] == "succeeded":
            root = successful_run(store, run_id)
            validate_wav(safe_path(root, "master.wav"))
            report = read_manifest(safe_path(root, "report.json"))
            from .contracts import validate_report
            validate_report(report)
            if report["technical"].get("errors"):
                raise ContractError("Technical report contains errors")
            result.update(validated=True, audio_url="/api/production/v1/audio?run=" + run_id,
                          report=report)
        return result

    @staticmethod
    def _validate(brief, plan, preview=False):
        from .arrangement import validate_arrangement
        from .contracts import expected_frames
        validate_arrangement(brief, plan)
        if preview and not 30 <= expected_frames(plan) / 48000 <= 60:
            raise ContractError("Provide a validated 30–60 second preview plan")

    def start(self, request):
        if not isinstance(request, dict):
            raise ContractError("Provide a production request")
        options = self.options_factory()
        mode = request.get("mode", "full")
        if mode not in ("full", "preview"):
            raise ContractError("Invalid production mode")
        # A trusted operator can configure a prepared pilot for the simple UI.
        # Arbitrary prompts cannot be converted to a plan by the K02 lighthouse recipe.
        if "brief" not in request:
            pilot = options.get("pilot")
            if not isinstance(pilot, dict):
                raise ContractError("Configure a local prepared pilot brief and plans")
            prompt = request.get("prompt", "")
            if not isinstance(prompt, str):
                raise ContractError("Provide a text prompt")
            brief = pilot.get("brief", {})
            if prompt.strip() and prompt.strip() not in (brief.get("title"), brief.get("style")):
                raise ContractError("Provide an agent-authored plan for this new prompt")
            request = {**pilot, "mode": mode}
        if mode == "preview":
            brief, plan = request.get("preview_brief"), request.get("preview_plan")
            if brief is None:
                brief, plan = request.get("brief"), request.get("plan")
            self._validate(brief, plan, preview=True)
            return self._submit(brief, plan, mode, options)
        brief, plan = request.get("brief"), request.get("plan")
        preview_brief, preview_plan = request.get("preview_brief"), request.get("preview_plan")
        self._validate(brief, plan)
        self._validate(preview_brief, preview_plan, preview=True)
        if any(preview_brief[k] != brief[k] for k in ("title", "seed", "bpm", "key")):
            raise ContractError("Preview must belong to the same song and seed")
        return self._submit(brief, plan, mode, options, preview=(preview_brief, preview_plan))

    def revise(self, request):
        if not isinstance(request, dict):
            raise ContractError("Provide a revision request")
        parent = request.get("run")
        root = successful_run(self.store, parent)
        brief = read_manifest(safe_path(root, "brief.json"))
        options = self.options_factory()
        plan = request.get("plan")
        text = request.get("text", "")
        if plan is None:
            if not isinstance(text, str):
                raise ContractError("Provide revision text")
            # A configured agent result maps an exact requested revision to a new plan.
            plan = options.get("revisions", {}).get(text.strip())
            if plan is None:
                raise ContractError("Provide an agent-authored revision plan for this request")
        if not isinstance(plan, dict) or "seed" not in plan:
            raise ContractError("Provide a valid revision plan")
        brief = dict(brief, seed=plan["seed"])
        self._validate(brief, plan)
        return self._submit(brief, plan, "full", options, parent=parent)

    def _submit(self, brief, plan, mode, options, *, parent=None, preview=None):
        from .runner import Runner
        with self.lock:
            if self.active is not None:
                raise ContractError("Wait for or cancel the active production job")
            store = self.store
            runner = Runner(self.cfg, self.backend_factory(self.cfg, options))
            run_id, root = store.create(parent)
            write_json_atomic(root / "brief.json", brief)
            write_json_atomic(root / "plan.json", plan)
            self.active = run_id

            def work():
                def check():
                    store.check_cancel(run_id)
                try:
                    if preview is not None:
                        check()
                        store.status(run_id, "running", "preview", 0)
                        result = runner.render(*preview, "preview", additional_cancel=check)
                        check()
                        if result["status"] != "succeeded":
                            store.status(run_id, "failed", "preview",
                                         error={"preview_run_id": result["run_id"],
                                                "next_action": "Prüfe den Preview-Status."})
                            return
                        write_json_atomic(root / "preview.json", {"schema_version": 1,
                                          "run_id": result["run_id"]})
                    runner.render(brief, plan, mode, parent=parent, run_id=run_id)
                except Cancelled:
                    store.status(run_id, "cancelled", "prepare")
                except Exception as exc:
                    if store.inspect(run_id)["status"] in ("queued", "running"):
                        store.status(run_id, "failed", "prepare", error=type(exc).__name__)
                finally:
                    with self.lock:
                        self.active = None

            try:
                threading.Thread(target=work, name="sirens-production", daemon=True).start()
            except Exception:
                self.active = None
                store.status(run_id, "failed", "prepare", error="Worker start failed")
                raise
        return {"schema_version": 1, "run_id": run_id, "status": "queued"}

    def cancel(self, run_id):
        self.store.cancel(run_id)
        return {"schema_version": 1, "run_id": run_id, "cancel_requested": True}

    def audio(self, run_id):
        root = successful_run(self.store, run_id)
        path = safe_path(root, "master.wav")
        validate_wav(path)
        return path

    def export(self, run_id):
        result = export_ableton(self.store, run_id, self.options_factory())
        return {**result, "validated": True,
                "instructions": "IMPORT.md im lokalen Exportordner lesen; WAV/MIDI ab 1.1.1, Warp aus."}

    def check_return(self, export_id):
        from .contracts import validate_ableton, validate_return
        root = ableton_root(self.store)
        exported = safe_path(root, export_id)
        manifest = validate_ableton(read_manifest(safe_path(exported, "ableton.json")), root=exported)
        if manifest["export_id"] != export_id:
            raise ContractError("Export ID mismatch")
        inbox = safe_path(root, "return/" + export_id)
        receipt = safe_path(inbox, "return.json")
        if receipt.is_file():
            data = validate_return(read_manifest(receipt), root=inbox)
            if data["export_id"] != export_id or data["parent_run_id"] != manifest["run_id"]:
                raise ContractError("Return ID mismatch")
            path = safe_path(inbox, data["master_file"])
        elif inbox.is_dir() and {p.name for p in inbox.iterdir()} == {"master.wav"}:
            path = safe_path(inbox, "master.wav")
        else:
            return {"export_id": export_id, "validated": False}
        validate_wav(path, channels=2)
        # The final import repeats hash and stability checks before publication.
        return {"export_id": export_id, "validated": True}

    def take_return(self, export_id, confirm):
        result = import_ableton(self.store, export_id, confirm)
        return self.status(result["run_id"])


def dispatch(handler, path, query, data=None):
    """Only called after the existing loopback Host/Origin/JSON guards."""
    service = handler.app.production
    action = path.removeprefix("/api/production/v1/")
    try:
        if handler.command == "GET":
            if action == "status":
                return handler._json(200, service.status(query.get("run")))
            if action == "audio":
                return handler._senden(service.audio(query.get("run")))
            if action == "return":
                return handler._json(200, service.check_return(query.get("export")))
        if handler.command == "POST" and isinstance(data, dict):
            if action == "start":
                return handler._json(202, service.start(data))
            if action == "revise":
                return handler._json(202, service.revise(data))
            if action == "cancel":
                return handler._json(200, service.cancel(data.get("run")))
            if action == "ableton-export":
                return handler._json(200, service.export(data.get("run")))
            if action == "export":
                return handler._json(200, export_master(service.store, data.get("run"),
                                     data.get("destination"), service.options_factory()))
            if action == "ableton-import":
                return handler._json(200, service.take_return(data.get("export"), data.get("confirm")))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        # Report fixed action, not arbitrary paths/lyrics from underlying errors.
        message = str(exc) if isinstance(exc, ContractError) else "Lokale Produktionskonfiguration prüfen."
        return handler._json(400, {"error": "production", "meldung": message})
    return handler._json(404, {"error": "not_found", "meldung": "Produktionsaktion nicht verfügbar."})
