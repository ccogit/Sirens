"""Die Finder auch mit absichtlich fehlerhaften verschachtelten Dateien prüfen."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_web


@unittest.skipUnless(shutil.which("node"), "Node ist nicht installiert")
class Discovery(unittest.TestCase):
    def test_node_fehler_aus_unterordner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "tests" / "nested"
            folder.mkdir(parents=True)
            (folder / "kaputt.test.mjs").write_text("throw new Error('WP00-NODE-BELEG');\n")
            with patch.object(test_web, "ROOT", root), self.assertRaisesRegex(AssertionError, "WP00-NODE-BELEG"):
                test_web.Seite("test_logik_mit_node").test_logik_mit_node()

    def test_syntax_fehler_aus_unterordner(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            folder = web / "js" / "realtime"
            folder.mkdir(parents=True)
            (folder / "kaputt.js").write_text("export const = ;\n")
            with patch.object(test_web, "WEB", web), self.assertRaisesRegex(AssertionError, "kaputt.js"):
                test_web.Seite("test_javascript_module_syntax").test_javascript_module_syntax()
