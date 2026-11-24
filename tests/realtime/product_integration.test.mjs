import test from "node:test";
import assert from "node:assert/strict";
import {filterCatalog,sessionExport,unavailableTools} from "../../web/js/realtime/integration.js";
import {createRtApi} from "../../web/js/realtime/api.js";

test("Katalogsuche ohne Verlust der aktuell gewählten Quelle",()=>{
  const songs=[{path:"a.wav",label:"Künstler · Erste"},{path:"b.wav",label:"Andere · Zweite"}];
  assert.deepEqual(filterCatalog(songs,"KÜNSTLER erste"),[songs[0]]);
  assert.deepEqual(filterCatalog(songs,"zweite","a.wav"),songs);
  assert.deepEqual(filterCatalog(songs,"unbekannt"),[]);
});
test("Export enthält geprüfte Quelle, Asset-IDs und Befehle; kein Modell vorgetäuscht",()=>{
  const source={asset_id:"a".repeat(32),sha256:"b".repeat(64)};
  const assets=["c".repeat(32),"c".repeat(32)], timeline=[{frame:0,command:{command:"play",epoch:0,seq:1,args:{}}}];
  const value=sessionExport(source,48000,{wet:50,bypass:false},assets,timeline);
  assert.deepEqual(value.sources,[source]);assert.deepEqual(value.assets,[assets[0]]);
  assert.deepEqual(value.models,[{name:"mock",version:"mock-v1"}]);
  assert.deepEqual(value.timeline,timeline);assert.throws(()=>sessionExport({},48000,{},[],[]));
  assert.ok(unavailableTools.includes("DrumSep"));
});
test("Export-Quelle wird sitzungsgebunden abgefragt",async()=>{
  const calls=[], source={asset_id:"a".repeat(32),sha256:"b".repeat(64)};
  const api=createRtApi({fetcher:async(p,o)=>{calls.push([p,o.method]);return {status:200,json:async()=>source};}});
  assert.deepEqual(await api.exportSource({id:"c".repeat(32)}),source);
  assert.deepEqual(calls,[[`/api/rt/v1/sessions/${"c".repeat(32)}/export-source`,"GET"]]);
});
