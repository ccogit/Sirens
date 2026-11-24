"""Read existing AMM/WB inventories in the configured worker, no installs."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amm-backend", required=True)
    parser.add_argument("--inventory-dir", required=True)
    parser.add_argument("--plugin", action="append", default=[],
                        help="WB relative plugin reference, from existing catalog")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.amm_backend).resolve(strict=True)))
    from app.production.plugin_inventory import read_inventory
    from app.audio_engine.factory_presets import list_presets
    from app.audio_engine.sample_instruments import list_instruments
    result = {"inventory": read_inventory(Path(args.inventory_dir)),
              "presets": {name: list_presets(name) for name in args.plugin},
              "sample_instruments": list_instruments(),
              "host_compatibility": None, "license_approval": None}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
