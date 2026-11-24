import test from "node:test";
import assert from "node:assert/strict";
import {SpectralEffect} from "../../web/js/realtime/effects/spectral.js";
import {GranularEffect,stretchStereo} from "../../web/js/realtime/effects/granular.js";
import {ConvolutionEffect} from "../../web/js/realtime/effects/convolution.js";
import {EffectRack,RackPath} from "../../web/js/realtime/effects/rack.js";
import {Smooth} from "../../web/js/realtime/effects/effect.js";
for(const Type of [SpectralEffect,GranularEffect,ConvolutionEffect]){
    for(const bypass of [true,false])test(Type.name+" Bitgleich "+(bypass?"Bypass":"Wet=0"),()=>{
        const e=new Type("fast"),o=new Float32Array(2),n=e.latencyFrames;
        if(bypass)e.setBypass(true);else e.setWet(0);
        const a=Float32Array.from({length:4096},(_,i)=>0.1*Math.sin(i));
        for(let i=0;i<256+n;i++)e.process(0,0,o);
        for(let i=0;i<2048+n;i++){
            e.process(a[2*i]||0,a[2*i+1]||0,o);
            assert.equal(o[0],a[2*(i-n)]||0);assert.equal(o[1],a[2*(i-n)+1]||0);
        }
        assert.throws(()=>e.setWet(NaN));assert.throws(()=>e.setBypass(1));
    });
}
test("Glättung, Grenzen und Rack-Ausrichtung",()=>{
    const s=new Smooth(0,0,1,256);s.set(10);let last=0;for(let i=0;i<256;i++){const v=s.tick();assert.ok(v-last<=1/256+1e-12);last=v;}assert.equal(last,1);
    const a=new RackPath("fast",4000),b=new RackPath("standard",4000),x=new Float32Array(2),y=new Float32Array(2);
    for(let i=0;i<256;i++){a.sample(0,0,x);b.sample(0,0,y);}
    for(let i=0;i<4100;i++){a.sample(i===0?0.25:0,0,x);b.sample(i===0?0.25:0,0,y);assert.equal(x[0],i===4000?0.25:0);assert.equal(x[0],y[0]);}
    const rack=new EffectRack();assert.throws(()=>rack.applyPreset("unknown"));assert.throws(()=>rack.setParameter(0,"pitch",Infinity));assert.throws(()=>rack.setParameter(2,"foo",0));
    assert.throws(()=>stretchStereo(new Float32Array(3),2));
});
test("Morph und Maskierung: Sinus, Stereo, begrenzte Ausgabe",()=>{
    const e=new ConvolutionEffect("fast",Float32Array.of(1),Float32Array.of(-1)),o=new Float32Array(2);
    for(let i=0;i<200;i++)e.process(.2,-.1,o);
    e.setMorph(1);let prev=o[0];for(let i=0;i<600;i++){e.process(.2,-.1,o);assert.ok(Math.abs(o[0]-prev)<.001);prev=o[0];assert.ok(Math.abs(o[1]+o[0]/2)<1e-6);}assert.ok(Math.abs(o[0]+.2)<1e-6);
    const s=new SpectralEffect("fast");s.setMask(.2);for(let i=0;i<5000;i++){if(i===2000)s.setFreeze(true);s.process(.1*Math.sin(i*.1),.1*Math.cos(i*.1),o);assert.ok(o.every(v=>Number.isFinite(v)&&Math.abs(v)<=4));}
});

test("Bypass blendet ohne Sprung und erreicht bitgleichen Dry-Pfad",()=>{
    const e=new ConvolutionEffect("fast",Float32Array.of(-1),Float32Array.of(-1)),o=new Float32Array(2);
    for(let i=0;i<300;i++)e.process(.25,-.125,o);
    e.setBypass(true);let prev=o[0];for(let i=0;i<256;i++){e.process(.25,-.125,o);assert.ok(Math.abs(o[0]-prev)<=.002);prev=o[0];}assert.equal(o[0],.25);assert.equal(o[1],-.125);
});
