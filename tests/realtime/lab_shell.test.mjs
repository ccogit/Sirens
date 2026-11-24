import test from "node:test";
import assert from "node:assert/strict";
import { deriveState } from "../../web/js/realtime/capabilities.js";
import { capability } from "../../web/js/realtime/mock_api.js";

test("Status und Bedienbarkeit", () => {
  const caps = { protocol_version: 1, capabilities: [capability] };
  for (const [input, expected, enabled] of [
    [{ error: {status: 503}, capabilities: null }, "Schalter aus", false],
    [{ capabilities: {protocol_version:1, capabilities:[]}, gpu: {available:false} }, "Kein Modell installiert", false],
    [{ capabilities: caps, gpu: {available:false}, mock: true, songs: 1 }, "Testmodus", true],
    [{ capabilities: caps, gpu: {available:false}, mock: false }, "Keine GPU", false],
    [{ error: {status: 502} }, "API-Fehler", false],
    [{ capabilities: caps, mock:true, songs:0 }, "Leere Bibliothek", false],
    [{ capabilities: caps, mock:true, songs:1, error:{error:"busy_gpu"} }, "GPU beschäftigt", false],
  ]) {
    const state = deriveState(input);
    assert.match(state.text, new RegExp(expected));
    assert.equal(state.enabled, enabled);
  }
});

import { createRtApi, MOCK_ASSET } from "../../web/js/realtime/api.js";
import { createResources, keyAction, readPresets, savePreset, MIDI_BINDINGS } from "../../web/js/realtime/controls.js";
import { createLabShell, createSessionController, catalogEntries } from "../../web/js/realtime/shell.js";
import { gpuText, latencyText } from "../../web/js/realtime/gpu_panel.js";

test("API: 503, kaputtes JSON, falsche Struktur, busy_gpu", async () => {
  for (const [status, body, expected] of [
    [503, {error:"unavailable"}, 503],
    [200, null, 502],
    [200, {}, 502],
    [409, {error:"busy_gpu"}, 409],
  ]) {
    const api = createRtApi({fetcher:async()=>({status,json:async()=>{
      if(body===null)throw new SyntaxError("JSON");
      return body;
    }})});
    await assert.rejects(api.capabilities(),e=>e.status===expected && (status!==409 || e.error==="busy_gpu"));
  }
});
test("Mock: Play, Pause, Seek mit neuer Epoch, Close", async () => {
  const api = createRtApi({mock:true});
  const caps = await api.capabilities();
  assert.equal(caps.capabilities[0].mock,true);
  assert.equal((await api.gpu()).available,false);
  let s=await api.create("mock");
  s=await api.command(s,"load",{asset_id:MOCK_ASSET});
  s=await api.command(s,"play");
  assert.equal(s.state,"playing");
  s=await api.command(s,"pause");
  assert.equal(s.state,"paused");
  s=await api.command(s,"seek",{source_frame:20});
  assert.equal(s.epoch,1);assert.equal(s.seq,null);
  s=await api.command(s,"bypass",{enabled:true});
  assert.equal(s.seq,0);
  assert.equal((await api.close(s)).state,"closed");
});
test("Controller schließt auch bei ausstehendem Start und nach Panic", async () => {
  const real = createRtApi({mock:true});
  let closeCount=0, createCount=0;
  const api={...real,create:(...a)=>{createCount++;return real.create(...a);},
    close:s=>{closeCount++;return real.close(s);}};
  const c=createSessionController(api);
  await c.run(cmd=>cmd("play"));
  assert.equal(c.state,"playing");
  await c.reset();assert.equal(c.state,"created");
  const pending=c.run(cmd=>cmd("play"));
  const done=c.destroy();
  await Promise.all([pending,done]);
  assert.equal(closeCount,1);assert.equal(createCount,1);
  await c.run(()=>assert.fail("Nach destroy kein Befehl"));
});
test("Presets lokal, fehlerhafte Daten, Tastatur und MIDI", () => {
  let data;
  const storage={getItem:()=>data,setItem:(k,v)=>{data=v;}};
  assert.deepEqual(readPresets(storage),{});
  assert.equal(savePreset(storage,"A",{wet:101,bypass:true,gain:0.25}),true);
  assert.deepEqual(readPresets(storage).A,{wet:100,bypass:true,gain:0.25});
  assert.equal(savePreset(storage,"X",{}),false);
  data="kaputt";assert.deepEqual(readPresets(storage),{});
  assert.equal(keyAction({key:" "}),"transport");
  assert.equal(keyAction({key:"Escape"}),"panic");
  assert.equal(keyAction({key:"b",target:{tagName:"INPUT"}}),null);
  assert.equal(keyAction({key:"a",ctrlKey:true}),null);
  assert.equal(keyAction({key:"a",repeat:true}),null);
  assert.equal(MIDI_BINDINGS.wet.cc,1);
});
test("GPU null-Werte und deklarierte Mock-Latenz",()=>{
  assert.match(gpuText({available:false,queue_depth:0}),/VRAM: unbekannt · Warteschlange: 0/);
  assert.match(gpuText({available:true,vram_used_bytes:null,vram_total_bytes:1048576}),/unbekannt \/ 1 MiB/);
  assert.match(latencyText(capability),/nicht gemessen/);
  assert.deepEqual(catalogEntries({artists:[]}),[]);
});

// Minimales DOM für Lifecycle-Abnahme; keine Browser-/Audio-Emulation.
test("mount, pause, destroy: Listener, Timer, keine AudioContexts, keine späten Updates", async () => {
  let listeners=0, timers=0, contexts=0, resolveCaps;
  class Element {
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.value="";this.textContent="";}
    setAttribute(k,v){this[k]=v;}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=[];this.append(...nodes);}
    addEventListener(){listeners++;}
    removeEventListener(){listeners--;}
    get options(){return this.children;}
  }
  const previous={document:globalThis.document,Node:globalThis.Node,AudioContext:globalThis.AudioContext};
  globalThis.Node=Element;
  globalThis.document={createElement:tag=>new Element(tag),createTextNode:text=>Object.assign(new Element("#text"),{textContent:text})};
  globalThis.AudioContext=class{constructor(){contexts++;}};
  try{
    const keyboard=new Element("window"),root=new Element("div");
    const timerHost={setInterval:()=>++timers,clearInterval:()=>{timers--;}};
    const remote={capabilities:()=>new Promise(r=>{resolveCaps=r;}),gpu:async()=>({available:false})};
    const shell=createLabShell({remote,catalog:{katalog:async()=>({artists:[]})},timerHost,keyboard});
    shell.mount(root);assert.equal(timers,1);assert.ok(listeners>0);
    shell.mount(root);assert.equal(timers,1);
    await shell.pause();assert.equal(timers,0);assert.equal(listeners,0);assert.equal(root.children.length,0);
    resolveCaps({protocol_version:1,capabilities:[capability]});
    await Promise.resolve();await Promise.resolve();
    assert.equal(root.children.length,0);
    shell.mount(root);assert.equal(timers,1);
    await shell.destroy();await shell.destroy();
    assert.equal(timers,0);assert.equal(listeners,0);assert.equal(contexts,0);
    resolveCaps({protocol_version:1,capabilities:[]});
    await Promise.resolve();
  }finally{Object.assign(globalThis,previous);}
});

test("Fehlendes Modell bleibt bei GPU-503 sichtbar",()=>{
  const state=deriveState({capabilities:{protocol_version:1,capabilities:[]},error:{status:503}});
  assert.match(state.text,/API-Fehler/);
  assert.match(state.text,/Kein Modell installiert/);
  assert.equal(state.enabled,false);
});
test("Destroy während Session-Erzeugung verhindert Load und schließt die Session",async()=>{
  const real=createRtApi({mock:true});
  let resolveCreate, commands=0, closed=0;
  const api={...real,create:()=>new Promise(r=>{resolveCreate=r;}),
    command:(...a)=>{commands++;return real.command(...a);},
    close:s=>{closed++;return real.close(s);}};
  const controller=createSessionController(api);
  const pending=controller.run(()=>assert.fail("Play nach destroy"));
  await Promise.resolve();
  const done=controller.destroy();
  resolveCreate(await real.create("mock"));
  await Promise.all([pending,done]);
  assert.equal(commands,0);
  assert.equal(closed,1);
});
