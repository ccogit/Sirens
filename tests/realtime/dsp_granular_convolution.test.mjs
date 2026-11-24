import test from "node:test";
import assert from "node:assert/strict";
import {GranularEffect,stretchStereo} from "../../web/js/realtime/effects/granular.js";
import {ConvolutionEffect,generatedIR} from "../../web/js/realtime/effects/convolution.js";
test("Stretch Faktor 2 mit gleicher Tonhöhe",()=>{
    const a=Float32Array.from({length:16000},(_,i)=>i%2?0:0.2*Math.sin(2*Math.PI*400*Math.floor(i/2)/48000));
    const b=stretchStereo(a,2);assert.equal(b.length,a.length*2);
    let crosses=0;for(let i=2000;i<12000;i++){assert.equal(b[2*i+1],0);assert.ok(Number.isFinite(b[2*i]));if(b[2*i]>0&&b[2*i-2]<=0)crosses++;}
    assert.ok(Math.abs(crosses*4.8-400)<30);
});
test("Granular neutral: Stereo und Latenz",()=>{
    const e=new GranularEffect("fast"),o=new Float32Array(2);
    for(let i=0;i<900;i++){e.process(i===0?0.5:0,i===3?-0.25:0,o);assert.equal(o[0],i===256?0.5:0);assert.equal(o[1],i===259?-0.25:0);}
    e.setCloud(1);for(let i=0;i<4000;i++){e.process(Math.sin(i)*0.2,0,o);assert.ok(Number.isFinite(o[0])&&Math.abs(o[0])<=0.21);assert.equal(o[1],0);}
});
test("Partitionierte Faltung: Impuls ergibt IR, Stereo",()=>{
    const a=generatedIR(512),e=new ConvolutionEffect("fast",a,a),o=new Float32Array(2);
    for(let i=0;i<800;i++){e.process(i===0?1:0,i===7?0.5:0,o);assert.ok(Math.abs(o[0]-(a[i-128]||0))<1e-6);assert.ok(Math.abs(o[1]-0.5*(a[i-135]||0))<1e-6);}
});
