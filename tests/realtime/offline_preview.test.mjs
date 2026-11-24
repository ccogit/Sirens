import test from "node:test";
import assert from "node:assert/strict";
import {createOfflinePreview} from "../../web/js/realtime/offline_preview.js";

function fakeCore(events) {
  return {
    context:{createBuffer(ch,n,rate){
      const data=Array.from({length:ch},()=>new Float32Array(n));
      return {sampleRate:rate,getChannelData:i=>data[i]};
    }},
    sources:[{}],param:()=>{},stopSources:()=>events.push("stop"),
    play:buffers=>{events.push("play");assert.equal(buffers[0].sampleRate,44100);},
    destroy:async()=>events.push("destroy")
  };
}
test("Mix vorbereiten startet nichts; Vorhören schließt Mock zuerst",async()=>{
  const events=[];
  const p=createOfflinePreview({beforePlay:async()=>events.push("close mock"),
    openCore:async()=>{events.push("open");return fakeCore(events);}});
  await p.prepare(new Float32Array([.1,.2,.3,.4]),44100);
  assert.deepEqual(events,[]);
  await p.play();
  assert.deepEqual(events,["close mock","open","play"]);
  assert.equal(p.playing,true);
  await p.stop(true);
  assert.deepEqual(events,["close mock","open","play","stop","destroy"]);
  assert.equal(p.ready,false);
});
test("Panic während Core-Öffnung verhindert späte Wiedergabe",async()=>{
  const events=[];
  let entered, resume;
  const opened=new Promise(r=>{entered=r;});
  const p=createOfflinePreview({openCore:()=>{entered();return new Promise(r=>{resume=r;});}});
  await p.prepare(new Float32Array(4),44100);
  const starting=p.play();await opened;
  const stopping=p.stop(true);
  resume(fakeCore(events));
  await Promise.all([starting,stopping]);
  assert.deepEqual(events,["destroy"]);
  assert.equal(p.playing,false);assert.equal(p.ready,false);
});
