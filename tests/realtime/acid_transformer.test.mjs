import test from "node:test";
import assert from "node:assert/strict";
import {acidTransformer,acidPreset} from "../../web/js/realtime/acid_transformer.js";
import {savePreset,loadPreset} from "../../web/js/realtime/drum_architect.js";
const rate=48000,grid={bpm:123,beat0:0,bar0:0,confidence:1,tempo_map:[]};
test("Acid: Noten, Raster, Bass stumm, Pegel, Onset-Warnung, Preset",()=>{
 const bass=new Float32Array(rate).fill(.2),p=acidPreset({hideBass:true,quantize:1,drive:4,octave:1});
 const x=acidTransformer({rate,length:rate,bass,grid,notes:[[.49,.7,36,.9],[.7,.9,39,.5]],preset:p});
 assert.equal(x.events[0].frame,Math.round(rate*60/123));assert.equal(x.track[0],0);assert.ok(x.track.some(v=>v!==0));assert.ok(x.track.every(v=>Math.abs(v)<=.800001));
 assert.ok(acidTransformer({rate,length:rate,onsets:[{frame:1}]}).warnings.length);
 assert.deepEqual(loadPreset("acid",savePreset("acid",p),acidPreset),p);
});

test("Slide bleibt über mehrere tatsächlich gespielte Noten verbunden",()=>{
 const notes=[[0,.1,36,1],[.1,.2,39,1],[.2,.3,43,1]];
 const slid=acidTransformer({rate,length:rate,notes,preset:{slide:.06}}).track;
 const plain=acidTransformer({rate,length:rate,notes,preset:{slide:0}}).track;
 assert.ok(slid.slice(9600,12000).some((v,i)=>v!==plain[9600+i]));
});
