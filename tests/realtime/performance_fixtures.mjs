import {drumArchitect} from "../../web/js/realtime/drum_architect.js";
import {stemCrossover} from "../../web/js/realtime/stem_crossover.js";
import {acidTransformer} from "../../web/js/realtime/acid_transformer.js";
// Ausschließlich synthetische PCM-Fixtures; keine Medien im Repository.
export const rate=48000,length=rate*4;
export const grid={bpm:123,beat0:0,bar0:0,confidence:1,tempo_map:[]};
const sine=(hz,gain=.15)=>Float32Array.from({length},(_,i)=>Math.sin(2*Math.PI*hz*i/rate)*gain);
const drum=new Float32Array(length);
const onsets=Array.from({length:8},(_,i)=>({frame:Math.round(i*rate*60/123),kind:["kick","cymbal","snare","cymbal"][i%4],velocity:i%2?.45:.85}));
const notes=onsets.map((e,i)=>({start_frame:e.frame,end_frame:e.frame+Math.round(rate*.49),pitch:[36,36,39,43][i%4],amplitude:e.velocity}));
const songs=[{id:"a",grid,key:"C Moll",track:sine(130.81)},{id:"b",grid:{...grid,bpm:120},key:"Es Dur",track:sine(155.56)},{id:"c",grid,key:"C Moll",track:sine(196)},{id:"d",grid,key:"C Moll",track:sine(261.63)}];
export const demos={
 "drum-double":()=>drumArchitect({rate,length,grid,stems:{drums:drum},onsets}),
 "drum-replace-fixture":()=>drumArchitect({rate,length,grid,stems:{kick:sine(55,.03),snare:drum,cymbal:drum},onsets,preset:{mode:"replace"}}),
 "drum-correction":()=>drumArchitect({rate,length,grid,stems:{drums:drum},onsets,preset:{quantize:1,corrections:[{index:1,frame:Math.round(rate*.52),velocity:.95}]}}),
 "crossover-two":()=>stemCrossover({rate,length,grid,targetKey:"C Moll",songs:songs.slice(0,2).map(s=>({...s,key:s.id==="b"?"D# Dur":s.key}))}),
 "crossover-four":()=>stemCrossover({rate,length,grid,targetKey:"C Moll",songs,preset:{songs:[{id:"b",start:Math.round(rate*60/123)}]}}),
 "crossover-conflict":()=>stemCrossover({rate,length,grid,targetKey:"C Moll",songs:[songs[0],{...songs[1],grid:{...grid,bpm:180},key:"F# Dur"}]}),
 "acid-accent":()=>acidTransformer({rate,length,grid,notes,preset:{accent:.6,hideBass:true}}),
 "acid-slide-drive":()=>acidTransformer({rate,length,grid,notes,bass:sine(65.4),preset:{slide:.1,drive:5,octave:1,resonance:6}}),
 "acid-onsets":()=>acidTransformer({rate,length,grid,onsets:onsets.map(e=>e.frame),preset:{onsetMidi:40,cutoff:450}})
};
