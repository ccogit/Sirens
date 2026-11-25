"""`sirens serve --port` ändert nur den Port; Echtzeit-, Mock- und Claude-Einstellungen bleiben erhalten."""
import io
import unittest
from unittest import mock

from sirens import cli


class ServePort(unittest.TestCase):
    def test_port_behaelt_uebrige_einstellungen(self):
        env = {"SIRENS_RT_ENABLED": "an", "SIRENS_RT_MOCK": "an", "SIRENS_CLAUDE": "an",
               "SIRENS_RT_RESERVE_BYTES": "123"}
        gesehen = {}
        with mock.patch("sirens.server.serve", side_effect=lambda cfg: gesehen.setdefault("cfg", cfg)):
            cli.main(["serve", "--port", "8095"], env=env, out=io.StringIO())
        cfg = gesehen["cfg"]
        self.assertEqual(cfg.port, 8095)
        self.assertTrue(cfg.rt_enabled)
        self.assertTrue(cfg.rt_mock)
        self.assertTrue(cfg.claude_start)
        self.assertEqual(cfg.rt_reserve_bytes, 123)


if __name__ == "__main__":
    unittest.main()
