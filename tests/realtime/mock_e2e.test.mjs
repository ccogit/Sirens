import test from "node:test";
import assert from "node:assert/strict";
import {decodeDry} from "../../web/js/realtime/shell.js";
import {createRtApi} from "../../web/js/realtime/api.js";

test("Dry-Referenz bleibt stereo und samplegenau",()=>{
  const channels=[new Float32Array(2),new Float32Array(2)];
  const core={rate:48000,context:{createBuffer:(n,count,rate)=>{
    assert.deepEqual([n,count,rate],[2,2,48000]);
    return {getChannelData:c=>channels[c]};
  }}};
  const raw=new ArrayBuffer(16),v=new DataView(raw);
  [0.25,-0.125,0.5,-0.5].forEach((x,i)=>v.setFloat32(i*4,x,true));
  decodeDry(core,raw,{sample_rate:48000,nframes:2});
  assert.deepEqual([...channels[0]],[.25,.5]);
  assert.deepEqual([...channels[1]],[-.125,-.5]);
  assert.throws(()=>decodeDry(core,raw,{sample_rate:44100,nframes:2}));
});

test("Transportantwort ist kein Sitzungs-Schema; Render sendet nur Frame-Koordinaten",async()=>{
  const calls=[];
  const api=createRtApi({fetcher:async(path,options)=>{
    calls.push([path,options.method,JSON.parse(options.body)]);
    return {status:200,json:async()=>path.endsWith("/transport")?{port:12345,token:"test"}:{accepted:true}};
  }});
  const session={id:"a".repeat(32)};
  assert.equal((await api.transport(session)).port,12345);
  const request={epoch:0,audio_epoch:1,seq:0,start_frame:1234,source_frame:0,nframes:256};
  assert.equal((await api.render(session,request)).accepted,true);
  assert.deepEqual(calls[1][2],request);
});
