import test from "node:test";
import assert from "node:assert/strict";
import {AudioCore} from "../../web/js/realtime/audio_core.js";
import {makeRenderPlan, fillRenderPlan} from "../../web/js/realtime/shell.js";
import {pack} from "../../web/js/realtime/pcm.js";

let Processor;
globalThis.AudioWorkletProcessor=class {
  constructor(){this.port={postMessage:()=>{}};}
};
globalThis.registerProcessor=(_,p)=>{Processor=p;};
globalThis.sampleRate=48000;
globalThis.currentFrame=0;
await import("../../web/js/realtime/worklet_processor.js?pump34");
globalThis.AudioWorkletNode=class {
  constructor(_context,_name,options){
    this.processor=new Processor(options);
    this.port={postMessage:m=>this.processor.port.onmessage({data:m})};
    this.processor.port.postMessage=m=>this.port.onmessage?.({data:m});
  }
  connect(){}
  disconnect(){}
};

function setup(rate=48000){
  globalThis.sampleRate=rate;globalThis.currentFrame=0;
  const context={sampleRate:rate,currentTime:0,destination:{}};
  const core=new AudioCore(context,[0]);
  clearInterval(core.timer);
  const pending=[];
  const render=async(_session,p)=>{pending.push({due:currentFrame+rate/20,p});};
  const packet=p=>pack({protocol_version:1,stream_id:1,epoch:p.audio_epoch,seq:p.seq,
    start_frame:BigInt(p.start_frame),nframes:p.nframes,channels:2,
    flags:p.seek?1:0,sample_rate:48000},new Uint8Array(p.nframes*8));
  function deliver(){
    while(pending.length && pending[0].due<=currentFrame)
      core.push(packet(pending.shift().p));
  }
  const step=rate/100, input=new Float32Array(step), out=[new Float32Array(step),new Float32Array(step)];
  function tick(){
    core.node.processor.process([[input,input]],[out]);
    globalThis.currentFrame+=step;context.currentTime=currentFrame/rate;
  }
  function status(){core.node.port.postMessage({type:"status"});}
  return {core,pending,render,packet,deliver,tick,status};
}

async function simulate(rate,preload){
  const {core,render,deliver,tick,status}=setup(rate);
  const length=rate*4, start=rate*22/100;
  const state=core.reset(0,true,start,length);
  const plan=makeRenderPlan(state,0,length,length);
  const view=preload?core:Object.create(core,{loopPlan:{value:null}});
  // Der Vergleichspfad sieht den Plan nicht, wie die frühere Pumpe.
  if(!preload){
    view.noteRenderRequest=core.noteRenderRequest.bind(core);
    view.forgetRenderRequest=core.forgetRenderRequest.bind(core);
  }
  core.param(1,{mix:1});
  for(let i=0;i<40035;i++){
    deliver();
    if(i%2===0){
      status();
      await fillRenderPlan(plan,view,{epoch:0},render);
    }
    tick();
  }
  status();
  assert.equal(core.clock.epoch,state.epoch+100);
  return core.status.streams[0];
}

test("WP34: 100 Loop-Wechsel bei 50 ms Produzentenlatenz und Regression ohne Vorlauf",async()=>{
  assert.equal((await simulate(48000,true)).unexpectedUnderruns,0);
  assert.ok((await simulate(48000,false)).unexpectedUnderruns>0);
});

test("WP34: manueller Seek mit erwartetem Aussetzer und Ablehnung alter Pakete",async()=>{
  const {core,render,packet,deliver,tick,status}=setup();
  const old=core.reset(0,true,0,192000);
  const state=core.reset(0,true,0,192000,true);
  const plan=makeRenderPlan(state,0,192000,192000,true);
  core.param(1,{mix:1});
  assert.equal(core.push(packet({audio_epoch:old.epoch,seq:0,start_frame:0,nframes:256})),false);
  let first;
  const submit=async(s,p)=>{first??=p;await render(s,p);};
  for(let i=0;i<100;i++){
    deliver();
    if(i%2===0){status();await fillRenderPlan(plan,core,{epoch:1},submit);}
    tick();
  }
  status();
  assert.equal(first.seek,true);
  assert.equal(first.seq,0);
  assert.ok(core.status.streams[0].expectedUnderruns>0);
  assert.equal(core.status.streams[0].unexpectedUnderruns,0);
});
