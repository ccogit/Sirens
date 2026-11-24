import {RingBuffer} from "./ringbuffer.js";

export const CEILING = Math.pow(10,-1/20);
// Float32-Grenze abrunden, damit auch der gespeicherte Wert nicht über -1 dBFS liegt.
const LIMIT = Math.fround(CEILING) > CEILING ? Math.fround(CEILING - 1e-7) : Math.fround(CEILING);
const finite = v => Number.isFinite(v) ? v : 0;
const clamp = (v,lo,hi) => Math.max(lo,Math.min(hi,v));

export class RenderPath {
    constructor(latency=0, ramp=64, capacity=16384) {
        if (!Number.isInteger(latency) || latency<0 || latency>192000) throw new RangeError("Latenz");
        this.wet = new RingBuffer(capacity);
        this.delay = new Float32Array(latency*2);
        this.latency=latency; this.index=0;
        this.pair=new Float32Array(2); this.out=new Float32Array(2);
        this.lastWet=new Float32Array(2); this.ramp=Math.max(1,ramp);
        this.mix=0; this.target=0; this.gain=1; this.targetGain=1; this.bypass=false;
    }
    reset(epoch,frame) {
        this.wet.reset(epoch,frame); this.delay.fill(0); this.index=0;
        this.mix=0; this.lastWet.fill(0);
    }
    // Dry wird um deklarierte Wet-Latenz verzögert. Wet trägt bereits
    // seine kompensierte Master-Adresse. Bei Lücken blendet der letzte
    // gültige Wert in den zeitgleichen Dry-Pfad aus.
    sample(left,right) {
        left=finite(left); right=finite(right);
        if(this.latency) {
            const i=this.index, l=this.delay[i], r=this.delay[i+1];
            this.delay[i]=left; this.delay[i+1]=right; left=l; right=r;
            this.index=(i+2)%this.delay.length;
        }
        const ready=this.wet.read(this.pair);
        if(ready) { this.lastWet[0]=this.pair[0]; this.lastWet[1]=this.pair[1]; }
        const target=ready && !this.bypass ? this.target : 0;
        this.mix += clamp(target-this.mix,-1/this.ramp,1/this.ramp);
        this.gain += clamp(this.targetGain-this.gain,-1/this.ramp,1/this.ramp);
        this.out[0]=(this.mix===0?left:left+(this.lastWet[0]-left)*this.mix)*this.gain;
        this.out[1]=(this.mix===0?right:right+(this.lastWet[1]-right)*this.mix)*this.gain;
    }
}
export function limit(v) { return clamp(finite(v),-LIMIT,LIMIT); }

// Unter Node wird derselbe Referenzpfad ohne Browser-Globals getestet.
if(typeof AudioWorkletProcessor !== "undefined") {
    class SirensProcessor extends AudioWorkletProcessor {
        constructor(options) {
            super();
            const cfg=options.processorOptions;
            this.paths=cfg.latencies.map(l=>new RenderPath(l,Math.max(1,Math.round(sampleRate*.005))));
            this.epoch=0; this.start=currentFrame; this.active=false; this.cursor=currentFrame;
            this.loopLength=0; this.nextLoop=Infinity;
            this.port.onmessage=({data:m})=>{
                if(m.type==="reset" && m.epoch>=this.epoch) {
                    this.epoch=m.epoch; this.start=m.frame; this.active=m.active;
                    this.loopLength=m.loopLength||0; this.nextLoop=this.loopLength?this.start+this.loopLength:Infinity;
                    for(const p of this.paths) p.reset(m.epoch,m.frame);
                } else if(m.type==="pcm") {
                    const p=this.paths[m.stream-1];
                    if(p && !p.wet.write(m.epoch,m.start,m.samples))
                        this.port.postMessage({type:"reject",stream:m.stream,seq:m.seq,epoch:m.epoch,cursor:p.wet.cursor});
                } else if(m.type==="param") {
                    const p=this.paths[m.stream-1];
                    if(p) {
                        if(Number.isFinite(m.mix)) p.target=clamp(m.mix,0,1);
                        if(Number.isFinite(m.gain)) p.targetGain=clamp(m.gain,0,1);
                        if(typeof m.bypass==="boolean") p.bypass=m.bypass;
                    }
                } else if(m.type==="status") {
                    this.port.postMessage({type:"status",epoch:this.epoch,cursor:this.cursor,
                        streams:this.paths.map(p=>({cursor:p.wet.cursor,underruns:p.wet.underruns}))});
                }
            };
        }
        process(inputs,outputs) {
            const out=outputs[0];
            if(!out.length) return true;
            for(let i=0;i<out[0].length;i++) {
                const frame=currentFrame+i;
                let l=0,r=0;
                if(this.active && frame>=this.start) {
                    if(frame===this.nextLoop) {
                        if(this.epoch===0xffffffff) this.active=false;
                        else {
                            this.epoch++; this.nextLoop+=this.loopLength;
                            for(let j=0;j<this.paths.length;j++) this.paths[j].reset(this.epoch,frame);
                        }
                    }
                    if(this.active) for(let j=0;j<this.paths.length;j++) {
                        const p=this.paths[j], input=inputs[j];
                        // Ein verspäteter Reset darf keine vergangenen Blöcke wiedergeben.
                        if(p.wet.cursor!==frame) p.reset(this.epoch,frame);
                        const a=input[0],b=input[1];
                        p.sample(a?a[i]:0,b?b[i]:a?a[i]:0);
                        l+=p.out[0]; r+=p.out[1];
                    }
                }
                out[0][i]=limit(l); if(out.length>1) out[1][i]=limit(r);
                this.cursor=frame+1;
            }
            return true;
        }
    }
    registerProcessor("sirens-core-v1",SirensProcessor);
}
