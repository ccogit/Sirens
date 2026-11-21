"""Auftragsablage: eine JSON-Datei je Auftrag, atomar geschrieben, nie gelöscht."""
import copy
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from .contracts import ID_RE, SCHEMA_VERSION, Ablehnung


def jetzt():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json_atomic(path, data):
    """Temporäre Datei im selben Ordner schreiben, dann ersetzen."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    for versuch in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: ein Leser hält die Datei gerade offen
            if versuch == 19:
                os.unlink(tmp)
                raise
            time.sleep(0.02)


@contextmanager
def sperre(path, timeout=10.0, veraltet=60.0):
    """Lockdatei exklusiv anlegen; eine liegengebliebene Sperre verfällt nach `veraltet` Sekunden."""
    ende = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except (FileExistsError, PermissionError):
            try:
                if time.time() - os.path.getmtime(path) > veraltet:
                    os.unlink(path)
                    continue
            except OSError:
                pass
            if time.monotonic() > ende:
                raise Ablehnung("locked", "Der Auftrag wird gerade von anderer Stelle geändert. Bitte erneut versuchen.",
                                status=503) from None
            time.sleep(0.02)
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass


class Store:
    def __init__(self, cfg):
        self.dir = cfg.orders_dir

    def _bereit(self):
        self.dir.mkdir(parents=True, exist_ok=True)

    def _datei(self, oid):
        if not isinstance(oid, str) or not ID_RE.match(oid):
            raise Ablehnung("not_found", "Diesen Auftrag gibt es nicht.", "id", 404)
        return self.dir / f"{oid}.json"

    def load(self, oid):
        datei = self._datei(oid)
        try:
            return json.loads(datei.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise Ablehnung("not_found", "Diesen Auftrag gibt es nicht.", "id", 404) from None
        except ValueError:
            raise Ablehnung("corrupt", f"Die Auftragsdatei {datei.name} ist nicht lesbar.", "id", 500) from None

    def list(self):
        """Alle lesbaren Aufträge, neueste Änderung zuerst."""
        orders = []
        if self.dir.is_dir():
            for datei in self.dir.glob("SA-*.json"):
                try:
                    orders.append(self.load(datei.stem))
                except Ablehnung:
                    continue
        return sorted(orders, key=lambda o: (o["updated_at"], o["id"]), reverse=True)

    def create(self, wunsch, vorgaenger_id=None):
        self._bereit()
        tag = datetime.now().strftime("%Y%m%d")
        with sperre(self.dir / "neu.lock"):
            nummern = [int(p.stem[-3:]) for p in self.dir.glob(f"SA-{tag}-*.json") if ID_RE.match(p.stem)]
            nummer = max(nummern, default=0) + 1
            if nummer > 999:
                raise Ablehnung("limit", "Für heute sind keine Auftragsnummern mehr frei.", status=409)
            zeit = jetzt()
            order = {
                "schema_version": SCHEMA_VERSION, "id": f"SA-{tag}-{nummer:03d}", "revision": 1,
                "created_at": zeit, "updated_at": zeit, "status": "entwurf", "vorgaenger_id": vorgaenger_id,
                "wunsch": wunsch, "plan": None, "tracks_stand": [],
                "ergebnis": {"release_slug": "", "song_slugs": [], "package_ids": []},
                "verlauf": [], "bewertungen": [],
            }
            write_json_atomic(self._datei(order["id"]), order)
            return order

    def mutate(self, oid, expected_revision, fn):
        """Auftrag unter Sperre ändern. `fn` bekommt eine Kopie; lehnt sie ab, bleibt die Ablage unverändert."""
        datei = self._datei(oid)
        if not datei.is_file():
            raise Ablehnung("not_found", "Diesen Auftrag gibt es nicht.", "id", 404)
        with sperre(datei.with_suffix(".lock")):
            order = self.load(oid)
            if expected_revision is not None and expected_revision != order["revision"]:
                raise Ablehnung("revision_conflict",
                                "Der Auftrag wurde inzwischen geändert. Bitte neu laden und erneut versuchen.",
                                "revision", 409)
            neu = copy.deepcopy(order)
            fn(neu)
            neu["revision"] = order["revision"] + 1
            neu["updated_at"] = jetzt()
            write_json_atomic(datei, neu)
            return neu
