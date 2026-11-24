import {makeTrack,finite,frame,normalize,gridFor,applyRack,clamp} from "./drum_architect.js";
export const acidDefaults=Object.freeze({gain:.5,cutoff:900,resonance:3,drive:1,octave:0,accent:.75,slide:.06,hideBass:false,quantize:0,rack:"neutral",onsetMidi:36});
export function acidPreset(p={}){
  const x={...acidDefaults,...p};
  for(const [k,a,b] of [["gain",0,1],["cutoff",80,10000],["resonance",.5,12],["drive",1,8],["octave",-2,2],["accent",0,1],["slide",0,.3],["quantize",0,1],["onsetMidi",0,127]])finite(x[k],a,b,k);
  if(!Number.isInteger(x.octave)||!Number.isInteger(x.onsetMidi)||typeof x.hideBass!=="boolean"||!["neutral","cloud","octave","freeze"].includes(x.rack))throw new RangeError("Acid-Preset");
  return x;
}
export function acidTransformer({rate,length,bass,notes=[],onsets=[],grid,preset={}}){
  const p=acidPreset(preset),out=makeTrack(length,rate),warnings=[],g=p.quantize?gridFor(grid,rate,warnings):null;
  if(bass!==undefined&&(!(bass instanceof Float32Array)||bass.length!==length))throw new RangeError("Bass-PCM");
  if(bass&&!p.hideBass)out.set(bass);
  if(!notes.length&&onsets.length)warnings.push("Nur Onsets – Tonhöhe ist vorgegeben, nicht erkannt");
  // Noten aus Stem Studio: [Startsekunden, Endsekunden, MIDI, Velocity].
  const raw=notes.length?notes.map(n=>({frame:Math.round(n[0]*rate),end:Math.round(n[1]*rate),midi:n[2],velocity:n[3]})):
    onsets.map(n=>({frame:n.frame,end:n.frame+Math.round(rate*.15),midi:n.midi??p.onsetMidi,velocity:n.velocity??.7}));
  const events=raw.map(n=>{
    const f=frame(n.frame),end=frame(n.end);if(end<=f)throw new RangeError("Notenlänge");
    const start=g?g.quantize(f,p.quantize):f;
    return {frame:start,end:start+end-f,midi:finite(n.midi,0,127,"MIDI"),velocity:finite(n.velocity,0,1,"Velocity")};
  }).sort((a,b)=>a.frame-b.frame);
  let phase=0,prevFreq=0,z1=0,z2=0;
  const omega=2*Math.PI*Math.min(p.cutoff,rate*.4)/rate,alpha=Math.sin(omega)/(2*p.resonance),a0=1+alpha;
  const b0=(1-Math.cos(omega))/(2*a0),b1=2*b0,b2=b0,a1=-2*Math.cos(omega)/a0,a2=(1-alpha)/a0;
  for(let k=0;k<events.length;k++){
    const n=events[k],end=Math.min(n.end,events[k+1]?.frame??length,length);
    if(end<=n.frame)continue;
    const freq=Math.min(rate*.4,440*2**((n.midi+12*p.octave-69)/12));
    const linked=k>0&&events[k-1].end>=n.frame;
    if(!linked){phase=0;prevFreq=freq;z1=z2=0;}
    for(let i=n.frame;i<end;i++){
      const t=(i-n.frame)/rate,slide=linked&&p.slide?Math.min(1,t/p.slide):1;
      const hz=prevFreq*(freq/prevFreq)**slide;
      phase=(phase+hz/rate)%1;
      // Bandbegrenzte Sägezahn-Näherung (wenige Harmonische).
      let v=0;for(let h=1;h<=Math.min(12,Math.floor(rate*.45/hz));h++)v+=Math.sin(2*Math.PI*h*phase)/h;
      const filtered=b0*v+z1;z1=b1*v-a1*filtered+z2;z2=b2*v-a2*filtered;
      const env=Math.min(1,t/.003,(end-i)/(rate*.008))*Math.exp(-t*2);
      const accent=n.velocity>=p.accent?1:.65;
      out[i]+=Math.tanh(filtered*p.drive)*env*n.velocity*accent*p.gain;
    }
    prevFreq=freq;
  }
  return {track:applyRack(normalize(out),p.rack),events,warnings};
}
