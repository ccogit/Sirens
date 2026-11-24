import test from "node:test";
import assert from "node:assert/strict";
import {PadScheduler, PAD_TYPES} from "../../web/js/realtime/pad_scheduler.js";
const grid={bpm:120,beat0:0,bar0:0,confidence:0.9};
const make=(options={})=>new PadScheduler({grid,sampleRate:48000,p95Ms:430,...options});
const job=(type="Rise",bars=1)=>({type,bars,prompt:"Techno",seed:1,strength:0.7});
const clip=(frames=96000)=>({frames,sampleRate:48000});
test("sechs Pad-Typen, Vorhören und exakte Taktgrenze",()=>{
  for(const type of PAD_TYPES){
    const s=make(), j=s.request(job(type),1000);
    assert.equal(j.startFrame,96000);
    assert.equal(s.ready(j.id,clip(),21640).status,"ready");
    assert.deepEqual(s.preview(j.id),clip());
    const plan=s.take(j.id,22000);
    assert.equal(plan.startFrame,96000);
    assert.equal(plan.crossfadeFrames,960);
    assert.equal(plan.status,"scheduled");
  }
});
test("Verspätung verschiebt, weitere Verspätung oder späte Freigabe bleibt dry",()=>{
  const s=make(), j=s.request(job(),0);
  assert.equal(s.ready(j.id,clip(),j.deadlineFrame+1).startFrame,192000);
  assert.equal(s.take(j.id,100000).startFrame,192000);
  const t=make(), k=t.request(job(),0);
  assert.equal(t.ready(k.id,clip(),192000).status,"dry");
  const u=make(), l=u.request(job(),0);
  u.ready(l.id,clip(),1000);
  assert.equal(u.take(l.id,96000).status,"dry");
});
test("Queue begrenzt; unsicheres BeatGrid sperrt",()=>{
  const s=make({maxPending:2});
  const a=s.request(job(),0);
  s.request(job("Fill"),0);
  assert.equal(s.request(job("Drop"),0).status,"dry");
  s.cancel(a.id);
  assert.equal(s.request(job("Drop"),0).status,"rendering");
  assert.equal(make({grid:{...grid,confidence:0.1}}).request(job(),0).status,"dry");
});
test("Stretch-Grenze, Warnung und Phrasenraster",()=>{
  const s=make({phraseBars:4}), j=s.request(job(),0);
  assert.equal(j.startFrame,384000);
  assert.ok(s.ready(j.id,clip(98000),1000).warning);
  const t=make(), k=t.request(job(),0);
  assert.equal(t.ready(k.id,clip(110000),1000).status,"dry");
});
