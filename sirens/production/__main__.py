"""Production CLI. Real adapters are wired by the integration chain (P08)."""
import argparse
import json
import sys

from ..config import load, umgebung
from .contracts import ContractError, read_manifest, validate_plan
from .jobs import RunStore
from .runner import Runner
from . import integration


def parser():
    p = argparse.ArgumentParser(prog="python -m sirens.production")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory")
    sub.add_parser("references").add_argument("--brief", required=True)
    sub.add_parser("validate").add_argument("--plan", required=True)
    render = sub.add_parser("render")
    render.add_argument("--brief", required=True)
    render.add_argument("--plan")
    render.add_argument("--mode", choices=("preview", "full"), required=True)
    for name in ("inspect", "cancel", "resume", "revise", "export"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--run", required=True)
        if name == "revise":
            cmd.add_argument("--plan", required=True)
        if name in ("resume", "revise"):
            cmd.add_argument("--mode", choices=("preview", "full"), default="full")
        if name == "export":
            cmd.add_argument("--destination", required=True)
    sub.add_parser("benchmark").add_argument("--manifest", required=True)
    ab = sub.add_parser("ableton").add_subparsers(dest="ableton_action", required=True)
    ab.add_parser("probe")
    ab.add_parser("export").add_argument("--run", required=True)
    imp = ab.add_parser("import")
    imp.add_argument("--export", required=True)
    imp.add_argument("--confirm", action="store_true", required=True)
    return p


def main(argv=None, *, cfg=None, backend=None):
    args = parser().parse_args(argv)
    cfg = load(umgebung()) if cfg is None else cfg
    try:
        if args.action == "inventory":
            options = integration.settings()
            result = {"schema_version": 1, "music_root_available": cfg.music_root.is_dir(),
                      "data_dir_available": cfg.data_dir.is_dir(),
                      "render_available": True if backend is not None else None,
                      "configured": bool(options),
                      "gpu_available": None, "ableton_available": None}
            if cfg.music_root.is_dir():
                from .references import collect
                projection = read_manifest(options["amm_export"]) if options.get("amm_export") else None
                _, coverage = collect(cfg, amm_export=projection)
                result["references"] = coverage
        elif args.action == "references":
            result = integration.references(cfg, read_manifest(args.brief), options=integration.settings())
        elif args.action == "benchmark":
            from .quality import benchmark, configured_analyzer
            result = benchmark(args.manifest, analyzer=configured_analyzer(integration.settings()))
        elif args.action == "validate":
            validate_plan(read_manifest(args.plan))
            result = {"schema_version": 1, "valid": True}
        elif args.action == "inspect":
            result = RunStore(cfg).inspect(args.run)
        elif args.action == "cancel":
            RunStore(cfg).cancel(args.run)
            result = {"schema_version": 1, "cancel_requested": True}
        elif args.action in ("render", "revise", "resume"):
            runner = Runner(cfg, backend if backend is not None else integration.RealBackend(cfg))
            if args.action == "render":
                brief = read_manifest(args.brief)
                plan = read_manifest(args.plan) if args.plan else integration.plan_for(brief, args.mode)
                result = runner.render(brief, plan, args.mode)
            elif args.action == "revise":
                result = runner.revise(args.run, read_manifest(args.plan), args.mode)
            else:
                result = runner.resume(args.run, args.mode)
        elif args.action == "export":
            result = integration.export_master(RunStore(cfg), args.run, args.destination)
        elif args.action == "ableton":
            if args.ableton_action == "probe":
                from .ableton import probe
                result = probe()
            elif args.ableton_action == "export":
                result = integration.export_ableton(RunStore(cfg), args.run)
            else:
                result = integration.import_ableton(RunStore(cfg), args.export, args.confirm)
        else:
            raise ContractError("adapter unavailable; integration P08")
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 1 if result.get("status") in ("failed", "cancelled") else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"schema_version": 1, "error": type(exc).__name__, "message": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
