import {test} from "node:test";
import assert from "node:assert/strict";
import {createBeatGrid} from "../../web/js/realtime/beat_grid.js";

test("konstantes Raster, Samplegenauigkeit und Taktversatz", () => {
  const g = createBeatGrid({bpm:120,beat0:480,bar0:24480,confidence:.9},48000);
  assert.equal(g.frameToBeat(24480),1);
  assert.equal(g.frameToBar(24480),0);
  assert.equal(g.barToFrame(1),120480);
  assert.equal(g.nextBar(24479),24480);
  assert.equal(g.nextBar(24480),120480);
  assert.equal(g.quantize(12500),24480);
  assert.equal(g.quantize(0),480);
  assert.equal(g.beatToFrame(g.frameToBeat(1234567)),1234567);
});
test("stetige Tempo-Karte, auch Wechsel zwischen Schlägen", () => {
  const g = createBeatGrid({bpm:120,beat0:0,bar0:0,confidence:1,
    tempo_map:[{source_frame:30000,bpm:150},{source_frame:82800,bpm:60}]},48000);
  assert.equal(g.frameToBeat(30000),1.25);
  assert.equal(g.beatToFrame(2),44400);
  assert.equal(g.barToFrame(1),82800);
  assert.equal(g.nextBar(82799),82800);
  assert.equal(g.nextBar(82800),274800);
  assert.equal(g.quantize(44401),44400);
  for (const f of [0,29999,30000,30001,82799,82800,82801,999999])
    assert.equal(g.beatToFrame(g.frameToBeat(f)),f);
});
test("unsicheres und ungültiges Raster abweisen", () => {
  const base={bpm:120,beat0:0,bar0:0,confidence:1};
  assert.throws(()=>createBeatGrid({...base,confidence:.49},48000),RangeError);
  assert.throws(()=>createBeatGrid({...base,tempo_map:[{source_frame:10,bpm:90},{source_frame:10,bpm:100}]},48000),RangeError);
  assert.throws(()=>createBeatGrid(base,0),RangeError);
});

test("Raster vor der Quelle und Quellframe-Grenzen", () => {
  const g = createBeatGrid({bpm:120,beat0:18000,bar0:18000,confidence:1},48000);
  assert.equal(g.quantize(0),18000);
  assert.equal(g.nextBar(0),18000);
  assert.throws(()=>g.beatToFrame(-1),RangeError);
  assert.throws(()=>g.beatToFrame(Number.MAX_SAFE_INTEGER),RangeError);
  assert.throws(()=>g.quantize(1,0),RangeError);
  const m = createBeatGrid({bpm:120,beat0:48000,bar0:48000,confidence:1,
    tempo_map:[{source_frame:0,bpm:60},{source_frame:48000,bpm:120}]},48000);
  assert.equal(m.frameToBeat(0),-1);
  assert.equal(m.beatToFrame(-1),0);
  assert.equal(m.beatToFrame(1),72000);
});
