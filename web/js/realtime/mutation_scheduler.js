// WP18: reine, framebasierte Steuerung. Keine Timer, Worker oder Audio-Kontexte.
export const DSP_MODE = "Reduzierter DSP-Modus";
const DSP = Object.freeze([
  {id:"dsp-rack", kind:"dsp", assets:0},
  {id:"drum", kind:"dsp", assets:0},
  {id:"crossover", kind:"dsp", assets:0},
  {id:"acid", kind:"dsp", assets:0},
]);
const neural = new Set(["demon","rave","after"]);
const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
function integer(v,min,max,name) {
  if(!Number.isSafeInteger(v)||v<min||v>max) throw new RangeError(name);
  return v;
}
function unit(v,name) {
  if(!Number.isFinite(v)||v<0||v>1) throw new RangeError(name);
  return v;
}
// Nur angebotene, tatsächlich verfügbare Registry-Einträge und vorhandene Adapter.
export function mutationBackends(capabilities, adapters) {
  const list=DSP.filter(b=>adapters.has(b.id));
  for(const c of capabilities?.capabilities??[]) {
    if(neural.has(c.id)&&c.available===true&&c.mock===false&&
       ["streaming","lookahead"].includes(c.mode)&&adapters.has(c.id)&&
       !list.some(b=>b.id===c.id)) list.push({id:c.id,kind:"neural",assets:1,mode:c.mode});
  }
  return list.sort((a,b)=>a.id.localeCompare(b.id,"en"));
}
function random(seed, block, salt) {
  let x=(seed^Math.imul(block+1,0x9e3779b9)^salt)>>>0;
  x=Math.imul(x^(x>>>16),0x21f0aaad);
  x=Math.imul(x^(x>>>15),0x735a2d97);
  return ((x^(x>>>15))>>>0)/4294967296;
}
export class MutationScheduler {
  constructor({grid, adapters, capabilities=()=>({capabilities:[]}), apply, original, log=()=>{},
    seed=0, bars=4, intensity=.5, energy=.5, maxPeak=.8, maxAssets=16, maxPending=1, switchBars=8}={}) {
    if(!grid?.nextBar||!grid?.barToFrame||!grid?.frameToBar||!(adapters instanceof Map)||
       typeof apply!=="function"||typeof original!=="function") throw new TypeError("Mutation-Anbindung fehlt");
    if(![4,8,16].includes(bars)) throw new RangeError("Taktblock");
    this.grid=grid; this.adapters=adapters; this.capabilities=capabilities;
    this.apply=apply; this.original=original; this.log=log;
    this.seed=integer(seed,0,0xffffffff,"Seed"); this.bars=bars;
    this.intensity=unit(intensity,"Intensität"); this.energy=unit(energy,"Energie");
    this.maxPeak=unit(maxPeak,"Pegelgrenze"); this.maxAssets=integer(maxAssets,0,1000,"Asset-Quota");
    this.maxPending=integer(maxPending,1,8,"Warteschlange"); this.switchBars=integer(switchBars,4,64,"Modellwechsel");
    this.pending=new Map(); this.assets=0; this.serial=0; this.running=false;
    this.lastNeural=null; this.lastSwitch=-Infinity; this.lastFrame=0;
  }
  get backends(){return mutationBackends(this.capabilities(),this.adapters);}
  get mode(){return this.backends.some(b=>b.kind==="neural")?"Freigegebene neuronale Backends verfügbar":DSP_MODE;}
  event(type,frame,extra={}){this.log(Object.freeze({type,frame,seed:this.seed,bars:this.bars,...extra}));}
  start(frame) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    if(this.running) throw new Error("Mutation bereits aktiv");
    this.running=true; this.lastFrame=frame; this.anchor=Math.round(this.grid.frameToBar(this.grid.nextBar(frame)));
    this.block=0; this.next=this.grid.barToFrame(this.anchor);
    this.lastNeural=null; this.lastSwitch=-Infinity;
    this.event("start",frame,{intensity:this.intensity,energy:this.energy,mode:this.mode});
  }
  // Vorbereitung nur aus dem Controller, nicht aus dem AudioWorklet. Pro Plan
  // höchstens ein Asset; auch abgebrochene Anfragen verbrauchen die Quota.
  plan() {
    if(!this.running||this.pending.size>=this.maxPending||
       [...this.pending.values()].some(p=>p.frame===this.next)) return null;
    const bar=this.anchor+this.block*this.bars;
    const available=this.backends.filter(b=>b.kind==="dsp"||
      (this.assets+b.assets<=this.maxAssets&&
       (!this.lastNeural||b.id===this.lastNeural||bar-this.lastSwitch>=this.switchBars)));
    if(!available.length) return null;
    const b=available[Math.floor(random(this.seed,this.block,1)*available.length)];
    const amount=clamp(this.intensity*(.5+this.energy)*( .5+random(this.seed,this.block,2)*.5),0,1);
    const p=Object.freeze({token:++this.serial,frame:this.next,bar,block:this.block,backend:b.id,
      kind:b.kind,seed:this.seed,amount,energy:this.energy,peak:this.maxPeak});
    this.assets+=b.assets; this.pending.set(p.token,p);
    if(b.kind==="neural"&&b.id!==this.lastNeural){this.lastNeural=b.id;this.lastSwitch=bar;}
    this.event("plan",this.lastFrame,{plan:p,assets:this.assets});
    return p;
  }
  // Nur exakt am geplanten Quellframe aufrufen. Verspätete Blöcke nie nachholen.
  advance(frame, prepared=null) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    if(!this.running)return false;
    if(frame<this.lastFrame){this.stop(frame);return false;}
    this.lastFrame=frame;
    if(frame<this.next)return false;
    let applied=false;
    const p=prepared&&this.pending.get(prepared.token);
    if(frame===this.next&&p?.frame===frame&&this.backends.some(b=>b.id===p.backend)&&
       Number.isFinite(prepared.peak)&&prepared.peak>=0&&prepared.peak<=this.maxPeak){
      this.apply(p,prepared);this.event("apply",frame,{plan:p,peak:prepared.peak});applied=true;
    }else this.event("skip",frame,{reason:"Deadline, Freigabe oder Pegel"});
    this.pending.clear();
    // Bei Seek oder Hintergrundtab keine verpassten Aktionen ausführen.
    const bar=this.grid.frameToBar(frame);
    this.block=Math.max(this.block+1,Math.floor((bar-this.anchor)/this.bars)+1);
    this.next=this.grid.barToFrame(this.anchor+this.block*this.bars);
    return applied;
  }
  override(frame,{intensity=this.intensity,energy=this.energy}={}) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    this.intensity=unit(intensity,"Intensität");this.energy=unit(energy,"Energie");
    this.pending.clear();this.event("override",frame,{intensity,energy});
  }
  stop(frame=this.lastFrame) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    this.running=false;this.pending.clear();this.original();
    this.event("original",frame,{assets:this.assets});
  }
  returnToOriginal(frame){this.stop(frame);}
}
