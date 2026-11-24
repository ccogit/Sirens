import test from "node:test";
import assert from "node:assert/strict";
import {createBeatGrid} from "../../web/js/realtime/beat_grid.js";
import {createWalk} from "../../workers/rave/beat_walk.mjs";

test("Walk folgt BeatGrid auch bei Tempo-Wechsel, reproduzierbar und nur am Takt",()=>{
  const grid=createBeatGrid({bpm:120,beat0:0,bar0:0,confidence:1,
    tempo_map:[{source_frame:96000,bpm:60}]},48000);
  const preset={seed:42,step:0.25,initial:0};
  const a=createWalk(grid,preset), b=createWalk(grid,preset);
  assert.deepEqual(a.advance(95999),[]);
  assert.equal(a.value,0);
  const first=a.advance(96000);
  assert.equal(first[0].frame,96000);
  assert.deepEqual(a.advance(287999),[]);
  const second=a.advance(288000);
  assert.equal(second[0].frame,288000);
  assert.deepEqual([...first,...second],b.advance(288000));
  assert.throws(()=>a.advance(0),/Seek/);
  assert.notDeepEqual(createWalk(grid,{...preset,seed:43}).advance(288000),[...first,...second]);
});
