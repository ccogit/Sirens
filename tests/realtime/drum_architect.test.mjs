import test from "node:test";
import assert from "node:assert/strict";
import {drumArchitect,drumPreset,savePreset,loadPreset,PerformanceScheduler} from "../../web/js/realtime/drum_architect.js";
const rate=48000, grid={bpm:123,beat0:0,bar0:0,confidence:1,tempo_map:[]};
test("Drum: Raster, Groove, Velocity, Pegel, Korrektur, fehlende Stems",()=>{
 const length=48000, drums=new Float32Array(length);
 const x=drumArchitect({rate,length,stems:{drums},grid,onsets:[{kind:"kick",frame:23416,velocity:.7}],preset:{quantize:1}});
 assert.equal(x.events[0].frame,Math.round(rate*60/123));assert.equal(x.events[0].velocity,.7);assert.ok(x.warnings.length);assert.ok(x.track.every(v=>Math.abs(v)<=.800001));
 const y=drumArchitect({rate,length,stems:{drums},onsets:[{kind:"kick",frame:4,velocity:1}],preset:{corrections:[{index:0,frame:9,velocity:.4}]}});
 assert.equal(y.events[0].frame,9);assert.equal(y.events[0].velocity,.4);
 const p=drumPreset({mode:"replace",gain:.3});assert.deepEqual(loadPreset("drum",savePreset("drum",p),drumPreset),p);
});
test("Gemeinsamer Scheduler: Play/Stop/Seek am Core",()=>{
 const calls=[],core={rate,context:{createBuffer:(_,length)=>({length,copyToChannel(){}})},play:(_,o)=>calls.push(o.source),stop:()=>calls.push("stop")};
 const s=new PerformanceScheduler(core);s.setTrack(new Float32Array(100));s.play();s.seek(40);s.stop();s.seek(20);s.play();assert.deepEqual(calls,[0,40,"stop",20]);
});
