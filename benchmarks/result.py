"""Validierung und Ausgabe des gemeinsamen Benchmark-Ergebnisformats."""
import argparse
import datetime
import json
import math
from pathlib import Path

GATES = ("green", "amber", "red", "nicht_gemessen")
MODES = ("streaming", "lookahead", "offline", "unbekannt")
METRICS = ("p50_ms", "p95_ms", "p99_ms", "peak_vram_mib", "rtf", "underruns")


def validate(data: dict) -> dict:
    def required(obj, field, prefix=""):
        if not isinstance(obj, dict) or field not in obj:
            raise ValueError(f"Pflichtfeld fehlt: {prefix}{field}")
        return obj[field]

    for field in ("wp", "kandidat", "zeitpunkt", "befehl"):
        value = required(data, field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field}: nichtleerer Text erwartet")
    for field, choices in (("gate", GATES), ("modus", MODES)):
        if required(data, field) not in choices:
            raise ValueError(f"{field}: unbekannter Wert, erlaubt: {', '.join(choices)}")
    try:
        stamp = datetime.datetime.fromisoformat(data["zeitpunkt"])
        if stamp.utcoffset() is None or "T" not in data["zeitpunkt"]:
            raise ValueError
    except ValueError:
        raise ValueError("zeitpunkt: ISO-8601 mit Zeitzone erwartet") from None
    machine = required(data, "rechner")
    if not isinstance(machine, dict):
        raise ValueError("rechner: Baseline-Objekt erwartet")
    for field in ("os", "python", "node", "ffmpeg", "gpus", "wsl", "disk", "git", "notes"):
        required(machine, field, "rechner.")
    notes = required(data, "notizen")
    if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
        raise ValueError("notizen: Liste aus Texten erwartet")
    measurements = required(data, "messwerte")
    for phase in ("warm", "kalt"):
        values = required(measurements, phase, "messwerte.")
        for metric in METRICS:
            value = required(values, metric, f"messwerte.{phase}.")
            if value is None:
                continue
            if type(value) not in (float, int) or value < 0 or not math.isfinite(value):
                raise ValueError(f"{phase}.{metric}: nichtnegative endliche Zahl oder null erwartet")
            if metric == "underruns" and type(value) is not int:
                raise ValueError(f"{phase}.{metric}: ganze Zahl erwartet")
        quantiles = [values[m] for m in METRICS[:3] if values[m] is not None]
        if quantiles != sorted(quantiles):
            raise ValueError(f"{phase}: Perzentile sind nicht aufsteigend")
    return data


def write(path: Path, data: dict) -> None:
    validate(data)
    content = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read(path: Path) -> dict:
    return validate(json.loads(path.read_text(encoding="utf-8")))


def markdown(data: dict) -> str:
    validate(data)
    def cell(value):
        return "nicht gemessen" if value is None else str(value).replace("|", "\\|").replace("\n", " ")
    lines = [f"# {data['wp']}: {data['kandidat']}", "",
             f"Gate: {data['gate']}; Modus: {data['modus']}; Zeitpunkt: {data['zeitpunkt']}", "",
             "| Messwert | Kalt | Warm |", "|---|---:|---:|"]
    for metric in METRICS:
        lines.append(f"| {metric} | {cell(data['messwerte']['kalt'][metric])} | {cell(data['messwerte']['warm'][metric])} |")
    lines.extend(["", "## Rechner", "", "    " + json.dumps(data["rechner"], ensure_ascii=False),
                  "", "## Nachstellen", "", "    " + data["befehl"].replace("\n", "\n    "), "", "## Notizen", ""])
    lines.extend(f"- {n}" for n in data["notizen"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datei", type=Path)
    parser.add_argument("--markdown", type=Path, help="Markdown-Bericht schreiben")
    args = parser.parse_args()
    try:
        data = read(args.datei)
        if args.markdown:
            args.markdown.write_text(markdown(data), encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Ergebnis ungültig: {error}\n")
    print("Ergebnis gültig")


if __name__ == "__main__":
    main()
