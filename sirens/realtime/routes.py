"""Steuer-API v1; PCM ausschließlich auf dem privaten Sidecar-Pfad."""
import threading

from ..contracts import Ablehnung
from .contracts import error, invalid, uint
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


def recording_block(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if (handler.headers.get("Transfer-Encoding") is not None
            or handler.headers.get("Content-Type", "").lower() != "application/octet-stream"
            or not 8 <= length <= 16384 or length % 8):
        handler.close_connection = True
        raise invalid("payload")
    raw = handler.rfile.read(length)
    if len(raw) != length:
        handler.close_connection = True
        raise invalid("payload")
    return raw


def dispatch(handler, path, body):
    # Unbekannte oder abgelehnte PUTs dürfen keine ungelesenen Bytes für
    # einen weiteren HTTP-Request auf derselben Verbindung hinterlassen.
    if handler.command == "PUT":
        handler.close_connection = True
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
        recorder = s.manager.recordings
        if tail and tail[0] == "recordings":
            with s.lock:
                sid = s.data["id"]
                if method == "POST" and len(tail) == 1:
                    if s.data["state"] not in ("ready", "playing", "paused"):
                        raise error("unavailable")
                    return handler._json(201, recorder.create(sid, body, s.data["sample_rate"]))
                if len(tail) == 3 and tail[2] == "close" and method == "POST":
                    if body != {}:
                        raise invalid("body")
                    return handler._json(200, recorder.close(sid, tail[1]))
                if len(tail) == 4 and tail[2] == "blocks" and method == "PUT":
                    if s.data["state"] not in ("ready", "playing", "paused"):
                        raise error("unavailable")
                    with recorder.lock:
                        recorder._get(sid, tail[1])
                    if not tail[3].isascii() or not tail[3].isdigit() or len(tail[3]) > 16:
                        raise invalid("start_frame")
                    start = uint(int(tail[3]), "start_frame")
                    return handler._json(200, recorder.append(sid, tail[1], start, recording_block(handler)))
        if method == "GET" and tail == ["export-source"]:
            # Nur die bereits geladene Quelle dieser Sitzung; keine Pfade vom Client.
            with s.lock, s.manager.sources.lock:
                if s.asset is None or s.data["state"] not in ("ready", "playing", "paused"):
                    raise error("unavailable")
                aid = s.asset["id"]
                digest = s.manager.sources.digests.get(aid)
                if digest is None:
                    raise error("unavailable")
                return handler._json(200, {"asset_id": aid, "sha256": digest})
        if tail and tail[0] == "exports":
            if method == "POST" and len(tail) == 1:
                return handler._json(201, recorder.export(s.data["id"], body))
            if method == "GET" and len(tail) == 2:
                return handler._json(200, recorder.load_export(s.data["id"], tail[1]))
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
        if method == "GET" and tail == ["dry"]:
            raw = s.dry_audio()
            handler.send_response(200)
            handler.send_header("Content-Type", "application/octet-stream")
            handler.send_header("Content-Length", str(len(raw)))
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("X-Content-Type-Options", "nosniff")
            handler.end_headers()
            handler.wfile.write(raw)
            return
        if method == "POST" and tail == ["render"]:
            return handler._json(202, s.render(body))
    if len(parts) >= 2 and parts[0] == "jobs":
        if method == "GET" and len(parts) == 2:
            return handler._json(200, service(handler).job(parts[1]))
        if method == "POST" and parts[2:] == ["cancel"]:
            if body != {}:
                raise invalid("body")
            return handler._json(200, service(handler).job(parts[1], cancel=True))
    if method == "POST" and parts == ["assets", "resolve"]:
        if not isinstance(body, dict) or set(body) != {"pfad"}:
            raise invalid("asset")
        return handler._json(201, service(handler).sources.register(body["pfad"]))
    if method == "GET" and len(parts) == 3 and parts[0] == "assets" and parts[2] == "beatgrid":
        return handler._json(200, service(handler).sources.beatgrid(parts[1]))
    if method == "GET" and len(parts) == 2 and parts[0] == "assets":
        return handler._json(200, service(handler).asset(parts[1]))
    raise error("unavailable")
