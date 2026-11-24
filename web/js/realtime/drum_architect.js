import {createBeatGrid} from "./beat_grid.js";
import {EffectRack} from "./effects/rack.js";

// Gemeinsame Offline-Render- und Preset-Schnittstelle. Frames sind Quellframes.
export const clamp = (x, min=-1, max=1) => Math.min(max, Math.max(min,x));
export function finite(x,min,max,name) {
  if(typeof x!=="number" || !Number.isFinite(x) || x<min || x>max) throw new RangeError(name);
  return x;
}
export function frame(x) {
  if(!Number.isSafeInteger(x)||x<0) throw new RangeError("Frame");
  return x;
}
export function rateCheck(rate) { if(!Number.isSafeInteger(rate))throw new RangeError("Samplerate");return finite(rate,8000,192000,"Samplerate"); }
export function makeTrack(length,rate) {
  frame(length); rateCheck(rate);
  if(length>rate*600) throw new RangeError("Maximal 10 Minuten je Render");
  return new Float32Array(length);
}
export function normalize(track,peak=.8) {
  let max=0;
  for(const v of track) {if(!Number.isFinite(v)) throw new RangeError("PCM"); max=Math.max(max,Math.abs(v));}
  if(max>peak) for(let i=0;i<track.length;i++) track[i]*=peak/max;
  return track;
}
export function gridFor(grid,rate,warnings) {
  try {return createBeatGrid(grid,rate);} catch {warnings.push("BeatGrid unsicher – keine automatische Quantisierung");return null;}
}
export function savePreset(tool,parameters) {return JSON.stringify({version:1,tool,parameters});}
export function loadPreset(tool,json,validate) {
  const p=JSON.parse(json);
  if(p?.version!==1||p.tool!==tool) throw new RangeError("Preset-Version oder Werkzeug");
  return validate(p.parameters);
}
export function applyRack(track,preset="neutral") {
  if(preset==="neutral") return track;
  const rack=new EffectRack(); rack.applyPreset(preset);
  const out=new Float32Array(2), result=new Float32Array(track.length);
  // Offline-Latenz kompensieren, am Ende mit Null auffüllen.
  for(let i=0;i<track.length+rack.latencyFrames;i++){
    const v=track[i]??0; rack.process(v,v,out);
    if(i>=rack.latencyFrames) result[i-rack.latencyFrames]=(out[0]+out[1])*.5;
  }
  return normalize(result);
}
// Kein eigener AudioContext; Übergabe an den einzigen AudioCore.
export class PerformanceScheduler {
  constructor(core){this.core=core;this.buffers=[];this.playing=false;this.source=0;}
  setTrack(track){
    this.stop();
    const b=this.core.context.createBuffer(1,track.length,this.core.rate);
    b.copyToChannel(track,0);this.buffers=[b];
  }
  play(source=this.source,options={}) {
    frame(source);if(!this.buffers.length||source>=this.buffers[0].length) throw new RangeError("Quellframe");
    const result=this.core.play(this.buffers,{...options,source});this.source=source;this.playing=true;return result;
  }
  stop(){if(this.playing)this.core.stop();this.playing=false;this.source=0;}
  seek(source,options={}){frame(source);if(!this.buffers.length||source>=this.buffers[0].length)throw new RangeError("Quellframe");if(this.playing)return this.play(source,options);this.source=source;}
}
const kinds=["kick","snare","cymbal"];
export const drumDefaults=Object.freeze({mode:"double",gain:.5,quantize:0,rack:"neutral",corrections:[]});
export function drumPreset(p={}) {
  const x={...drumDefaults,...p};
  if(!["double","replace"].includes(x.mode)||!["neutral","cloud","octave","freeze"].includes(x.rack))throw new RangeError("Drum-Preset");
  finite(x.gain,0,1,"Gain");finite(x.quantize,0,1,"Quantisierung");
  if(!Array.isArray(x.corrections))throw new RangeError("Korrekturen");
  return {...x,corrections:x.corrections.map(c=>({index:frame(c.index),frame:frame(c.frame),velocity:finite(c.velocity,0,1,"Velocity")}))};
}
export function drumArchitect({rate,length,stems={},onsets=[],grid,preset={}}){
  const p=drumPreset(preset),warnings=[],out=makeTrack(length,rate),g=p.quantize?gridFor(grid,rate,warnings):null;
  const available=kinds.filter(k=>stems[k] instanceof Float32Array);
  if(available.length!==3)warnings.push("Einzelschlagzeugspuren fehlen – nur vorhandene Spuren; Demucs drums wird nicht ersetzt");
  for(const [kind,track] of Object.entries(stems)){
    if(!(track instanceof Float32Array)||track.length!==length)throw new RangeError("Stem-Länge");
    if(p.mode==="replace"&&available.includes(kind)&&onsets.some(e=>e.kind===kind&&e.frame<length))continue;
    for(let i=0;i<length;i++)out[i]+=track[i];
  }
  const events=[];
  for(const [index,e] of onsets.entries()){
    if(!available.includes(e.kind)&&!(stems.drums instanceof Float32Array&&p.mode==="double"&&kinds.includes(e.kind)))continue;
    const c=p.corrections.find(c=>c.index===index);
    const original=frame(c?.frame??e.frame),velocity=finite(c?.velocity??e.velocity,0,1,"Velocity");
    const start=c||!g?original:g.quantize(original,p.quantize);
    if(start>=length)continue;
    const event={kind:e.kind,frame:start,velocity};events.push(event);
    const duration=Math.round(rate*(e.kind==="cymbal"?.12:.09));
    let seed=(start+1)>>>0;
    for(let j=0;j<duration&&start+j<length;j++){
      const t=j/rate;seed=(Math.imul(seed,1664525)+1013904223)>>>0;
      const noise=seed/2147483648-1;
      const signal=e.kind==="kick"?Math.cos(2*Math.PI*(55*t+65*(1-Math.exp(-45*t))/45)):e.kind==="snare"?.7*noise+.3*Math.cos(2*Math.PI*170*t):noise*Math.cos(2*Math.PI*3500*t);
      out[start+j]+=signal*Math.exp(-t*(e.kind==="cymbal"?30:55))*velocity*p.gain;
    }
  }
  return {track:applyRack(normalize(out),p.rack),events,warnings};
}
