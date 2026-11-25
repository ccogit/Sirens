import test from "node:test";
import assert from "node:assert/strict";
import {Transport, frameAtRate, resample} from "../../web/js/realtime/transport.js";
import {pack} from "../../web/js/realtime/pcm.js";
import {decodeDry} from "../../web/js/realtime/shell.js";

test("WP35: 2 Stunden absolute Framegrenzen ohne akkumulierten Rest",()=>{
  const limit=345600000;
  let sum=0,previous=0;
  for(let start=0;start<limit;start+=2048){
    const end=Math.min(limit,start+2048), next=frameAtRate(end,48000,44100);
    const expected=Number((BigInt(end)*147n+80n)/160n);
    assert.equal(next,expected);
    sum+=next-previous;previous=next;
  }
  assert.equal(sum,317520000);
  assert.equal(frameAtRate(sum,44100,48000),limit);
  assert.equal(frameAtRate(limit,48000,48000),limit);
});

test("WP35: Wet-Paketgrenzen am Dry-Quellraster, auch nach Seek",()=>{
  for(const rate of [48000,44100]){
    const sent=[];
    const transport=new Transport({postMessage:m=>sent.push(m)},1,rate);
    transport.setWireRate(48000);
    const origin=12493, source=137, wire=frameAtRate(origin,rate,48000);
    transport.reset(3,origin,source);
    const raw=new Float32Array(8192*2);
    for(let i=0;i<raw.length;i++)raw[i]=Math.sin(i*.04);
    const dry=resample(raw,48000,rate);
    const channels=[new Float32Array(dry.length/2),new Float32Array(dry.length/2)];
    decodeDry({rate,context:{createBuffer:(c,n,r)=>{
      assert.deepEqual([c,n,r],[2,dry.length/2,rate]);
      return {getChannelData:i=>channels[i]};
    }}},raw.buffer,{sample_rate:48000,nframes:8192});
    let cursor=origin;
    for(let offset=0,seq=0;offset<6144;offset+=2048,seq++){
      const bytes=new Uint8Array(raw.buffer,(source+offset)*8,2048*8);
      const block=pack({protocol_version:1,stream_id:1,epoch:3,seq,start_frame:BigInt(wire+offset),
        nframes:2048,channels:2,flags:seq===0?1:0,sample_rate:48000},bytes);
      assert.ok(transport.push(block));
      const m=sent.at(-1);
      assert.equal(m.start,cursor);
      const base=frameAtRate(source+offset,48000,rate);
      // Innere Samples verwenden dasselbe Phasenraster wie Dry.
      for(let i=2;i<m.samples.length/2-2;i+=97){
        assert.ok(Math.abs(m.samples[i*2]-channels[0][base+i])<1e-6);
        assert.ok(Math.abs(m.samples[i*2+1]-channels[1][base+i])<1e-6);
      }
      cursor+=m.samples.length/2;
      transport.advance(3,cursor);
    }
    assert.equal(cursor,origin+frameAtRate(source+6144,48000,rate)-frameAtRate(source,48000,rate));
  }
});
