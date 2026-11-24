"""Operator-only pilot; no downloads, no Live mutation, no committed audio.

Run from Sirens checkout using the standard Python interpreter. The worker
interpreter must have the existing AMM/WB dependencies installed separately.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sirens.production.instruments import WBWorker, render_stems

ROLES = {"tight_kick": "drums", "mono_sub": "bass",
         "mechanical_funk_bass": "bass", "metallic_hook": "synths",
         "percussion": "drums", "mandolin": "instruments", "cello": "instruments"}


def plan(variant):
    tracks = []
    for patch, role in ROLES.items():
        events = []
        for bar in range(16):
            base = bar*3840
            if patch == "tight_kick":
                notes = [(i*960, 120, 36, 112) for i in range(4)]
            elif patch == "mono_sub":
                notes = [(i*960+240, 560, 38 if bar%4 != 3 else 41, 91) for i in range(4)]
            elif patch == "mechanical_funk_bass":
                notes = [(i*960 + (240 if i%2 else 480), 180+variant*60,
                          (50, 53, 57, 48)[(i+variant+bar//4)%4], 90+i*3) for i in range(4)]
            elif patch == "metallic_hook":
                notes = [(360+variant*120, 210, 74, 90), (2160, 300, 69+variant, 80)]
            elif patch == "percussion":
                notes = [(i*480+120+(variant*15 if i%2 else 0), 90, 42, 74+i*4) for i in range(8)]
            elif patch == "mandolin":
                notes = [(1440, 360, 65, 80), (2880, 360, 69, 74)] if bar%4 == 2 else []
            else:
                notes = [(0, 1920, 50, 78)] if bar%4 == 3 else []
            events.extend({"tick": base+t, "duration_ticks": d, "note": n, "velocity": v}
                          for t,d,n,v in notes)
        tracks.append({"id": patch, "role": role, "backend": "instrument",
                       "patch": patch, "events": events, "automation": []})
    return {"schema_version": 1, "seed": 101+variant, "bpm": 126, "key": "D minor",
            "meter": [4, 4], "ppq": 960, "total_bars": 16, "tail_seconds": 2,
            "sections": [{"id": "groove", "start_bar": 0, "bars": 16, "intent": "pilot"}],
            "tracks": tracks, "asset_requests": [],
            "mix": {"target_lufs": None, "ceiling_dbtp": -1}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker-python", required=True)
    p.add_argument("--amm-backend", required=True)
    p.add_argument("--revision", required=True, help="Actual AMM/host/plugin versions")
    p.add_argument("--patches", type=Path, required=True,
                   help="Local JSON array of three semantic patch mapping objects")
    p.add_argument("--output", type=Path, required=True, help="Fresh local output outside git")
    args = p.parse_args()
    patches = json.loads(args.patches.read_text(encoding="utf-8"))
    if len(patches) != 3 or any(set(ROLES)-set(x) for x in patches):
        p.error("Three complete, locally verified patch maps required")
    presets = {json.dumps(x["mechanical_funk_bass"]["instrument"], sort_keys=True) for x in patches}
    if len(presets) != 3:
        p.error("Provide three distinct bass preset/state bindings")
    args.output.mkdir(parents=True, exist_ok=False)
    backend = WBWorker(args.worker_python, args.amm_backend, args.revision)
    for variant in range(3):
        run = args.output / ("variant-" + str(variant+1))
        run.mkdir()
        song = plan(variant)
        (run/"plan.json").write_text(json.dumps(song, indent=2), encoding="utf-8")
        result = render_stems(song, {"schema_version": 1, "assets": []}, run,
                              patches=patches[variant], backend=backend,
                              cache_dir=args.output/"cache")
        print(json.dumps({"variant": variant+1, "frames": result["frames"],
                          "sample_rate": result["sample_rate"], "stems": result["stems"]}))


if __name__ == "__main__":
    main()
