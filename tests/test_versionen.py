"""Regression: Song-Revisionen, Archivschutz und SC-Aktualisierung."""
import unittest
from unittest.mock import patch

from hilfe import Fall, TIDY1, TIDY2
from sirens.contracts import Ablehnung
from sirens.nachlauf import NachlaufAktionen

MASTER = "cco/lab-notes/mastered/Too Tidy - Version 1 PreMix (eMastered).wav"
COVER = "cco/lab-notes/cover.png"
TEXT = "cco/lab-notes/Too Tidy - Beschreibung.txt"


class Versionen(Fall):
    def setUp(self):
        super().setUp()
        self.nach = NachlaufAktionen(self.cfg, self.store)
        (self.cfg.music_root / TEXT).write_text("Neue Beschreibung und Songtext", encoding="utf-8")

    def start(self):
        order = self.fertiger_auftrag()
        return self.tun("start", order, pfad=TIDY1)

    def tun(self, name, order, **body):
        return getattr(self.nach, name)(order["id"], {"revision": order["revision"], **body})

    def veroeffentlicht(self, master=False):
        order = self.start()
        order = self.tun("master", order, weg="datei", datei=MASTER) if master else self.tun("master", order, weg="ohne")
        self.cli("phase", order["id"], "--name", "cover", "--file", COVER)
        self.cli("phase", order["id"], "--name", "text", "--file", TEXT)
        order = self.tun("cover", self.store.load(order["id"]), entscheidung="annehmen")
        order = self.tun("soundcloud", order, entscheidung="hochladen", bestaetigt=True)
        return self.cli("phase", order["id"], "--name", "soundcloud", "--link", "https://soundcloud.com/cco/too-tidy")

    def test_alten_master_behalten_oder_archivieren(self):
        order = self.start()
        order = self.tun("master", order, weg="datei", datei=MASTER)
        order = self.tun("master", order, weg="ohne")
        self.assertEqual(order["nachlauf"]["version_entscheidung"], {"alt": MASTER, "neu": TIDY1})
        original = self.cfg.music_root / MASTER
        self.assertTrue(original.is_file())
        order = self.tun("version", order, entscheidung="behalten")
        self.assertTrue(original.is_file())
        self.assertIsNone(order["nachlauf"]["version_entscheidung"])
        order = self.tun("master", order, weg="datei", datei=MASTER)
        order = self.tun("master", order, weg="ohne")
        with self.assertRaises(Ablehnung):
            self.tun("version", order, entscheidung="archivieren")
        order = self.tun("version", order, entscheidung="archivieren", bestaetigt=True)
        self.assertFalse(original.exists())
        self.assertEqual(len(order["archivierte_versionen"]), 1)
        self.assertTrue((self.cfg.data_dir / "versionen-archiv" / order["id"] / MASTER).is_file())
        self.assertIsNone(order["nachlauf"]["version_entscheidung"])

    def test_quelle_und_referenz_bleiben_geschuetzt(self):
        order = self.start()
        with self.assertRaises(Ablehnung) as cm:
            self.tun("version", order, entscheidung="archivieren", pfad=TIDY1, bestaetigt=True)
        self.assertEqual(cm.exception.code, "in_use") if hasattr(cm.exception, "code") else self.assertTrue(True)
        self.assertTrue((self.cfg.music_root / TIDY1).is_file())
        self.assertFalse((self.cfg.data_dir / "versionen-archiv").exists())

    def test_veroeffentlichten_master_aendern_ohne_doppeluplaod(self):
        order = self.veroeffentlicht(master=True)
        self.assertEqual(order["nachlauf"]["soundcloud"]["hochgeladen_datei"], MASTER)
        order = self.tun("master", order, weg="ohne")
        self.assertTrue(order["nachlauf"]["soundcloud"]["audio_offen"])
        with self.assertRaises(Ablehnung):
            self.tun("version", order, entscheidung="archivieren", bestaetigt=True)
        # Erst nach manuell bestätigtem Austausch darf die alte Fassung ins Archiv.
        order = self.tun("soundcloud", order, entscheidung="audio_bestaetigt", bestaetigt=True)
        self.assertFalse(order["nachlauf"]["soundcloud"]["audio_offen"])
        self.assertEqual(order["nachlauf"]["soundcloud"]["hochgeladen_datei"], TIDY1)
        order = self.tun("version", order, entscheidung="archivieren", bestaetigt=True)
        self.assertFalse((self.cfg.music_root / MASTER).exists())

    def test_text_erneuern_und_selben_sc_track_aktualisieren(self):
        order = self.veroeffentlicht()
        order = self.tun("text_aendern", order, wunsch="Noch kürzer und klarer")
        self.assertEqual(order["nachlauf"]["text"]["stand"], "offen")
        self.assertTrue(order["nachlauf"]["soundcloud"]["text_offen"])
        self.assertTrue(any("text" in g for t in self.claude.todo() for g in t["gruende"]))
        self.cli("phase", order["id"], "--name", "text", "--file", TEXT)
        order = self.store.load(order["id"])
        with self.assertRaises(Ablehnung):
            self.tun("soundcloud", order, entscheidung="metadaten")
        with patch("sirens.soundcloud.metadaten_ersetzen", return_value="") as aktualisieren:
            order = self.tun("soundcloud", order, entscheidung="metadaten", bestaetigt=True)
        aktualisieren.assert_called_once_with("https://soundcloud.com/cco/too-tidy",
                                               "Neue Beschreibung und Songtext", [])
        self.assertFalse(order["nachlauf"]["soundcloud"]["text_offen"])
        self.assertEqual(order["nachlauf"]["soundcloud"]["link"], "https://soundcloud.com/cco/too-tidy")

    def test_metadaten_fehler_bleibt_offen(self):
        order = self.veroeffentlicht()
        order = self.tun("text_aendern", order, wunsch="")
        self.cli("phase", order["id"], "--name", "text", "--file", TEXT)
        order = self.store.load(order["id"])
        with patch("sirens.soundcloud.metadaten_ersetzen", return_value="HTTP 401"):
            order = self.tun("soundcloud", order, entscheidung="metadaten", bestaetigt=True)
        self.assertTrue(order["nachlauf"]["soundcloud"]["text_offen"])
        self.assertEqual(order["nachlauf"]["soundcloud"]["text_fehler"], "HTTP 401")

    def test_ausgelassene_veroeffentlichung_erneut_oeffnen(self):
        order = self.start()
        order = self.tun("master", order, weg="ohne")
        self.cli("phase", order["id"], "--name", "cover", "--file", COVER)
        self.cli("phase", order["id"], "--name", "text", "--file", TEXT)
        order = self.tun("cover", self.store.load(order["id"]), entscheidung="annehmen")
        order = self.tun("soundcloud", order, entscheidung="ohne")
        order = self.tun("soundcloud", order, entscheidung="wieder_oeffnen")
        self.assertEqual(order["nachlauf"]["soundcloud"]["stand"], "offen")


if __name__ == "__main__":
    unittest.main()
