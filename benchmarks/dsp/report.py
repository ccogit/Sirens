"""Lokale WP09-Messdaten in das gemeinsame Ergebnisformat überführen."""
import argparse
import datetime
import json
import math
from pathlib import Path
from benchmarks import baseline, result


def quantiles(values):
    values = sorted(values)
    return {name: values[math.ceil(q * len(values)) - 1] if values else None
            for name, q in (("p50_ms", .5), ("p95_ms", .95), ("p99_ms", .99))}


def nonnegative(value):
    if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
        raise ValueError("Ungültige Messstichprobe")
    return value


def breakdown(data):
    """Nur gepaarte, gültige Schätzungen für die Sirens-Kennzahl verwenden."""
    total = [nonnegative(v) for v in data["control_ms"]]
    series = {key: [] for key in ("sirens_ms", "base_latency_ms", "output_latency_ms",
                                 "rack_latency_ms", "message_ms",
                                 "received_to_first_ms", "first_to_90_ms")}
    samples = data.get("control_samples", [])
    if "control_samples" in data and [s["total_ms"] for s in samples] != total:
        raise ValueError("Gesamtlatenz und Stichproben passen nicht zusammen")
    for sample in samples:
        for key in ("rack_latency_ms", "received_to_first_ms", "first_to_90_ms"):
            series[key].append(nonnegative(sample[key]))
        for key in ("base_latency_ms", "output_latency_ms"):
            if sample[key] is not None:
                series[key].append(nonnegative(sample[key]))
        base, output = sample["base_latency_ms"], sample["output_latency_ms"]
        if base is None or output is None:
            continue
        own = sample["total_ms"] - base - output
        # Zeitstempel und Gerätedaten sind Schätzungen. Inkonsistente
        # Stichproben nicht durch Nullsetzen künstlich beschönigen.
        message = own - sample["received_to_first_ms"] - sample["first_to_90_ms"]
        if own >= 0:
            series["sirens_ms"].append(own)
        if message >= 0:
            series["message_ms"].append(message)
    return {"total_ms": quantiles(total),
            **{key: quantiles(values) for key, values in series.items()},
            "samples_total": len(total), "samples_sirens": len(series["sirens_ms"]),
            "samples_message": len(series["message_ms"])}


def build(data, machine):
    if data["backend"] != "cpu" or data["profile"] not in ("fast", "standard", "detail"):
        raise ValueError("Unbekannter Messpfad")
    if data["stems"] not in (1, 2, 4, 8):
        raise ValueError("Spurzahl")
    metrics = {phase: dict.fromkeys(result.METRICS) for phase in ("kalt", "warm")}
    notes = ["CPU-Referenz; GPU nicht gemessen; Gate erst nach Geräte-/Hörtest entscheiden."]
    latency = None
    if "control_ms" in data:
        latency = breakdown(data)
        metrics["warm"].update(latency["sirens_ms"])
        notes += [
            f"Browser Control-to-audio (Ausgabezeitstempel, kein physischer Loopback), n={latency['samples_total']}.",
            f"Gesamtlatenz p50/p95/p99 (ms): {latency['total_ms']}.",
            f"Sirens ohne baseLatency + outputLatency (ms): {latency['sirens_ms']}; n={latency['samples_sirens']}.",
            f"Gerät: baseLatency={latency['base_latency_ms']}; outputLatency={latency['output_latency_ms']} (ms).",
            f"Rack (deklarierte Signallaufzeit): {latency['rack_latency_ms']} ms; nicht nochmals addieren.",
            f"Nachrichtenweg (Restschätzung): {latency['message_ms']} ms; n={latency['samples_message']}.",
            f"Empfang bis 1 Prozent: {latency['received_to_first_ms']} ms; 1 bis 90 Prozent: {latency['first_to_90_ms']} ms.",
            f"Impuls: {data['impulse']}; Timeouts: {data['timeouts']}; Geräteunderruns nicht gemessen.",
            f"Render-Ack-Stichprobe n={len(data['render_ack_ms'])}; Ausgabezeit und Gerätelatenz geschätzt.",
        ]
        if latency["samples_sirens"] != latency["samples_total"]:
            notes.append("Fehlende oder inkonsistente Gerätedaten: keine Sirens-Kennzahl für diese Stichproben.")
        if not data.get("control_samples"):
            notes.append("Altmessung: erste messbare Änderung statt 90 Prozent; keine Sirens-Kennzahl ableitbar.")
    else:
        for phase in metrics:
            for key in ("p50_ms", "p95_ms", "p99_ms", "rtf"):
                metrics[phase][key] = data[phase][key]
        notes += [f"Node-Rechenzeit je {data['frames']} Frames bei {data['rate']} Hz; keine Audioausgabe.",
                  f"Deklarierte Zusatzlatenz: {data['latency_frames']} Frames."]
    report = {"wp": "WP09", "kandidat": f"CPU {data['profile']} {data['stems']} Stems",
        "gate": "nicht_gemessen", "modus": "unbekannt", "zeitpunkt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rechner": machine, "messwerte": metrics, "notizen": notes,
        "befehl": "Siehe benchmarks/dsp/README.md (Browser- oder Node-Pfad)"}
    if latency is not None:
        report["latency_breakdown"] = latency
    return result.validate(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result.write(args.output, build(data, baseline.collect()))


if __name__ == "__main__":
    main()
