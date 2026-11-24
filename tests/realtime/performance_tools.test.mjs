import test from "node:test";
import assert from "node:assert/strict";
import {createBeatGrid} from "../../web/js/realtime/beat_grid.js";
import {drumArchitect} from "../../web/js/realtime/drum_architect.js";
import {acidTransformer} from "../../web/js/realtime/acid_transformer.js";
import {stemCrossover} from "../../web/js/realtime/stem_crossover.js";
import {demos,rate,grid} from "./performance_fixtures.mjs";
test("Neun reproduzierbare Demos: Signal, begrenzte Pegel und Warnungen",()=>{
 for(const [name,render] of Object.entries(demos)){
   const r=render();assert.ok(r.track.some(v=>v!==0),name);assert.ok(r.track.every(v=>Number.isFinite(v)&&Math.abs(v)<=.800001),name);
   assert.deepEqual(render(),r,name);
 }
 assert.ok(demos["crossover-conflict"]().warnings.some(x=>x.includes("Stretch-Limit")));
});
test("Alle Werkzeuge: absolute Rasterberechnung über zehn Minuten",()=>{
 const rate=8000,length=rate*600,grid={bpm:123,beat0:0,bar0:0,confidence:1,tempo_map:[]};
 const g=createBeatGrid(grid,rate),beat=1229,expected=Math.round(beat*60*rate/123),f=expected+2;
 for(let b=0;b<=beat;b++)assert.equal(g.beatToFrame(b),Math.round(b*60*rate/123));
 const drums=new Float32Array(length);
 const d=drumArchitect({rate,length,grid,stems:{drums},onsets:[{frame:f,kind:"kick",velocity:1}],preset:{quantize:1}});
 assert.equal(d.events[0].frame,expected);assert.notEqual(d.track[expected],0);
 const a=acidTransformer({rate,length,grid,onsets:[{frame:f}],preset:{quantize:1}});
 assert.equal(a.events[0].frame,expected);
 const c=stemCrossover({rate,length,grid,targetKey:"C Dur",songs:[{id:"a",grid,key:"C Dur",track:new Float32Array([1])}],preset:{songs:[{id:"a",start:f}]}});
 assert.equal(c.events[0].frame,expected);assert.equal(c.events[0].sourceFrame,0);
});
