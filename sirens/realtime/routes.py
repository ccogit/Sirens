"""Steuer-API v1; PCM ausschließlich auf dem privaten Sidecar-Pfad."""
import threading

from ..contracts import Ablehnung
from .contracts import error, invalid
from .model_registry import ModelRegistry
from .sessions import Sessions
from .telemetry import read_gpu

_LOCK = threading.Lock()


def service(handler):
    with _LOCK:
        app = handler.app
        if getattr(app, "rt_sessions", None) is None:
            app.rt_sessions = Sessions(app.cfg, {f"http://{h}" for h in handler._erlaubte_hosts()})
        return app.rt_sessions


def dispatch(handler, path, body):
    origin = handler.headers.get("Origin")
    if origin is not None and origin not in {f"http://{h}" for h in handler._erlaubte_hosts()}:
        raise Ablehnung("forbidden_origin", "Anfragen von fremden Seiten werden abgelehnt.", status=403)
    cfg = handler.app.cfg
    if not cfg.rt_enabled:
        raise error("unavailable")
    method = handler.command
    parts = path.removeprefix("/api/rt/v1/").split("/")
    if method == "GET" and parts == ["capabilities"]:
        return handler._json(200, {"protocol_version": 1,
                                   "capabilities": ModelRegistry(mock_enabled=cfg.rt_mock).capabilities()})
    if method == "GET" and parts == ["gpu"]:
        snapshot = read_gpu().as_dict()
        sessions = getattr(handler.app, "rt_sessions", None)
        if sessions:
            with sessions.lock:
                active = tuple(sessions.sessions.values())
            snapshot["queue_depth"] = sum(s.pending.qsize() for s in active)
        return handler._json(200, snapshot)
    if method == "POST" and parts == ["sessions"]:
        if not cfg.rt_mock:
            raise error("unavailable")
        return handler._json(201, service(handler).create(body))
    if len(parts) >= 2 and parts[0] == "sessions":
        s = service(handler).get(parts[1])
        tail = parts[2:]
        if method == "GET" and not tail:
            return handler._json(200, s.snapshot())
        if method == "POST" and tail == ["commands"]:
            return handler._json(200, s.command(body))
        if method == "POST" and tail == ["close"]:
            if body != {}:
                raise invalid("body")
            return handler._json(200, s.close())
        if method == "POST" and tail == ["transport"]:
            if body != {}:
                raise invalid("body")
            return handler._json(200, s.transport())
        if method == "POST" and tail == ["render"]:
            return handler._json(202, s.render(body))
    if len(parts) >= 2 and parts[0] == "jobs":
        if method == "GET" and len(parts) == 2:
            return handler._json(200, service(handler).job(parts[1]))
        if method == "POST" and parts[2:] == ["cancel"]:
            if body != {}:
                raise invalid("body")
            return handler._json(200, service(handler).job(parts[1], cancel=True))
    if method == "GET" and len(parts) == 2 and parts[0] == "assets":
        return handler._json(200, service(handler).asset(parts[1]))
    raise error("unavailable")
