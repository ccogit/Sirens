"""Nur den lokalen Benchmark und seine ES-Module ausliefern."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS = {"/benchmarks/audio_core/index.html", "/benchmarks/audio_core/measure.js"}
PATHS |= {"/web/js/realtime/" + p for p in (
    "audio_core.js", "clock.js", "transport.js", "pcm.js",
    "worklet_processor.js", "ringbuffer.js")}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def allowed(self):
        return (self.path in PATHS and
                self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}")

    def do_GET(self):
        if self.allowed():
            super().do_GET()
        else:
            self.send_error(404)

    def do_HEAD(self):
        if self.allowed():
            super().do_HEAD()
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8766)
    args = p.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}/benchmarks/audio_core/index.html", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
