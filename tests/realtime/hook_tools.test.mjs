import test from "node:test";
import assert from "node:assert/strict";
import {HOOK_TOOLS,hookState,descriptorControls,mountHookTools} from "../../web/js/realtime/hook_tools.js";

test("alle Hooks unabhängig von Reihenfolge und Registry-Vollständigkeit sichtbar",()=>{
  const ids=HOOK_TOOLS.map(([id])=>id);
  assert.equal(ids.length,13);
  for(const id of ids){
    assert.equal(hookState(id,[]).enabled,false);
    assert.match(hookState(id,[]).text,/nicht gemessen/i);
    const cap={id,available:true,controls:[]};
    assert.equal(hookState(id,[{id:"mock",available:true},cap]).enabled,false);
    assert.equal(hookState(id,[cap],{wired:true,measured:true}).enabled,true);
    assert.equal(hookState(id,[cap],{wired:true,measured:true,error:new Error("503")}).enabled,false);
  }
});
test("Deskriptorgrenzen und ganzzahlige Seeds",()=>{
  assert.deepEqual(descriptorControls([
    {name:"seed",min:0,max:100,default:0},
    {name:"latent_0",min:-1,max:1,default:0},
    {name:"invalid",min:0,max:1,default:2}
  ]).map(c=>c.step),[1,"any"]);
});
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.textContent="";this.attrs={};}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=v;}
}
test("Karten enthalten deaktivierte Aktionen und dynamische Regler",()=>{
  const host=new Element("div");
  const cards=mountHookTools(host,{document:{createElement:t=>new Element(t)}});
  cards.paint([{id:"rave",available:false,controls:[{name:"latent_0",min:-1,max:1,default:0}]}]);
  assert.equal(host.children.length,HOOK_TOOLS.length);
  for(const card of host.children){
    assert.ok(card.children[0].textContent);
    assert.ok(card.children.slice(3).every(b=>b.disabled));
  }
  const rave=host.children.find(c=>c.children[0].textContent==="RAVE");
  const input=rave.children[2].children[0].children[0];
  assert.equal(input.attrs["aria-label"],"latent_0");
  assert.equal(input.min,"-1");
  assert.equal(input.disabled,true);
  cards.paint([],new Error("API"));
  assert.match(rave.children[1].textContent,/Fehler/);
  cards.destroy();assert.equal(host.children.length,0);
});
