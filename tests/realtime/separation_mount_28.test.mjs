import test from "node:test";
import assert from "node:assert/strict";
import {mountSeparationJobs} from "../../web/js/realtime/advanced_stems.js";

class Element {
  constructor(tag,doc){this.tag=tag;this.ownerDocument=doc;this.children=[];this.events={};this.value="";this.textContent="";}
  setAttribute(){}
  removeAttribute(){}
  append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);if(n.tag==="option"&&!this.value)this.value=n.value;}}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);}
  addEventListener(name,fn){this.events[name]=fn;}
  pause(){}
}
const doc={createElement:t=>new Element(t,doc)};
const id="a".repeat(32);
test("Mount startet nichts; Panic wartet auf Job-ID und fordert Cancel an",async()=>{
  const host=new Element("div",doc),calls=[];
  let resolveStart;
  const api={start:(path,model)=>{calls.push(["start",path,model]);return new Promise(r=>{resolveStart=r;});},
    cancel:async jid=>calls.push(["cancel",jid])};
  const dispose=mountSeparationJobs(host,{selectedPath:()=>"Test.wav",api,onMix:()=>assert.fail("Keine späte Mischung")});
  const panel=host.children[0];
  assert.equal(panel.children.some(el=>el.tag==="audio"),false);
  assert.deepEqual(calls,[]);
  const start=panel.children.find(el=>el.textContent==="Offline trennen");
  const running=start.events.click();
  const done=dispose();
  resolveStart({id,state:"queued"});
  await Promise.all([running,done]);
  assert.deepEqual(calls,[["start","Test.wav","roformer"],["cancel",id]]);
  assert.equal(host.children.length,0);
});
test("Gesperrte Fähigkeit startet keinen Job",async()=>{
  const host=new Element("div",doc);
  const dispose=mountSeparationJobs(host,{selectedPath:()=>"Test.wav",canStart:()=>false,
    api:{start:()=>assert.fail("Nicht verfügbar")}});
  const start=host.children[0].children.find(el=>el.textContent==="Offline trennen");
  assert.equal(start.disabled,true);
  await start.events.click();await dispose();
});
