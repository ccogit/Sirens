import test from "node:test";
import assert from "node:assert/strict";
import {FFT} from "../../web/js/realtime/effects/fft.js";
import {SpectralEffect} from "../../web/js/realtime/effects/spectral.js";
test("FFT Rundlauf",()=>{const f=new FFT(16),r=Float64Array.from({length:16},(_,i)=>Math.sin(i)),a=r.slice(),im=new Float64Array(16);f.run(r,im);f.run(r,im,true);for(let i=0;i<16;i++)assert.ok(Math.abs(r[i]-a[i])<1e-12);});
test("STFT Impuls, Stereo und Latenz",()=>{const e=new SpectralEffect("fast"),o=new Float32Array(2);for(let i=0;i<1200;i++){e.process(i===0?0.5:0,i===3?-0.25:0,o);assert.ok(Math.abs(o[0]-(i===512?0.5:0))<1e-6);assert.ok(Math.abs(o[1]-(i===515?-0.25:0))<1e-6);}});
test("Oktave und endliche Energie",()=>{const e=new SpectralEffect("standard"),o=new Float32Array(2);e.setPitch(2);let crossings=0,prev=0,energy=0;for(let i=0;i<24000;i++){e.process(0.1*Math.sin(2*Math.PI*375*i/48000),0,o);assert.ok(Number.isFinite(o[0]));assert.equal(o[1],0);if(i>=8000){if(prev<=0&&o[0]>0)crossings++;energy+=o[0]*o[0];}prev=o[0];}assert.ok(Math.abs(crossings*3-750)<30);assert.ok(energy>1&&energy<1000);});
