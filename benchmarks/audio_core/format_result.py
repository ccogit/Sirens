"""Browser-Rohmessung in das gemeinsame Ergebnisformat übertragen."""
import argparse
import json
import math
from pathlib import Path

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write


def convert(raw, machine, latencies=()):
    duration = raw["elapsed_seconds"]
    underruns = raw["underruns"]
    if (type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0
            or type(underruns) is not int or underruns < 0
            or type(raw["completed"]) is not bool
            or any(type(raw[k]) is not int or raw[k] < 0 for k in ("skipped_blocks", "interruptions"))):
        raise ValueError("Rohmessung ungültig")
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in latencies):
        raise ValueError("Latenz ungültig")
    values = dict.fromkeys(METRICS)
    values["underruns"] = underruns
    samples = sorted(latencies)
    for key, q in (("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99)):
        if samples:
            values[key] = samples[max(0, math.ceil(q * len(samples)) - 1)]
    return {
        "wp": "WP04", "kandidat": "Browser AudioWorklet, synthetischer Gain-Mock",
        "zeitpunkt": raw["zeitpunkt"], "rechner": machine,
        "befehl": "python -m benchmarks.audio_core.serve --port 8766; Browser: Messung starten",
        "gate": "nicht_gemessen", "modus": "unbekannt",
        "messwerte": {"warm": values, "kalt": dict.fromkeys(METRICS)},
        "notizen": [
            f"Browser-Soak: {duration:.2f} s, vollständig: {raw['completed']}, "
            f"übersprungene Blöcke: {raw['skipped_blocks']}, Unterbrechungen: {raw['interruptions']}.",
            f"Context-Rate: {raw['sample_rate']} Hz; Browser-Schätzwerte baseLatency "
            f"{raw['base_latency_ms']} ms, outputLatency {raw['output_latency_ms']} ms (keine Gerätemessung).",
            ("Latenzperzentile: extern gemessene Loopback-Roundtrip-Zeiten, keine Einweglatenz."
             if samples else "Geräte-Latenz: nicht gemessen."),
            "Kein G2-Nachweis: Mock im Browser, kein integrierter Worker/Sidecar-Pfad."
        ]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("raw", type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--latency-ms", type=float, action="append", default=[])
    args = p.parse_args()
    write(args.out, convert(json.loads(args.raw.read_text(encoding="utf-8")), collect(), args.latency_ms))


if __name__ == "__main__":
    main()
