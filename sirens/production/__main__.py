"""Production CLI. Real adapters are wired by the integration chain (P08)."""
import argparse
import json
import sys

from ..config import load, umgebung
from .contracts import ContractError, read_manifest, validate_plan
from .jobs import RunStore
from .runner import Runner


def parser():
    p = argparse.ArgumentParser(prog="python -m sirens.production")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory")
    sub.add_parser("references").add_argument("--brief", required=True)
    sub.add_parser("validate").add_argument("--plan", required=True)
    render = sub.add_parser("render")
    render.add_argument("--brief", required=True)
    render.add_argument("--plan", required=True)
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
            result = {"schema_version": 1, "music_root_available": cfg.music_root.is_dir(),
                      "data_dir_available": cfg.data_dir.is_dir(), "render_available": backend is not None,
                      "gpu_available": None, "ableton_available": None}
        elif args.action == "validate":
            validate_plan(read_manifest(args.plan))
            result = {"schema_version": 1, "valid": True}
        elif args.action == "inspect":
            result = RunStore(cfg).inspect(args.run)
        elif args.action == "cancel":
            RunStore(cfg).cancel(args.run)
            result = {"schema_version": 1, "cancel_requested": True}
        elif args.action in ("render", "revise", "resume"):
            if backend is None:
                raise ContractError("real production adapter unavailable; no synthetic fallback")
            runner = Runner(cfg, backend)
            if args.action == "render":
                result = runner.render(read_manifest(args.brief), read_manifest(args.plan), args.mode)
            elif args.action == "revise":
                result = runner.revise(args.run, read_manifest(args.plan), args.mode)
            else:
                result = runner.resume(args.run, args.mode)
        elif args.action == "ableton" and args.ableton_action == "probe":
            result = {"schema_version": 1, "available": False, "reason": "adapter not connected"}
        else:
            raise ContractError("adapter unavailable; integration P08")
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 1 if result.get("status") in ("failed", "cancelled") else 0
    except (ContractError, OSError) as exc:
        print(json.dumps({"schema_version": 1, "error": type(exc).__name__, "message": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
