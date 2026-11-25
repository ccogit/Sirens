import assert from "node:assert/strict";
import {test} from "node:test";
import {EffectRack} from "../../web/js/realtime/effects/rack.js";
import {ConvolutionEffect} from "../../web/js/realtime/effects/convolution.js";

const rate=48000;
function measure(legacy=false){
    const rack=new EffectRack("fast");
    // Kontrollierte, gültige Impulsantworten: Identität und Stille.
    // Damit ist die Zielwirkung (90 % Pegelreduktion) eindeutig.
    const conv=new ConvolutionEffect("fast",Float32Array.of(1),Float32Array.of(0));
    rack.effects[2]=rack.convolution=conv;
    if(legacy)conv.morph.frames=512;
    rack.setParameter(2,"wet",1);
    const out=new Float32Array(2);
    let impulse=-1;
    for(let i=0;i<4096;i++){
        rack.process(i===0?.25:0,i===0?-.25:0,out);
        if(Math.abs(out[0])>.1&&impulse<0)impulse=i;
    }
    // Nach dem Impuls stationärer Pegel: keine Quellflanke während der Rampe.
    for(let i=0;i<4096;i++)rack.process(.25,-.25,out);
    assert.ok(Math.abs(out[0]-.25)<1e-5);
    rack.setParameter(2,"morph",1);
    let previous=out[0],jump=0,frames=null;
    for(let i=1;i<=2048;i++){
        rack.process(.25,-.25,out);
        jump=Math.max(jump,Math.abs(out[0]-previous));
        previous=out[0];
        if(frames===null&&Math.abs(out[0])<=.0250001)frames=i;
    }
    assert.notEqual(frames,null);
    assert.ok(Math.abs(out[0])<1e-5);
    return {impulse,frames,ms:frames/rate*1000,jump};
}

test("fast: Rack-Impuls, 90 Prozent Zielwirkung und klickarme Rampe",()=>{
    const before=measure(true),after=measure();
    console.log(JSON.stringify({before,after,rate}));
    assert.equal(after.impulse,896);
    assert.equal(before.impulse,after.impulse);
    assert.ok(after.ms<30);
    assert.ok(after.frames<before.frames);
    // 0,01 FS entspricht 4 % des stationären Testpegels je Sample.
    assert.ok(after.jump<.01);
});
