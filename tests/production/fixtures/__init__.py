"""Deterministic PCM24 test fixtures; generated only in temporary directories."""
import json
import random
import wave
from pathlib import Path
from sirens.store import write_json_atomic
from sirens.production.contracts import expected_frames, sha256_file, tick_to_sample

HERE = Path(__file__).parent


def load(name):
    return json.loads((HERE / (name + ".json")).read_text(encoding="utf-8"))


def wav(path, frames, seed, channels=1, offset=0, duration=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    duration = frames - offset if duration is None else duration
    data = bytearray()
    for i in range(frames):
        n = rng.randrange(-200000, 200001) if offset <= i < offset + duration else 0
        data.extend(n.to_bytes(3, "little", signed=True) * channels)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((channels, 3, 48000, frames, "NONE", "not compressed"))
        stream.writeframes(data)
    return sha256_file(path)


def generate(root, plan=None):
    root = Path(root)
    plan = load("plan") if plan is None else plan
    frames = expected_frames(plan)
    assets = []
    for request in plan["asset_requests"]:
        file = "assets/" + request["id"] + ".wav"
        count = round(request["duration_seconds"] * 48000)
        digest = wav(root / file, count, request["seed"])
        assets.append(dict(id=request["id"], file=file, kind=request["kind"],
                           sample_rate=48000, channels=1, frames=count, sha256=digest,
                           source=dict(backend="mock", revision="1", seed=request["seed"],
                                       license="synthetic-test", use="test-only"),
                           measured=dict(bpm=None, key=None)))
    stems = []
    for index, track in enumerate(plan["tracks"]):
        file = "stems/" + track["id"] + ".wav"
        event = track["events"][0]
        start = tick_to_sample(event["tick"], plan["bpm"])
        end = tick_to_sample(event["tick"] + event["duration_ticks"], plan["bpm"])
        digest = wav(root / file, frames, plan["seed"] + index, offset=start, duration=end-start)
        stems.append(dict(track_id=track["id"], role=track["role"], file=file,
                          channels=1, sha256=digest,
                          source=dict(backend="mock", patch=track["patch"], revision="1")))
    asset_manifest = dict(schema_version=1, assets=assets)
    stem_manifest = dict(schema_version=1, sample_rate=48000, frames=frames, stems=stems)
    return asset_manifest, stem_manifest


def write_manifests(root, plan=None):
    """Populate a temporary directory with deterministic brief/plan/assets/stems."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    plan = load("plan") if plan is None else plan
    assets, stems = generate(root, plan)
    for name, value in (("brief", load("brief")), ("plan", plan),
                        ("assets", assets), ("stems", stems)):
        write_json_atomic(root / (name + ".json"), value)
    return assets, stems
