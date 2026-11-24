import test from "node:test";
import assert from "node:assert/strict";
import {stemCrossover,crossoverPreset} from "../../web/js/realtime/stem_crossover.js";
import {savePreset,loadPreset} from "../../web/js/realtime/drum_architect.js";
const rate=48000,grid={bpm:123,beat0:0,bar0:0,confidence:1,tempo_map:[]};
test("Crossover: Raster, Tonart- und Stretch-Warnung, Pegel und Preset",()=>{
 const track=new Float32Array(rate).fill(.4),p=crossoverPreset({songs:[{id:"a",start:23410}]});
 const x=stemCrossover({rate,length:rate,grid,targetKey:"C major",songs:[{id:"a",track,grid,key:"F# major"},{id:"b",track,grid:{...grid,bpm:180},key:"C major"}],preset:p});
 assert.equal(x.events[0].frame,Math.round(rate*60/123));assert.equal(x.events.length,1);assert.ok(x.warnings.some(w=>w.includes("Tonartkonflikt")));assert.ok(x.warnings.some(w=>w.includes("Stretch-Limit")));assert.ok(x.track.every(v=>Math.abs(v)<=.800001));
 assert.deepEqual(loadPreset("crossover",savePreset("crossover",p),crossoverPreset),p);
});
