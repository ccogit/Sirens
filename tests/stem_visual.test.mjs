// Reine STEM- und Warp-Stage-Logik, ohne Browser/WebGL-GPU für CI testbar.
import assert from "node:assert/strict";
import { test } from "node:test";
import { renderProfil, RENDER_PROFILE, frequenzBaender } from "../web/js/stem_visual.js";
import { STEM_VERTEX, STEM_FRAGMENT } from "../web/js/stem_visual_shader.js";
import { noteGueltig, SYNTH_KLAENGE } from "../web/js/stem_synth.js";

test("RTX Ultra bietet mehr Pixel und Raymarch-Schritte als der Live-Modus",()=>{
  assert.ok(RENDER_PROFILE.ultra.steps > RENDER_PROFILE.live.steps);
  assert.ok(RENDER_PROFILE.ultra.maxWidth >= 3840);
  assert.ok(RENDER_PROFILE.ultra.maxHeight >= 2160);
  assert.equal(renderProfil("ultra",false).steps,160);
});

test("Während Claude läuft oder reduzierter Bewegung wird unabhängig vom Schalter Eco erzwungen",()=>{
  assert.deepEqual(renderProfil("ultra",true),RENDER_PROFILE.eco);
  assert.deepEqual(renderProfil("ultra",false,true),RENDER_PROFILE.eco);
  assert.deepEqual(renderProfil("unbekannt",false),RENDER_PROFILE.live);
});

test("FFT-Bänder reagieren getrennt auf Bass, Mitten und Höhen",()=>{
  const f=new Uint8Array(1024);
  for(let i=2;i<8;i++)f[i]=255; // ca. 43–172 Hz
  const bass=frequenzBaender(f,44100,2048);
  assert.ok(bass[0]>.5);
  assert.ok(bass[1]<.03);
  assert.equal(bass[2],0);
  f.fill(0);
  for(let i=350;i<400;i++)f[i]=200;
  const high=frequenzBaender(f,44100,2048);
  assert.ok(high[2]>.05);
  assert.equal(high[0],0);
});

test("Instrumenten-Noten bekommen eindeutige Grenzen",()=>{
  assert.deepEqual(Object.keys(SYNTH_KLAENGE),["synth","bell","keys","strings","bass"]);
  assert.equal(noteGueltig([0,1,60,.8]),true);
  assert.equal(noteGueltig([1,.5,60,.8]),false);
  assert.equal(noteGueltig([0,1,-1,.8]),false);
  assert.equal(noteGueltig([0,1,60,Number.POSITIVE_INFINITY]),false);
  assert.equal(noteGueltig(["0",1,60,.5]),false);
});

test("Warp Stage hat drei Shader-Welten, Sound-Uniforms und GPU-Schrittlimit",()=>{
  assert.match(STEM_VERTEX,/#version 300 es/);
  assert.match(STEM_FRAGMENT,/uniform vec3 u_audio/);
  assert.match(STEM_FRAGMENT,/uniform int u_steps/);
  assert.match(STEM_FRAGMENT,/u_scene==1/);
  assert.match(STEM_FRAGMENT,/u_scene==2/);
});
