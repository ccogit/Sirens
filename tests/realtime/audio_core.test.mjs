import test from "node:test";
import assert from "node:assert/strict";
import {RingBuffer} from "../../web/js/realtime/ringbuffer.js";
import {Clock} from "../../web/js/realtime/clock.js";
import {Transport,resample} from "../../web/js/realtime/transport.js";
import {pack} from "../../web/js/realtime/pcm.js";

test("Ring: voll, leer, Umlauf, Überlauf, Epoch, Lücken",()=>{
    const r = new RingBuffer(4), pair = new Float32Array(2);
    assert.equal(r.read(pair),false);
    assert.equal(r.underruns,1);
    assert.equal(r.write(0,1,new Float32Array([1,2,3,4,5,6,7,8])),true);
    assert.equal(r.write(0,2,new Float32Array([1,2])),false);
    assert.equal(r.write(0,5,new Float32Array([1,2])),false);
    assert.equal(r.read(pair),true); assert.deepEqual([...pair],[1,2]);
    assert.equal(r.write(0,5,new Float32Array([9,10])),true);
    for(let i=0;i<4;i++) assert.equal(r.read(pair),true);
    assert.deepEqual([...pair],[9,10]); assert.equal(r.count,0);
    r.reset(1,20); assert.equal(r.write(0,20,new Float32Array([1,2])),false);
    assert.equal(r.write(1,20,new Float32Array([NaN,Infinity])),true);
    r.read(pair); assert.deepEqual([...pair],[0,0]);
});
test("Uhr: getrennte Frames, Loop, Seek, Stop",()=>{
    const c=new Clock(48000); c.loop(2,4); c.seek(2); c.playing=true;
    c.tick(); c.tick(); assert.equal(c.source,2); assert.equal(c.epoch,2);
    assert.equal(c.output,2); c.stop(); assert.equal(c.source,0); assert.equal(c.epoch,3);
});
test("Resampling 44,1/48 kHz in beide Richtungen",()=>{
    for(const [from,to] of [[44100,48000],[48000,44100]]) {
        const x=new Float32Array(from*2);
        for(let i=0;i<from;i++) x[i*2]=x[i*2+1]=Math.sin(2*Math.PI*440*i/from);
        const y=resample(x,from,to); assert.equal(y.length,to*2);
        let crossings=0; for(let i=1;i<to;i++) if(y[i*2]>0 && y[i*2-2]<=0) crossings++;
        assert.ok(Math.abs(crossings-440)<=1);
    }
});
test("Transport: begrenzte Credits, Epoch und Sequenz",()=>{
    const sent=[];const t=new Transport({postMessage:m=>sent.push(m)},1,48000);
    const block=(seq,epoch=0)=>pack({protocol_version:1,stream_id:1,epoch,seq,start_frame:BigInt(seq*256),nframes:256,channels:2,flags:0,sample_rate:48000},new Uint8Array(2048));
    for(let i=0;i<8;i++) assert.equal(t.push(block(i)),true);
    assert.equal(t.push(block(8)),false);t.acknowledge({epoch:0,seq:0,cursor:256});
    assert.equal(t.push(block(8)),true);t.reset(1,0);
    assert.equal(t.push(block(9)),false);assert.equal(t.push(block(0,1)),true);
});

import {RenderPath,limit,CEILING} from "../../web/js/realtime/worklet_processor.js";
test("Dry/Wet: Impuls und Latenzausgleich, zwei gleiche Spuren",()=>{
    const a=new RenderPath(3,1), b=new RenderPath(3,1);
    a.target=1;b.target=0;
    const wet=new Float32Array(16);wet[6]=wet[7]=0.25;
    a.wet.write(0,0,wet);b.wet.write(0,0,wet);
    for(let i=0;i<8;i++){
        const v=i===0?.25:0;a.sample(v,v);b.sample(v,v);
        assert.equal(a.out[0],b.out[0]);assert.equal(a.out[0],i===3?.25:0);
        assert.equal(limit(a.out[0]+b.out[0]),i===3?.5:0);
    }
});
test("Dry bitgleich, Limiter, nicht-endliche Samples und Jitter-Fallback",()=>{
    const p=new RenderPath(0,4);p.target=0;
    for(const v of [Math.fround(.123),-.25,0]){p.sample(v,v);assert.equal(p.out[0],v);}
    p.target=1;p.wet.write(0,3,new Float32Array(8).fill(.5));
    for(let i=0;i<4;i++)p.sample(0,0);
    assert.equal(p.out[0],.5);
    for(let i=1;i<=4;i++){p.sample(0,0);assert.equal(p.out[0],.5*(1-i/4));}
    assert.equal(p.wet.underruns,7);
    for(const v of [NaN,Infinity,-Infinity,2,-2,0]){const x=limit(v);assert.ok(Number.isFinite(x)&&Math.abs(x)<=CEILING);}
    p.reset(1,100);assert.equal(p.wet.write(0,100,new Float32Array([.5,.5])),false);
});

test("Worklet: variable Quanten, Start und Loop an exakten Frames",async()=>{
    let Processor;
    globalThis.AudioWorkletProcessor=class {
        constructor(){this.port={postMessage:m=>{this.status=m;}};}
    };
    globalThis.registerProcessor=(_,p)=>{Processor=p;};
    globalThis.sampleRate=48000;globalThis.currentFrame=0;
    try {
        await import("../../web/js/realtime/worklet_processor.js?fixture");
        const p=new Processor({processorOptions:{latencies:[0]}});
        const send=data=>p.port.onmessage({data});
        send({type:"reset",epoch:1,frame:3,source:7,active:true,loopLength:5});
        for(const n of [4,3,5]){
            const input=new Float32Array(n).fill(.125),out=[new Float32Array(n),new Float32Array(n)];
            p.process([[input,input]],[out]);
            for(let i=0;i<n;i++)assert.equal(out[0][i],currentFrame+i<3?0:.125);
            globalThis.currentFrame+=n;
        }
        send({type:"status"});assert.equal(p.status.cursor,12);assert.equal(p.status.epoch,2);
        assert.equal(p.status.source,11);assert.equal(p.status.streams[0].underruns,0);
        send({type:"reset",epoch:3,frame:12,source:0,active:false});
        const out=[new Float32Array(7),new Float32Array(7)];
        p.process([[new Float32Array(7).fill(1)]],[out]);assert.ok(out[0].every(v=>v===0));
    } finally {for(const k of ["AudioWorkletProcessor","registerProcessor","sampleRate","currentFrame"])delete globalThis[k];}
});
