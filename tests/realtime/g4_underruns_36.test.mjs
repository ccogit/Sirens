import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {runInNewContext} from "node:vm";

// Das tatsächliche DevTools-Snippet ausführen; nur Browserimport und Umgebung ersetzen.
const source=readFileSync(new URL("../../benchmarks/g4/soak.js",import.meta.url),"utf8")
  .replace('await import("/js/realtime/audio_core.js")',"({AudioCore:globalThis.AudioCore})");

async function soak(streams){
  let now=0, index=0, blob;
  const rate=48000;
  const status=()=>({cursor:index*600*rate,epoch:index,streams:streams[index]});
  const core={rate, status:status(),clock:{playing:true},context:{state:"running"}};
  await runInNewContext(source,{
    AudioCore:{owner:core},
    performance:{now:()=>now},
    prompt:()=>"1800",
    document:{hidden:false,addEventListener(){},removeEventListener(){},
      createElement:()=>({click(){}})},
    setTimeout(fn,delay){
      if(delay===100){index++;now+=600000;core.status=status();fn();}
    },
    Blob,
    URL:{createObjectURL(value){blob=value;return "blob:test";},revokeObjectURL(){}},
    console:{log(){}},
  });
  return JSON.parse(await blob.text());
}

const modern=(unexpectedUnderruns,expectedUnderruns)=>({
  // Die expliziten Zähler sind maßgeblich, nicht ein möglicher alter Summenzähler.
  unexpectedUnderruns,expectedUnderruns,underruns:unexpectedUnderruns+expectedUnderruns,
  rawUnderruns:999,
});
const legacy=underruns=>({underruns});

test("G4: getrennte Deltas je Spur einschließlich Rücksetzern und Altformat",async()=>{
  const raw=await soak([
    [modern(8,20),legacy(4)],
    [modern(10,24),legacy(6)],
    [modern(1,2),legacy(1)],
    [modern(2,5),legacy(1)],
  ]);
  assert.equal(raw.completed,true);
  assert.equal(raw.unexpected_underruns,7);
  assert.equal(raw.expected_underruns,9);
  assert.equal(raw.underruns,7);
  assert.equal(raw.epoch_changes,3);
  assert.equal(raw.audio_seconds,1800);
});

test("G4: ausschließlich alte Zähler bleiben unerwartete Underruns",async()=>{
  const raw=await soak([[legacy(3)],[legacy(5)],[legacy(0)],[legacy(1)]]);
  assert.equal(raw.completed,true);
  assert.equal(raw.unexpected_underruns,3);
  assert.equal(raw.expected_underruns,0);
  assert.equal(raw.underruns,3);
});

test("G4: ungültiger expliziter Zähler bricht Messung ab",async()=>{
  const raw=await soak([[modern(0,0)],[modern(0,-1)]]);
  assert.equal(raw.completed,false);
  assert.match(raw.error,/Underrun-Zähler/);
});
