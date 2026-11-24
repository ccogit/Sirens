"""Local bridge to the existing AMM standard-library writer. No Live API."""
import json
from pathlib import Path
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: wb_midi.py AMM_TOOLS OUTPUT")
    tools = Path(sys.argv[1]).resolve(strict=True)
    sys.path.insert(0, str(tools))
    from music_sources.midi import write_midi
    document = json.load(sys.stdin)
    receipt = write_midi(document, Path(sys.argv[2]))
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
