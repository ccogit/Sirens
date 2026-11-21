"""Seite: Dateien vollständig, ohne externe Quellen, Logik als reine Funktionen (Node-Test, falls Node vorhanden)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


class Seite(unittest.TestCase):
    def test_keine_externen_quellen_und_importe_vorhanden(self):
        for datei in list(WEB.rglob("*.js")) + list(WEB.rglob("*.html")) + list(WEB.rglob("*.css")):
            text = datei.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"https?://|@import|url\(", text), datei.name)
            for ziel in re.findall(r'from "(\./[^"]+)"', text):
                self.assertTrue((datei.parent / ziel).is_file(), f"{datei.name}: {ziel}")
        logik = (WEB / "js" / "logic.js").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b(document|window|fetch|localStorage)\b|^import ", logik, re.M))

    def test_dateien_unter_400_zeilen(self):
        for datei in ROOT.rglob("*"):
            if datei.suffix in (".py", ".js", ".mjs", ".css", ".html", ".md", ".ps1", ".json") and "__pycache__" not in datei.parts:
                zeilen = len(datei.read_text(encoding="utf-8").splitlines())
                self.assertLess(zeilen, 400, datei.name)

    def test_keine_fremden_importe(self):
        for datei in (ROOT / "sirens").glob("*.py"):
            for modul in re.findall(r"^(?:from|import) ([\w.]+)", datei.read_text(encoding="utf-8"), re.M):
                self.assertNotIn(modul.split(".")[0], ("app", "requests", "psycopg", "psycopg2", "fastapi"), datei.name)

    @unittest.skipUnless(shutil.which("node"), "Node ist nicht installiert")
    def test_javascript_module_syntax(self):
        """Auch Änderungen an reinen DOM-Modulen müssen syntaktisch gültig sein."""
        for datei in (WEB / "js").glob("*.js"):
            lauf = subprocess.run(
                ["node", "--input-type=module", "--check"],
                input=datei.read_text(encoding="utf-8"),
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
            )
            self.assertEqual(lauf.returncode, 0, f"{datei.name}: {lauf.stderr}")

    @unittest.skipUnless(shutil.which("node"), "Node ist nicht installiert")
    def test_logik_mit_node(self):
        lauf = subprocess.run(["node", "--test", str(ROOT / "tests" / "logic.test.mjs")], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)


if __name__ == "__main__":
    unittest.main()
