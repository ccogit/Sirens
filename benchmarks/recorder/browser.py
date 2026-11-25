"""Lokaler WP16-Browser-Soak mit echtem Worklet und eigenem Test-HTTP-Adapter."""
import argparse
import datetime
import json
import secrets
import re
import tempfile
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from benchmarks.baseline import collect
from benchmarks.result import METRICS, write
from sirens.realtime.recordings import Recording

MODULES = Path(__file__).resolve().parents[2] / "web" / "js" / "realtime"
PAGE = """<!doctype html><meta charset=utf-8><title>WP16 Recorder-Soak</title>
<button id=start>Aufnahme starten</button><pre id=status>Bereit</pre>
<script type=module>
import {AudioCore} from "/js/audio_core.js";
import {Recorder} from "/js/recorder.js";
const token = TOKEN;
const seconds = SECONDS;
const status=document.querySelector("#status");
async function post(path, body, type="application/json"){
    const r=await fetch(path,{method:"POST",headers:{"Content-Type":type,"X-Recorder":token},
        body,signal:AbortSignal.timeout(5000)});
    if(!r.ok)throw new Error(await r.text());
    return r.json();
}
document.querySelector("#start").onclick=async e=>{
    e.target.disabled=true;
    let core, rec;
    try {
        core=await AudioCore.open([0]);
        if(core.rate!==48000)throw new Error("AudioContext nicht 48 kHz; Geräteformat einstellen");
        await post("/start",JSON.stringify({rate:core.rate}));
        rec=await Recorder.attach(core,async(frame,bytes)=>{
            return (await post("/block/"+frame,bytes,"application/octet-stream")).next;
        },()=>post("/close","{}"));
        const osc=core.context.createOscillator(), gain=core.context.createGain();
        osc.frequency.value=440;gain.gain.value=.05;
        osc.connect(gain);gain.connect(core.node,0,0);
        const play=core.reset(0,true);
        osc.start(play.frame/core.rate);
        rec.start();
        const until=core.context.currentTime+seconds;
        const timer=setInterval(()=>{
            status.textContent="Restzeit: "+Math.max(0,Math.ceil(until-core.context.currentTime))+" s";
            if(core.context.currentTime>=until)rec.stop();
            if(core.context.state!=="running")rec.fail("AudioContext unterbrochen");
        },100);
        const result=await rec.done;
        clearInterval(timer);osc.stop();
        await post("/report",JSON.stringify(result));
        status.textContent=JSON.stringify(result,null,2);
    }catch(err){
        if(rec){rec.fail(err);await rec.done;}
        status.textContent=String(err);
    }finally{if(core)await core.destroy();}
};
</script>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=1800)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 1800:
        parser.error("seconds: 1..1800")
    token = secrets.token_hex(16)
    state = {"rec": None, "start": None, "closed": False}
    with tempfile.TemporaryDirectory(dir=args.scratch) as tmp:
        root = Path(tmp)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, code, data, mime="application/json"):
                if not isinstance(data, bytes):
                    data = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def host_ok(self):
                return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

            def do_GET(self):
                if not self.host_ok() or self.requestline.split()[1] != self.path:
                    self.reply(404, {}); return
                if self.path == "/":
                    page = PAGE.replace("TOKEN", json.dumps(token)).replace("SECONDS", str(args.seconds))
                    self.reply(200, page.encode(), "text/html; charset=utf-8"); return
                if self.path.startswith("/js/"):
                    name = self.path[4:]
                    if re.fullmatch(r"(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.js", name):
                        try:
                            file = (MODULES / name).resolve(strict=True)
                            if file.is_relative_to(MODULES) and file.is_file():
                                self.reply(200, file.read_bytes(), "text/javascript"); return
                        except (OSError, RuntimeError, ValueError):
                            pass
                self.reply(404, {})

            def do_POST(self):
                origin = f"http://127.0.0.1:{self.server.server_port}"
                if not self.host_ok() or self.headers.get("Origin") != origin or self.headers.get("X-Recorder") != token:
                    self.reply(403, {}); return
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                    if not 0 <= length <= 16384 or self.headers.get("Transfer-Encoding"):
                        raise ValueError("Länge")
                    self.connection.settimeout(5)
                    data = self.rfile.read(length)
                    if len(data) != length:
                        raise ValueError("Unvollständiger Block")
                    rec = state["rec"]
                    if self.path == "/start" and rec is None:
                        if json.loads(data) != {"rate": 48000}:
                            raise ValueError("Abtastrate")
                        state["rec"] = Recording(root/"recordings", root/"music", "browser", 48000)
                        state["start"] = time.monotonic()
                        result = {}
                    elif self.path.startswith("/block/") and rec is not None and not state["closed"]:
                        if self.headers.get("Content-Type") != "application/octet-stream":
                            raise ValueError("PCM-Typ")
                        result = {"next": rec.append(data, int(self.path[7:]))}
                    elif self.path == "/close" and rec is not None:
                        state["paths"] = rec.stop()
                        state["closed"] = True
                        result = {}
                    elif self.path == "/report" and state["closed"]:
                        report = json.loads(data)
                        frames = 0
                        for path in state["paths"]:
                            with wave.open(str(path)) as f:
                                if (f.getframerate(), f.getnchannels(), f.getsampwidth()) != (48000, 2, 3):
                                    raise ValueError("WAV-Format")
                                frames += f.getnframes()
                        good = (report.get("error") is None and frames == report.get("frames")
                                and abs(frames-args.seconds*48000) <= 48000)
                        metrics = dict.fromkeys(METRICS)
                        metrics["rtf"] = (time.monotonic()-state["start"])/args.seconds
                        write(args.out, {"wp":"WP16","kandidat":"Browser-Recorder-Soak",
                            "zeitpunkt":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "befehl":f"python -m benchmarks.recorder.browser --scratch <scratch> --out <out> --seconds {args.seconds}",
                            "gate":"nicht_gemessen" if good else "red","modus":"offline","rechner":collect(),
                            "messwerte":{"kalt":metrics,"warm":dict.fromkeys(METRICS)},
                            "notizen":[f"Worklet/Disk-Testadapter: {'bestanden' if good else 'fehlgeschlagen'}",
                                       f"Frames={frames}; Browser-Frames={report.get('frames')}",
                                       "Produktions-Session-API und Geräte-Latenz nicht gemessen."]})
                        result = {"ok":good}
                    else:
                        raise ValueError("Zustand")
                    self.reply(200, result)
                except Exception as exc:
                    self.reply(400, {"error":str(exc)})

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            print(f"http://127.0.0.1:{server.server_port}/ – öffnen, Lautstärke niedrig, Start klicken; danach Strg+C", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                if state["rec"] is not None:
                    state["rec"].stop()


if __name__ == "__main__":
    main()
