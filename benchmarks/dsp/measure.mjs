import {performance} from "node:perf_hooks";
import {EffectRack} from "../../web/js/realtime/effects/rack.js";
const profile=process.argv[2]??"fast",stems=Number(process.argv[3]??1);
if(![1,2,4,8].includes(stems))throw new RangeError("Spuren: 1, 2, 4, 8");
const rate=48000,frames=128,iterations=1000;
const rack=Array.from({length:stems},()=>new EffectRack(profile)),o=new Float32Array(2);
for(const e of rack)e.applyPreset("cloud");
function run(){
    const ms=[];let t=0,checksum=0;
    for(let q=0;q<iterations;q++){
        const start=performance.now();
        for(let i=0;i<frames;i++){
            const x=.1*Math.sin(2*Math.PI*375*t++/rate);
            for(const e of rack){e.process(x,-x,o);checksum+=o[0];}
        }
        ms.push(performance.now()-start);
    }
    ms.sort((a,b)=>a-b);
    const p=q=>ms[Math.ceil(q*ms.length)-1];
    return {p50_ms:p(.5),p95_ms:p(.95),p99_ms:p(.99),rtf:ms.reduce((a,b)=>a+b,0)/(iterations*frames/rate*1000),checksum};
}
console.log(JSON.stringify({backend:"cpu",profile,stems,rate,frames,latency_frames:rack[0].latencyFrames,kalt:run(),warm:run()}));
