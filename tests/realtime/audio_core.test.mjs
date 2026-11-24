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
