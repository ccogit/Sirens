import {makeTrack,finite,frame,normalize,gridFor,applyRack} from "./drum_architect.js";
export const crossoverDefaults=Object.freeze({gain:.7,maxStretch:.12,quantize:1,rack:"neutral",songs:[]});
export function crossoverPreset(p={}){
  const x={...crossoverDefaults,...p};
  finite(x.gain,0,1,"Gain");finite(x.maxStretch,0,.2,"Stretch-Limit");finite(x.quantize,.25,4,"Raster");
  if(!["neutral","cloud","octave","freeze"].includes(x.rack)||!Array.isArray(x.songs)||x.songs.length>4)throw new RangeError("Crossover-Preset");
  if(x.songs.some(s=>!Number.isInteger(s.transpose??0)))throw new RangeError("Halbtöne");
  return {...x,songs:x.songs.map(s=>({id:String(s.id),gain:finite(s.gain??1,0,1,"Stem-Gain"),start:frame(s.start??0),transpose:finite(s.transpose??0,-3,3,"Halbtöne")}))};
}
const roots=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
function key(k){
  if(typeof k==="object"&&k)k=k.tonic+" "+k.mode;
  const m=typeof k==="string"&&k.match(/^([A-G]#?)\s+(major|minor|Dur|Moll)$/i);
  return m&&{root:roots.indexOf(m[1].toUpperCase()),mode:({dur:"major",moll:"minor"}[m[2].toLowerCase()]??m[2].toLowerCase())};
}
function compatible(a,b,transpose){
  if(!a||!b)return false;
  const root=(b.root+transpose+12)%12;
  return a.mode===b.mode&&a.root===root || a.mode!==b.mode&&((a.root+(a.mode==="major"?9:3))%12===root);
}
function sample(track,f){
  if(f<0||f>=track.length)return 0;
  const i=Math.floor(f),frac=f-i;return track[i]*(1-frac)+(track[i+1]??0)*frac;
}
// Absolute BeatGrid-Abbildung; überlappende Hann-Grains erhalten die lokale Tonhöhe.
export function stemCrossover({rate,length,grid,targetKey,songs=[],preset={}}){
  const p=crossoverPreset(preset),out=makeTrack(length,rate),warnings=[],events=[];
  if(!Array.isArray(songs)||songs.length>4)throw new RangeError("Maximal vier Songs");
  const target=gridFor(grid,rate,warnings);
  if(!target)return {track:out,warnings,events};
  const hop=Math.max(1,Math.round(rate*.02));
  for(const song of songs){
    const cfg=p.songs.find(s=>s.id===String(song.id))??{gain:1,start:0,transpose:0};
    const source=gridFor(song.grid,rate,warnings);
    if(!source)continue;
    if(!(song.track instanceof Float32Array))throw new RangeError("Stem-PCM");
    if(!compatible(key(targetKey),key(song.key),cfg.transpose))warnings.push("Tonartkonflikt oder unbekannte Tonart: "+song.id);
    const start=target.quantize(cfg.start,p.quantize),beat=target.frameToBeat(start);
    if(start>=length){warnings.push("Start außerhalb des Renderbereichs: "+song.id);continue;}
    const origin=source.frameToBeat(frame(song.sourceFrame??song.grid.beat0));
    const pitch=2**(cfg.transpose/12), map=f=>source.beatToFrame(origin+target.frameToBeat(f)-beat);
    let peak=0;for(const v of song.track){if(!Number.isFinite(v))throw new RangeError("PCM");peak=Math.max(peak,Math.abs(v));}
    // Prüfung über den ganzen Bereich, nicht nur das Anfangstempo.
    let allowed=true,previous=map(start);
    for(let f=start;f<length;){
      const step=Math.min(hop,length-f),next=map(f+step),ratio=(next-previous)/step;previous=next;f+=step;
      if(Math.abs(ratio-1)>p.maxStretch+1/step){allowed=false;break;}
    }
    if(!allowed){warnings.push("Stretch-Limit überschritten: "+song.id);continue;}
    events.push({id:song.id,frame:start,sourceFrame:map(start)});
    const gain=peak?cfg.gain*p.gain/Math.max(1,songs.length)/peak:0;
    for(let f=start;f<length;f+=hop){
      const center=map(f);
      for(let j=-hop;j<hop;j++){
        const i=f+j;if(i<start||i>=length)continue;
        const weight=.5+.5*Math.cos(Math.PI*j/hop);
        out[i]+=sample(song.track,center+j*pitch)*weight*gain;
      }
    }
  }
  return {track:applyRack(normalize(out),p.rack),warnings,events};
}
