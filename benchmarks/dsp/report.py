"""Lokale WP09-Messdaten in das gemeinsame Ergebnisformat überführen."""
import argparse
import datetime
import json
import math
from pathlib import Path
from benchmarks import baseline, result


def build(data, machine):
    if data["backend"] != "cpu" or data["profile"] not in ("fast", "standard", "detail"):
        raise ValueError("Unbekannter Messpfad")
    if data["stems"] not in (1, 2, 4, 8):
        raise ValueError("Spurzahl")
    metrics = {phase: dict.fromkeys(result.METRICS) for phase in ("kalt", "warm")}
    notes = ["CPU-Referenz; GPU nicht gemessen; Gate erst nach Geräte-/Hörtest entscheiden."]
    if "control_ms" in data:
        values = sorted(data["control_ms"])
        if any(type(v) not in (float, int) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Ungültige Messstichprobe")
        if values:
            for name, q in (("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99)):
                metrics["warm"][name] = values[math.ceil(q * len(values)) - 1]
        notes += [f"Browser Control-to-audio (Ausgabezeitstempel, kein physischer Loopback), n={len(values)}",
                  f"Impuls: {data['impulse']}; Timeouts: {data['timeouts']}; Geräteunderruns nicht gemessen.",
                  f"Render-Ack-Stichprobe n={len(data['render_ack_ms'])}; outputLatency={data['output_latency_ms']} ms."]
    else:
        for phase in metrics:
            for key in ("p50_ms", "p95_ms", "p99_ms", "rtf"):
                metrics[phase][key] = data[phase][key]
        notes += [f"Node-Rechenzeit je {data['frames']} Frames bei {data['rate']} Hz; keine Audioausgabe.",
                  f"Deklarierte Zusatzlatenz: {data['latency_frames']} Frames."]
    return result.validate({"wp": "WP09", "kandidat": f"CPU {data['profile']} {data['stems']} Stems",
        "gate": "nicht_gemessen", "modus": "unbekannt", "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rechner": machine, "messwerte": metrics, "notizen": notes,
        "befehl": "Siehe benchmarks/dsp/README.md (Browser- oder Node-Pfad)"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result.write(args.output, build(data, baseline.collect()))


if __name__ == "__main__":
    main()
