"""Einzige RT-Weiche: WP01 stellt nur capabilities bereit."""
from ..contracts import Ablehnung
from .contracts import error
from .mock import MockAdapter

def dispatch(handler, path, body):
    origin = handler.headers.get("Origin")
    if origin is not None and origin not in {f"http://{h}" for h in handler._erlaubte_hosts()}:
        raise Ablehnung("forbidden_origin", "Anfragen von fremden Seiten werden abgelehnt.", status=403)
    cfg = handler.app.cfg
    if not cfg.rt_enabled:
        raise error("unavailable")
    if handler.command == "GET" and path == "/api/rt/v1/capabilities":
        return handler._json(200, {"protocol_version": 1,
                                   "capabilities": [MockAdapter().probe()] if cfg.rt_mock else []})
    raise error("unavailable")
