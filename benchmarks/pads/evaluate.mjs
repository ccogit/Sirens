import {PadScheduler} from "../../web/js/realtime/pad_scheduler.js";
let raw="";
for await (const chunk of process.stdin) raw+=chunk;
const {rows,p95_ms}=JSON.parse(raw);
const rate=44100;
const scheduler=new PadScheduler({grid:{bpm:120,beat0:0,bar0:0,confidence:1},
  sampleRate:rate,p95Ms:p95_ms});
let timely=0,shifted=0,dry=0;
for (const row of rows){
  scheduler.reset();
  const j=scheduler.request({type:row.type,bars:row.bars,seed:row.seed,prompt:"Benchmark",strength:0.7},0);
  const now=Math.ceil(row.elapsed_ms*rate/1000);
  const ready=scheduler.ready(j.id,{frames:row.frames,sampleRate:rate},now);
  if(ready.status!=="ready"){dry++;continue;}
  const plan=scheduler.take(j.id,now);
  if(plan.status!=="scheduled")dry++;
  else if(plan.startFrame===j.startFrame)timely++;
  else shifted++;
}
console.log(JSON.stringify({jobs:rows.length,timely,shifted,dry,ratio:timely/rows.length}));
