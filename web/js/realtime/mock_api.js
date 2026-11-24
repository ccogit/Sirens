// UI-Mock: nur synthetische Daten, keine echte KI oder HTTP-Aufrufe.
export const capability = {"id":"mock","mock":true,"available":true,"mode":"offline","sample_rates":[48000],"channels":2,"context_frames":0,"hop_frames":256,"latency_frames":0,"controls":[{"name":"gain","min":0,"max":2,"default":1},{"name":"delay_frames","min":0,"max":48000,"default":0}],"vram_peak_bytes":"unknown","device":"cpu","license":"repository","model_revision":"mock-v1"};
export const telemetry = {"available":false,"device":null,"vram_total_bytes":null,"vram_used_bytes":null,"compute_percent":null,"temperature_c":null,"queue_depth":0,"deadline_misses":0,"underruns":0};
const asset = {"id":"33333333333333333333333333333333","kind":"source","sample_rate":48000,"channels":2,"nframes":256};
const clone = data => JSON.parse(JSON.stringify(data));
const failure = (error, status, meldung, feld=null) => ({status, body:{error,meldung,feld}});
export function createMockApi() {
    const sessions = new Map(), jobs = new Map();
    let counter=16;
    const id=()=> (counter++).toString(16).padStart(32,"0");
    const ok=(body,status=200)=>({status,body:clone(body)});
    const invalid=()=>failure("invalid",400,"Ungültiger Vertragswert.");
    const notFound=()=>failure("not_found",404,"Nicht gefunden.");
    const prefix="/api/rt/v1/";
    return async function request(method,path,body=null) {
        if (!path.startsWith(prefix)) return notFound();
        const [kind,key,action,...rest]=path.slice(prefix.length).split("/");
        if (rest.length) return notFound();
        if (method==="GET" && kind==="capabilities" && !key) return ok({protocol_version:1,capabilities:[capability]});
        if (method==="GET" && kind==="gpu" && !key) return ok(telemetry);
        if (method==="POST" && kind==="sessions" && !key) {
            if (body?.capability_id!=="mock" || body.sample_rate!==48000) return invalid();
            const s={id:id(),state:"created",epoch:0,seq:null,capability_id:"mock",sample_rate:48000,job_id:null};
            sessions.set(s.id,s); return ok(s,201);
        }
        if (kind==="sessions" && sessions.has(key)) {
            const s=sessions.get(key);
            if (method==="GET" && !action) return ok(s);
            if (method==="POST" && action==="close") {
                if (s.state!=="closed") {s.state="closed";s.epoch++;s.seq=null;}
                return ok(s);
            }
            if (method==="POST" && action==="commands") {
                if (!body || !Number.isInteger(body.epoch) || !Number.isInteger(body.seq) || body.seq<0 || body.seq>0xffffffff) return invalid();
                if (body.epoch!==s.epoch) return failure("stale_epoch",409,"Veraltete Transportgeneration.","epoch");
                if (s.seq!==null && body.seq<=s.seq || s.state==="closed") return invalid();
                const a=body.args;
                if (!a || typeof a!=="object" || Array.isArray(a)) return invalid();
                switch (body.command) {
                case "load":
                    if (s.state!=="created" || a.asset_id!==asset.id) return invalid();
                    const j={id:id(),session_id:s.id,state:"ready",progress:1,asset_id:asset.id,error:null};
                    jobs.set(j.id,j);s.job_id=j.id;s.state="ready";break;
                case "play": if (!["ready","paused"].includes(s.state)) return invalid();s.state="playing";break;
                case "pause": if (s.state!=="playing") return invalid();s.state="paused";break;
                case "seek": if (!Number.isSafeInteger(a.source_frame)||a.source_frame<0) return invalid();s.epoch++;s.seq=null;return ok(s);
                case "set_param": if (typeof a.name!=="string" || !Number.isFinite(a.value)) return invalid();break;
                case "bypass": if (typeof a.enabled!=="boolean") return invalid();break;
                case "schedule": if (!Number.isSafeInteger(a.output_frame)||a.output_frame<0||!["play","pause","set_param","bypass"].includes(a.command?.command)) return invalid();break;
                default: return invalid();
                }
                s.seq=body.seq;return ok(s);
            }
        }
        if (kind==="jobs" && jobs.has(key)) {
            const j=jobs.get(key);
            if (method==="GET" && !action) return ok(j);
            if (method==="POST" && action==="cancel") {
                if (["queued","running"].includes(j.state)) j.state="cancelled";
                return ok(j);
            }
        }
        if (method==="GET" && kind==="assets" && key===asset.id && !action) return ok(asset);
        return notFound();
    };
}
