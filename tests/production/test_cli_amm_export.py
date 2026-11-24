import contextlib
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from sirens.config import Config
from sirens.production.__main__ import main


class CliAmmExportTests(unittest.TestCase):
    def test_inventory_and_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = Config(root / "music", root / "data")
            folder = cfg.music_root / "electro/funk"
            folder.mkdir(parents=True)
            cfg.orders_dir.mkdir(parents=True)
            with wave.open(str(folder / "Alpha - Version 1.wav"), "wb") as wav:
                wav.setparams((1, 2, 8000, 0, "NONE", ""))
                wav.writeframes(b"\x01\x00" * 800)
            projection = root / "export.json"
            projection.write_text(json.dumps({"schema_version": 1, "songs": [
                {"artist_slug": "electro", "release_slug": "funk", "title": "Alpha",
                 "version": 1, "style_prompt": "fixture", "song_evaluations": []}]}), encoding="utf-8")
            config = root / "production.json"
            config.write_text(json.dumps({"schema_version": 1, "amm_export": str(projection)}), encoding="utf-8")
            brief = root / "brief.json"
            brief.write_text(json.dumps({"schema_version": 1, "title": "Test", "style": "electro",
                "negative_tags": [], "lyrics": None, "bpm": 126, "key": None,
                "target_seconds": 30, "seed": 1, "reference_ids": [], "vocal_mode": None}), encoding="utf-8")
            with patch.dict("os.environ", {"SIRENS_PRODUCTION_CONFIG": str(config)}):
                for argv in (["inventory"], ["references", "--brief", str(brief)]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(argv, cfg=cfg), 0)
                    result = json.loads(output.getvalue())
                    coverage = result["references"] if argv[0] == "inventory" else result["profile"]["coverage"]
                    self.assertEqual(coverage["with_prompts"], 1)
                    self.assertNotIn("amm_export", coverage["missing_sources"])
