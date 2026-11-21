"""Claude-Start aus der Seite: mit einem Ersatzbefehl, ohne echtes Claude Code."""
import dataclasses
import sys
import unittest

from hilfe import ServerFall, TIDY1

from sirens.starter import SATZ, ClaudeStarter

MERKER = "import sys, pathlib; pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())"


class StarterTest(ServerFall):
    def ersatz(self, an=True):
        self.merker = self.tmp / "gestartet.txt"
        cfg = dataclasses.replace(self.cfg, claude_start=an)
        starter = ClaudeStarter(cfg, cmd=[sys.executable, "-c", MERKER, str(self.merker)], cwd=self.tmp)
        self.server.app.starter = starter
        return starter

    def auftrag(self):
        wunsch = {"weg": "beschreibung", "umfang": "song", "artist_slug": "cco", "wunsch": "Ein Funk-Song."}
        order = self.http("POST", "/api/auftraege", wunsch)[1]
        return order["id"], order["revision"]

    def test_abschicken_startet_claude_mit_dem_satz(self):
        starter = self.ersatz()
        oid, revision = self.auftrag()
        status, order, _ = self.http("POST", f"/api/auftraege/{oid}/abschicken", {"revision": revision})
        self.assertEqual(status, 200)
        self.assertIn("claude", order)
        self.assertTrue(starter.warten())
        self.assertEqual(self.merker.read_text(encoding="utf-8"), SATZ)
        zustand = self.http("GET", "/api/claude")[1]
        self.assertEqual((zustand["aktiv"], zustand["laeuft"], zustand["letzter"]["exit_code"]), (True, False, 0))
        self.assertEqual(len(list((self.cfg.data_dir / "claude-laeufe").glob("*.log"))), 1)

    def test_abgeschaltet_startet_nichts(self):
        starter = self.ersatz(an=False)
        oid, revision = self.auftrag()
        self.http("POST", f"/api/auftraege/{oid}/abschicken", {"revision": revision})
        self.assertEqual(self.http("POST", "/api/claude/start", {})[0], 202)
        self.assertTrue(starter.warten())
        self.assertFalse(self.merker.exists())
        self.assertFalse(self.http("GET", "/api/claude")[1]["aktiv"])

    def test_knopf_startet_und_fehlender_befehl_wird_gemeldet(self):
        starter = self.ersatz()
        self.assertEqual(self.http("POST", "/api/claude/start", {})[0], 202)
        self.assertTrue(starter.warten())
        self.assertTrue(self.merker.exists())
        starter.cmd = [str(self.tmp / "gibt-es-nicht.exe")]
        self.http("POST", "/api/claude/start", {})
        self.assertTrue(self.http("GET", "/api/claude")[1]["letzter"]["fehler"])


if __name__ == "__main__":
    unittest.main()
