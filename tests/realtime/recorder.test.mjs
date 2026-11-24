import {test} from "node:test";
import assert from "node:assert/strict";
import {Capture,Recorder,BLOCK,POOL} from "../../web/js/realtime/recorder.js";
test("Variable Quanten, Stereo und Restblock",()=>{
    const out=[], c=new Capture(m=>out.push(m));
    for(let i=0;i<POOL;i++)c.recycle(new ArrayBuffer(BLOCK*8));
    c.process(Float32Array.of(1));assert.equal(out.length,0);
    c.start();
    c.process(new Float32Array(BLOCK-1).fill(.25),new Float32Array(BLOCK-1).fill(-.25));
    c.process(Float32Array.of(.5,.75),Float32Array.of(-.5,-.75));
    c.stop();
    assert.deepEqual(out.map(x=>x.type),["block","block","ended"]);
    assert.equal(out[0].frames,BLOCK);
    assert.equal(out[1].startFrame,BLOCK);
    assert.equal(out[1].frames,1);
    assert.equal(new DataView(out[1].buffer).getFloat32(4,true),-.75);
    assert.equal(out[2].frames,BLOCK+1);
});
test("Begrenzter Puffer meldet Abbruch",()=>{
    const out=[],c=new Capture(m=>out.push(m));
    for(let i=0;i<POOL;i++)c.recycle(new ArrayBuffer(BLOCK*8));
    c.start();
    for(let i=0;i<=POOL;i++)c.process(new Float32Array(BLOCK));
    assert.equal(out.length,POOL+1);
    assert.equal(out.at(-1).frames,POOL*BLOCK);
    assert.match(out.at(-1).error,/erschöpft/);
});
test("Serieller Upload und Bestätigung",async()=>{
    const sent=[],messages=[];
    const r=new Recorder({postMessage:m=>messages.push(m.type)},async(start,bytes)=>{
        sent.push([start,bytes.length]);return start+bytes.length/8;
    },async()=>{});
    r.start();assert.equal(messages.filter(x=>x==="recycle").length,POOL);
    r.receive({type:"block",buffer:new ArrayBuffer(BLOCK*8),frames:3,startFrame:0});
    r.receive({type:"block",buffer:new ArrayBuffer(BLOCK*8),frames:2,startFrame:3});
    const done=r.stop();r.receive({type:"ended",frames:5,error:null});
    assert.deepEqual(await done,{frames:5,error:null});
    assert.deepEqual(sent,[[0,24],[3,16]]);
});
test("Fehlende Bestätigung meldet Fehler",async()=>{
    const r=new Recorder({postMessage:()=>{}},async()=>0,async()=>{});
    r.start();
    r.receive({type:"block",buffer:new ArrayBuffer(BLOCK*8),frames:1,startFrame:0});
    assert.match((await r.done).error,/Bestätigung/);
});
