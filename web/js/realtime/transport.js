import {unpack} from "./pcm.js";

// Ganzzahlige absolute Grenzen: keine Rundung pro Block und kein aufsummierter Rest.
export function frameAtRate(frame, from, to) {
    if(!Number.isSafeInteger(frame)||frame<0||!Number.isSafeInteger(from)||from<=0||
        !Number.isSafeInteger(to)||to<=0)throw new RangeError("Frame/Abtastrate");
    const result=Number((BigInt(frame)*BigInt(to)+BigInt(Math.floor(from/2)))/BigInt(from));
    if(!Number.isSafeInteger(result))throw new RangeError("Frame");
    return result;
}

// Deterministische lineare Interpolation außerhalb des Render-Callbacks.
// Absolute Framegrenzen verhindern kumulierte Rundungsdrift.
export function resample(samples, from, to, start = 0) {
    if (!Number.isSafeInteger(start) || start < 0 || !Number.isInteger(from) || from <= 0 ||
        !Number.isInteger(to) || to <= 0 || samples.length % 2) throw new RangeError("PCM");
    const first = frameAtRate(start,from,to);
    const last = frameAtRate(start+samples.length/2,from,to);
    const phase=Number(BigInt(first)*BigInt(from)-BigInt(start)*BigInt(to));
    const result = new Float32Array((last - first) * 2);
    for (let i = 0; i < result.length / 2; i++) {
        const p = Math.max(0, Math.min(samples.length / 2 - 1, (phase+i*from)/to));
        const j = Math.floor(p), k = Math.min(j + 1, samples.length / 2 - 1), f = p - j;
        for (let c = 0; c < 2; c++) {
            const a = samples[j * 2 + c], b = samples[k * 2 + c];
            result[i * 2 + c] = (Number.isFinite(a) ? a : 0) * (1-f) + (Number.isFinite(b) ? b : 0) * f;
        }
    }
    return result;
}

// Maximal acht ausstehende Transferables je Stream. Der Worklet bestätigt
// erst nach Verbrauch/Verwerfen, nicht schon beim Empfang.
export class Transport {
    constructor(port, stream, rate, lookahead = 16384) {
        this.port = port; this.stream = stream; this.rate = rate; this.lookahead = lookahead;
        this.epoch = 0; this.seq = -1; this.cursor = 0; this.pending = new Map();
        this.dropped = 0; this.wireRate=null;
    }
    // Nur der Mock verwendet Masterkoordinaten in der festen Serverrate.
    setWireRate(rate) {
        if(!Number.isSafeInteger(rate)||rate<=0)throw new RangeError("Abtastrate");
        this.wireRate=rate;
    }
    reset(epoch, frame, wireSource=0) {
        this.epoch=epoch;this.cursor=frame;this.seq=-1;this.pending.clear();
        this.origin=frame;this.wireSource=wireSource;
        this.wireOrigin=this.wireRate===null?frame:frameAtRate(frame,this.rate,this.wireRate);
    }
    acknowledge(message) {
        if (message.epoch === this.epoch) {
            this.pending.delete(message.seq);
            this.cursor = Math.max(this.cursor, message.cursor ?? 0);
        }
    }
    advance(epoch,cursor) {
        if(epoch!==this.epoch) return;
        this.cursor=Math.max(this.cursor,cursor);
        for(const [seq,end] of this.pending) if(end<=this.cursor) this.pending.delete(seq);
    }
    push(block) {
        const {header:h,payload} = unpack(new Uint8Array(block));
        // Master-Ausgabeframe; beim festen Mock-Serverraster relativ zur Epoch umrechnen.
        if (h.stream_id !== this.stream || h.epoch !== this.epoch || h.seq <= this.seq ||
            h.start_frame > BigInt(Number.MAX_SAFE_INTEGER)) { this.dropped++; return false; }
        let start=Number(h.start_frame), sourceStart;
        if(this.wireRate!==null){
            if(h.sample_rate!==this.wireRate || start<this.wireOrigin){this.dropped++;return false;}
            sourceStart=this.wireSource+start-this.wireOrigin;
            if(!Number.isSafeInteger(sourceStart)){this.dropped++;return false;}
            start=this.origin+frameAtRate(sourceStart,this.wireRate,this.rate)-
                frameAtRate(this.wireSource,this.wireRate,this.rate);
        }else sourceStart=frameAtRate(start,this.rate,h.sample_rate);
        const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
        const raw = new Float32Array(h.nframes * 2);
        for (let i=0;i<raw.length;i++) raw[i] = view.getFloat32(i*4,true);
        const samples = resample(raw,h.sample_rate,this.rate,sourceStart);
        if (this.pending.size >= 8 || start < this.cursor || start + samples.length/2 > this.cursor+this.lookahead) {
            this.dropped++; return false;
        }
        this.seq = h.seq; this.pending.set(h.seq, start + samples.length/2);
        this.port.postMessage({type:"pcm",stream:this.stream,epoch:h.epoch,seq:h.seq,start,samples},[samples.buffer]);
        return true;
    }
}
