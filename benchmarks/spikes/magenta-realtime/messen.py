"""Messpfad für Magenta RealTime 2; keine Fremdimporte im Dry-Run."""
from benchmarks.spikes import runner


def main(argv=None):
    args = runner.parser("magenta-realtime").parse_args(argv)
    if args.dry_run:
        return runner.run("magenta-realtime", "offline", None, argv)
    raise SystemExit("Echte Inferenz noch nicht eingerichtet; siehe BERICHT.md")


if __name__ == "__main__":
    raise SystemExit(main())
