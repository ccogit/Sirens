import {applyRack, drumArchitect} from "./drum_architect.js";
import {stemCrossover} from "./stem_crossover.js";
import {acidTransformer} from "./acid_transformer.js";

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
  const list=DSP.filter(b=>typeof adapters.get(b.id)==="function");
  for(const c of capabilities?.capabilities??[]) {
    if(neural.has(c.id)&&c.available===true&&c.mock===false&&
       ["streaming","lookahead"].includes(c.mode)&&typeof adapters.get(c.id)==="function"&&
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
    this.maxPeak=Math.min(.8,unit(maxPeak,"Pegelgrenze")); this.maxAssets=integer(maxAssets,0,1000,"Asset-Quota");
    this.maxPending=integer(maxPending,1,8,"Warteschlange"); this.switchBars=integer(switchBars,4,64,"Modellwechsel");
    this.pending=new Map(); this.jobs=new Map(); this.prepared=new Map(); this.assets=0; this.serial=0; this.running=false;
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
    if(!this.running||this.jobs.size>=this.maxPending||this.pending.size>=this.maxPending||
       [...this.pending.values()].some(p=>p.frame===this.next)) return null;
    const bar=this.anchor+this.block*this.bars;
    const available=this.backends.filter(b=>b.kind==="dsp"||
      (this.assets+b.assets<=this.maxAssets&&
       (!this.lastNeural||b.id===this.lastNeural||bar-this.lastSwitch>=this.switchBars)));
    if(!available.length) return null;
    const b=available[Math.floor(random(this.seed,this.block,1)*available.length)];
    const amount=clamp(this.intensity*(.5+this.energy)*( .5+random(this.seed,this.block,2)*.5),0,1);
    const p=Object.freeze({token:++this.serial,frame:this.next,endFrame:this.grid.barToFrame(bar+this.bars),bar,block:this.block,backend:b.id,
      kind:b.kind,seed:this.seed,amount,energy:this.energy,peak:this.maxPeak});
    if(p.endFrame-p.frame>11520000)throw new RangeError("Taktblock zu lang");
    this.assets+=b.assets; this.pending.set(p.token,p);
    if(b.kind==="neural"&&b.id!==this.lastNeural){this.lastNeural=b.id;this.lastSwitch=bar;}
    this.event("plan",this.lastFrame,{plan:p,assets:this.assets});
    return p;
  }
  // Ein vorbereiteter Block enthält ausschließlich begrenztes PCM. Abbruch zählt
  // weiterhin gegen die Queue, bis der Adapter tatsächlich beendet ist.
  async prepare(plan, input) {
    if(this.pending.get(plan?.token)!==plan||this.jobs.has(plan.token)||this.prepared.has(plan.token)||
       this.jobs.size>=this.maxPending) return null;
    const controller=new AbortController();
    this.jobs.set(plan.token,controller);
    try {
      const result=await this.adapters.get(plan.backend)(plan,input,controller.signal);
      if(controller.signal.aborted||this.pending.get(plan.token)!==plan) return null;
      const track=result?.track;
      if(!(track instanceof Float32Array)||track.length!==plan.endFrame-plan.frame) return null;
      const peak=pcmPeak(track);
      if(peak>this.maxPeak) return null;
      const prepared={token:plan.token,track,peak,warnings:result.warnings??[]};
      this.prepared.set(plan.token,prepared);return prepared;
    } catch {
      this.event("error",this.lastFrame,{backend:plan.backend});return null;
    } finally {this.jobs.delete(plan.token);}
  }
  cancelPending(){
    for(const token of this.pending.keys())this.jobs.get(token)?.abort();
    this.pending.clear();this.prepared.clear();
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
    if(frame===this.next&&p?.frame===frame&&this.prepared.get(p.token)===prepared&&this.backends.some(b=>b.id===p.backend)&&
       prepared.track instanceof Float32Array&&prepared.track.length===p.endFrame-p.frame&&
       pcmPeak(prepared.track)<=this.maxPeak){
      try {this.apply(p,prepared);this.event("apply",frame,{plan:p,peak:pcmPeak(prepared.track)});applied=true;}
      catch {this.stop(frame);return false;}
    }else this.event("skip",frame,{reason:"Deadline, Freigabe oder Pegel"});
    this.cancelPending();
    // Bei Seek oder Hintergrundtab keine verpassten Aktionen ausführen.
    const bar=this.grid.frameToBar(frame);
    this.block=Math.max(this.block+1,Math.floor((bar-this.anchor)/this.bars)+1);
    this.next=this.grid.barToFrame(this.anchor+this.block*this.bars);
    while(this.next<=frame)this.next=this.grid.barToFrame(this.anchor+(++this.block)*this.bars);
    return applied;
  }
  override(frame,{intensity=this.intensity,energy=this.energy}={}) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    this.intensity=unit(intensity,"Intensität");this.energy=unit(energy,"Energie");
    this.cancelPending();this.event("override",frame,{intensity,energy});
  }
  stop(frame=this.lastFrame) {
    integer(frame,0,Number.MAX_SAFE_INTEGER,"Quellframe");
    this.running=false;this.cancelPending();this.original();
    this.event("original",frame,{assets:this.assets});
  }
  returnToOriginal(frame){this.stop(frame);}
}

function pcmPeak(track){
  let peak=0;
  for(const v of track){if(!Number.isFinite(v))return Infinity;peak=Math.max(peak,Math.abs(v));}
  return peak;
}
// Blocklokale, bereits dekodierte Mono-Quellen. Nur vorhandene Tools anbieten.
// Der Controller muss außerhalb des Audiopfads vorbereiten und Warnungen anzeigen.
export function dspMutationAdapters({drum=false,crossover=false,acid=false}={}){
  const mix=(plan,input,wet,warnings=[])=>{
    if(!(input.dry instanceof Float32Array)||input.dry.length!==wet.length)throw new RangeError("Dry-PCM");
    const track=new Float32Array(wet.length);
    for(let i=0;i<track.length;i++)track[i]=input.dry[i]*(1-plan.amount)+wet[i]*plan.amount;
    const peak=pcmPeak(track);
    if(!Number.isFinite(peak))throw new RangeError("PCM");
    if(peak>plan.peak)for(let i=0;i<track.length;i++)track[i]*=plan.peak*.999/peak;
    return {track,warnings};
  };
  const adapters=new Map([["dsp-rack",(p,x)=>mix(p,x,applyRack(x.dry,["cloud","octave","freeze"][Math.floor(random(p.seed,p.block,3)*3)]))]]);
  if(drum)adapters.set("drum",(p,x)=>{const r=drumArchitect({...x.drum,rate:x.rate,length:x.dry.length,preset:{mode:"double",gain:p.amount}});return mix(p,x,r.track,r.warnings);});
  if(crossover)adapters.set("crossover",(p,x)=>{const r=stemCrossover({...x.crossover,rate:x.rate,length:x.dry.length,preset:{gain:p.amount}});return mix(p,x,r.track,r.warnings);});
  if(acid)adapters.set("acid",(p,x)=>{const r=acidTransformer({...x.acid,rate:x.rate,length:x.dry.length,preset:{gain:p.amount,cutoff:200+1800*p.energy}});return mix(p,x,r.track,r.warnings);});
  return adapters;
}
const backends=["dsp-rack","drum","crossover","acid","demon","rave","after"];
// Exportprojektion auf eingefrorene WP16-set_param-Kommandos, nicht an
// Worker senden. Master-Frame und Sequenz stammen vom Session-Eigentümer.
export function mutationSessionParameters(event){
  const p=event.plan;
  const codes={start:1,plan:2,apply:3,skip:4,override:5,original:6,error:7};
  const values={mutation_event:codes[event.type],mutation_seed:event.seed,mutation_bars:event.bars,
    mutation_source:event.frame,mutation_backend:p?backends.indexOf(p.backend)+1:undefined,
    mutation_block:p?.block,mutation_amount:p?.amount,mutation_energy:p?.energy??event.energy,
    mutation_intensity:event.intensity,mutation_assets:event.assets,mutation_peak:event.peak};
  return Object.entries(values).filter(([,value])=>Number.isFinite(value)).map(([name,value])=>({name,value}));
}
