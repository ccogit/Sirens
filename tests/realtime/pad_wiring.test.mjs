import test from "node:test";
import assert from "node:assert/strict";
import {PadController,keyCode} from "../../web/js/realtime/pad_bar.js";
import {createPadAudio} from "../../web/js/realtime/pad_audio.js";

const rate=48000, caps=[{id:"stable_audio",available:true,mock:false,mode:"lookahead"}];
function fixture(capabilities=caps, confidence=1) {
  let now=0;const calls=[];
  const audio={now:()=>now,preview:()=>calls.push("preview"),stopPreview:()=>calls.push("stopPreview"),
    schedule:(p)=>{calls.push(p);return true;},reset:()=>calls.push("reset")};
  const backend={open:async()=>calls.push("load/warm"),close:async()=>calls.push("unload"),
    generate:async p=>{calls.push(p);return {assetId:"a".repeat(32),
      buffer:{numberOfChannels:2,length:p.duration*rate,sampleRate:rate}};}};
  const controller=new PadController({capabilities,backend,audio,grid:{bpm:120,bar0:0,beat0:0,confidence},
    key:"C Dur",keyConfidence:.9,sampleRate:rate,p95Ms:430});
  return {controller,calls,backend,setNow:f=>{now=f;}};
}
const request={type:"Fill",bars:1,seed:7,strength:.5};
test("nur Nutzeraktion lädt; Dateijob-Kandidat, Freigabe und Entladen",async()=>{
  const {controller:c,calls}=fixture();
  assert.equal(await c.open(),false);
  assert.deepEqual(calls,[]);
  assert.equal(await c.open(true),true);
  const p=await c.request(request);
  assert.equal(p.status,"ready");
  assert.deepEqual(calls[1],{pad_type:1,bars:1,seed:7,strength:.5,duration:2,bpm:120,key:1});
  assert.equal(c.preview(),true);
  const plan=c.take();
  assert.equal(plan.startFrame,96000);
  assert.equal(plan.crossfadeFrames,960);
  assert.equal(plan.status,"scheduled");
  await c.close();
  assert.deepEqual(calls.slice(-2),["reset","unload"]);
});
test("gesperrtes Modell und unsicheres BeatGrid starten keinen Worker",async()=>{
  for(const f of [fixture([{...caps[0],available:false}]),fixture(caps,.1),fixture([])]){
    assert.equal(f.controller.state,"disabled");
    assert.equal(await f.controller.open(true),false);
    assert.deepEqual(f.calls,[]);
  }
  assert.equal(keyCode("Eb Moll",.9),16);
  assert.equal(keyCode("C Dur",.1),0);
});
test("verspätetes Asset verschieben oder verwerfen; nach Close keine Freigabe",async()=>{
  for(const [at,expected] of [[97000,"ready"],[195000,"dry"]]){
    const {controller:c,backend,setNow}=fixture();
    await c.open(true);
    let finish;backend.generate=()=>new Promise(r=>{finish=r;});
    const pending=c.request(request);setNow(at);
    finish({assetId:"a".repeat(32),buffer:{numberOfChannels:2,length:96000,sampleRate:rate}});
    const result=await pending;
    assert.equal(result.status,expected);
    if(expected==="ready")assert.equal(result.startFrame,192000);
    await c.close();assert.equal(c.take().status,"dry");
  }
  const {controller:c,backend}=fixture();
  await c.open(true);
  let finish;backend.generate=()=>new Promise(r=>{finish=r;});
  const pending=c.request(request);
  await c.close();
  finish({assetId:"a".repeat(32),buffer:{numberOfChannels:2,length:96000,sampleRate:rate}});
  assert.equal((await pending).status,"dry");
});
test("Audio-Einsatz nutzt ganzzahlige Frame-Adresse, Crossfade und Epoch",()=>{
  const events=[];
  const param=()=>({value:1,setValueAtTime:(...a)=>events.push(["set",...a]),
    linearRampToValueAtTime:(...a)=>events.push(["ramp",...a]),cancelScheduledValues:()=>{}});
  const src={playbackRate:{value:1},connect(){},disconnect(){},start:t=>events.push(["start",t]),
    stop:t=>events.push(["stop",t])};
  const core={rate,clock:{playing:true,epoch:1},frame:()=>1000,transports:[{},{}],node:{},
    context:{currentTime:1000/rate,createBufferSource:()=>src,createGain:()=>({gain:param(),connect(){},disconnect(){}})}};
  const audio=createPadAudio({core,dryGain:{gain:param()},anchor:()=>({epoch:1,frame:1000,source:0})});
  const plan={status:"scheduled",startFrame:96000,durationFrames:96000,crossfadeFrames:960,strength:.5,playbackRate:1};
  assert.equal(audio.schedule(plan,{sampleRate:rate}),true);
  assert.deepEqual(events.filter(e=>e[0]==="start"),[["start",97000/rate]]);
  assert.ok(events.some(e=>e[0]==="ramp"&&e[1]===.5&&e[2]===97960/rate));
  assert.equal(audio.schedule(plan,{sampleRate:rate}),false);
  core.clock.epoch=2;assert.equal(audio.schedule(plan,{sampleRate:rate}),false);
  audio.reset();
});
