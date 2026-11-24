import test from "node:test";
import assert from "node:assert/strict";
import {createBeatGrid} from "../../web/js/realtime/beat_grid.js";
import {MutationScheduler,DSP_MODE,dspMutationAdapters,mutationSessionParameters} from "../../web/js/realtime/mutation_scheduler.js";
const grid=createBeatGrid({confidence:1,bpm:120,beat0:0,bar0:0,tempo_map:[{source_frame:160000,bpm:100}]},8000);
const cap=(id,available=true,mock=false,mode="lookahead")=>({id,available,mock,mode});
const safe=async p=>({track:new Float32Array(p.endFrame-p.frame).fill(.2)});
function fixture(opts={}){
  const events=[], applied=[];let originals=0;
  const s=new MutationScheduler({grid,adapters:new Map([["dsp-rack",safe],["rave",safe],["after",safe]]),
    capabilities:()=>({capabilities:[cap("rave"),cap("after")]}),apply:(p,r)=>applied.push(p),original:()=>originals++,log:e=>events.push(e),...opts});
  return {s,events,applied,originals:()=>originals};
}
async function run(seed,bars){
  const {s,events}=fixture({seed,bars,switchBars:16,maxAssets:3});s.start(1);
  for(let i=0;i<12;i++){const p=s.plan();assert.ok(p);assert.equal(s.plan(),null);const r=await s.prepare(p);
    assert.equal(s.advance(p.frame-1,r),false);assert.equal(s.advance(p.frame,r),true);
    assert.equal(p.frame,grid.barToFrame(p.bar));assert.equal(p.bar,1+i*bars);}
  assert.ok(s.assets<=3);return events;
}
test("Seed, 4/8/16 Takte und Quota",async()=>{
  for(const bars of [4,8,16])assert.deepEqual(await run(42,bars),await run(42,bars));
  assert.notDeepEqual(await run(42,4),await run(43,4));
});
test("Registry-Freigabe, Mock und Offline bleiben gesperrt",()=>{
  let capabilities=[cap("rave",false),cap("after",true,true)];
  const {s}=fixture({capabilities:()=>({capabilities})});
  assert.equal(s.mode,DSP_MODE);assert.deepEqual(s.backends.map(b=>b.id),["dsp-rack"]);
  capabilities=[cap("rave"),cap("after",true,false,"offline")];
  assert.deepEqual(s.backends.map(b=>b.id),["dsp-rack","rave"]);
});
test("Pegel, verspäteter Block, Override, Stop und Original",async()=>{
  const {s,originals}=fixture({maxAssets:0});s.start(0);
  let p=s.plan(),r=await s.prepare(p);r.track[0]=.99;
  assert.equal(s.advance(p.frame,r),false);
  p=s.plan();r=await s.prepare(p);assert.equal(s.advance(p.frame+1,r),false);
  p=s.plan();r=await s.prepare(p);s.override(p.frame-1,{intensity:0});
  assert.equal(s.advance(p.frame,r),false);
  p=s.plan();assert.equal(p.amount,0);s.returnToOriginal(p.frame-2);
  assert.equal(s.plan(),null);assert.equal(originals(),1);assert.equal(s.advance(p.frame),false);
});
test("Abbruch, Queue und kein erneuter Start alter Arbeit",async()=>{
  let finish,signal;const {s}=fixture({maxAssets:0,adapters:new Map([["dsp-rack",(p,x,a)=>{signal=a;return new Promise(resolve=>{finish=()=>resolve({track:new Float32Array(p.endFrame-p.frame)});});}]])});
  s.start(0);const p=s.plan(),pending=s.prepare(p);s.stop(1);assert.equal(signal.aborted,true);
  s.start(1);assert.equal(s.plan(),null);finish();assert.equal(await pending,null);assert.ok(s.plan());
});
test("Modellwechsel und Freigabeentzug",async()=>{
  let caps=[cap("rave"),cap("after")];const {s}=fixture({adapters:new Map([["rave",safe],["after",safe]]),maxAssets:20,switchBars:16,capabilities:()=>({capabilities:caps})});
  s.start(0);let prev=null,last=-Infinity;
  for(let i=0;i<8;i++){const p=s.plan();if(p.backend!==prev){assert.ok(p.bar-last>=16);prev=p.backend;last=p.bar;}const r=await s.prepare(p);assert.equal(s.advance(p.frame,r),true);}
  const p=s.plan(),r=await s.prepare(p);caps=[];assert.equal(s.advance(p.frame,r),false);
});
test("DSP-Rack und Performance-Tools mit synthetischem PCM",async()=>{
  const adapters=dspMutationAdapters({drum:true,crossover:true,acid:true});
  const dry=new Float32Array(2048).fill(.2),input={rate:8000,dry,drum:{stems:{drums:dry}},crossover:{grid:{confidence:1,bpm:120,beat0:0,bar0:0},targetKey:"C major",songs:[{id:"synthetisch",track:dry,grid:{confidence:1,bpm:120,beat0:0,bar0:0},key:"C major"}]},acid:{bass:dry,onsets:[0]}};
  for(const [id,adapter] of adapters){const r=await adapter({amount:.5,energy:.5,peak:.5,seed:42,block:0},input);assert.equal(r.track.length,dry.length,id);assert.ok(r.track.every(v=>Number.isFinite(v)&&Math.abs(v)<=.5),id);}
  assert.ok(dry.every(v=>Math.abs(v-.2)<1e-7));
});
test("Session-Projektion auf gültige numerische Parameter",()=>{
  const {s,events}=fixture();s.start(0);s.plan();s.stop(1);
  for(const event of events)for(const p of mutationSessionParameters(event)){assert.match(p.name,/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/);assert.ok(Number.isFinite(p.value));}
});

test("Freigabe vor Vorbereitung entzogen und ungültige PCM-Werte",async()=>{
  let caps=[cap("rave")],calls=0;
  const {s}=fixture({adapters:new Map([["rave",async p=>{calls++;return {track:new Float32Array(p.endFrame-p.frame).fill(NaN)};}]]),capabilities:()=>({capabilities:caps})});
  s.start(0);let p=s.plan();caps=[];assert.equal(await s.prepare(p),null);assert.equal(calls,0);
  caps=[cap("rave")];s.advance(p.frame);p=s.plan();assert.equal(await s.prepare(p),null);
  assert.equal(await s.prepare(p),null);assert.equal(calls,1);assert.equal(s.advance(p.frame),false);
});
