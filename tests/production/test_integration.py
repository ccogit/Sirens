"""Offline tests of the K08 composition root."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sirens.config import Config
from sirens.production import integration
from sirens.production.contracts import ContractError
from sirens.production.jobs import RunStore


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cfg = Config(music_root=root / "music", data_dir=root / "data")

    def test_dispatch_without_whole_stage_cache(self):
        backend = integration.RealBackend(self.cfg, {})
        self.assertFalse(hasattr(backend, "revision"))
        with patch("sirens.production.mixing.mix", return_value={"ok": True}) as mix:
            self.assertEqual(backend.mix({}, {}, self.cfg.data_dir, lambda: None), {"ok": True})
            mix.assert_called_once()

    def test_unfinished_or_invalid_run_cannot_export(self):
        store = RunStore(self.cfg)
        run_id, _ = store.create()
        for value in (run_id, "../outside"):
            with self.assertRaises(ContractError):
                integration.export_master(store, value, "song", {})

    def test_missing_instrument_configuration(self):
        backend = integration.RealBackend(self.cfg, {})
        with self.assertRaises(ContractError):
            backend.stems({"tracks": [{"backend": "instrument"}]}, {}, self.cfg.data_dir, lambda: None)
