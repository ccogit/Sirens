"""Operator-only one-bar smoke render using SIRENS_PRODUCTION_CONFIG."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sirens.production.integration import settings
from sirens.production.instruments import WBWorker, render_stems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Fresh directory outside Git")
    parser.add_argument("--patch", default="tight_kick", help="Verified local semantic patch ID")
    args = parser.parse_args()
    options = settings()
    backend = WBWorker(options["instrument_python"], options["amm_backend"],
                       options["instrument_revision"], wb_data_dir=options.get("wb_data_dir"))
    song = {"schema_version": 1, "seed": 101, "bpm": 126, "key": None,
            "meter": [4, 4], "ppq": 960, "total_bars": 1, "tail_seconds": 0,
            "sections": [{"id": "smoke", "start_bar": 0, "bars": 1, "intent": "smoke"}],
            "tracks": [{"id": "smoke", "role": "drums", "backend": "instrument",
                        "patch": args.patch, "events": [
                            {"tick": i * 960, "duration_ticks": 120, "note": 36, "velocity": 100}
                            for i in range(4)], "automation": []}],
            "asset_requests": [], "mix": {"target_lufs": None, "ceiling_dbtp": -1}}
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    manifest = render_stems(song, {"schema_version": 1, "assets": []}, args.output,
                            patches=options["patches"], backend=backend)
    print(json.dumps({"render_seconds": time.perf_counter() - start, **manifest}))


if __name__ == "__main__":
    main()
