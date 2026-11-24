import {Delay,bounded} from "./effect.js";
import {SpectralEffect} from "./spectral.js";
import {GranularEffect} from "./granular.js";
import {ConvolutionEffect} from "./convolution.js";
export const presets=Object.freeze({
    neutral:Object.freeze({pitch:1,mask:1,freeze:false,cloud:0,morph:0,wet:[0,0,0]}),
    cloud:Object.freeze({pitch:1,mask:1,freeze:false,cloud:0.7,morph:0.5,wet:[0,0.8,0.3]}),
    octave:Object.freeze({pitch:2,mask:0.8,freeze:false,cloud:0,morph:0,wet:[1,0,0]}),
    freeze:Object.freeze({pitch:1,mask:0.65,freeze:true,cloud:0,morph:0.2,wet:[1,0,0.3]})
});
// Feste Reihenfolge und deklarierte Summenlatenz, auch bei Wet=0/Bypass.
export class EffectRack {
    constructor(profile="fast"){
        this.spectral=new SpectralEffect(profile);this.granular=new GranularEffect(profile);this.convolution=new ConvolutionEffect(profile);
        this.effects=[this.spectral,this.granular,this.convolution];
        this.latencyFrames=this.effects.reduce((n,e)=>n+e.latencyFrames,0);
        this.a=new Float32Array(2);this.b=new Float32Array(2);
        this.applyPreset("neutral");
    }
    applyPreset(name){
        const p=presets[name];if(!Object.hasOwn(presets,name))throw new RangeError("Preset");
        this.spectral.setPitch(p.pitch);this.spectral.setMask(p.mask);this.spectral.setFreeze(p.freeze);
        this.granular.setCloud(p.cloud);this.convolution.setMorph(p.morph);
        for(let i=0;i<3;i++)this.effects[i].setWet(p.wet[i]);
    }
    setParameter(family,key,value){
        const e=this.effects[family];if(!e)throw new RangeError("Effekt");
        if(key==="wet")e.setWet(value);
        else if(key==="bypass")e.setBypass(value);
        else if(family===0&&key==="pitch")e.setPitch(value);
        else if(family===0&&key==="mask")e.setMask(value);
        else if(family===0&&key==="freeze")e.setFreeze(value);
        else if(family===1&&key==="cloud")e.setCloud(value);
        else if(family===2&&key==="morph")e.setMorph(value);
        else throw new RangeError("Parameter");
    }
    process(l,r,out){
        this.effects[0].process(l,r,this.a);this.effects[1].process(this.a[0],this.a[1],this.b);
        this.effects[2].process(this.b[0],this.b[1],out);
    }
    reset(){for(const e of this.effects)e.reset();}
}
// Adapter je Core-RenderPath. Alle Spuren erhalten dieselbe Gesamtlatenz.
export class RackPath {
    constructor(profile="fast",totalLatency=null){
        this.rack=new EffectRack(profile);
        const n=totalLatency??this.rack.latencyFrames;
        if(!Number.isSafeInteger(n)||n<this.rack.latencyFrames||n>192000)throw new RangeError("Pfad-Latenz");
        this.latencyFrames=n;this.align=new Delay(n-this.rack.latencyFrames);this.frame=new Float32Array(2);
    }
    sample(l,r,out){this.rack.process(l,r,this.frame);this.align.process(this.frame[0],this.frame[1],out);}
    reset(){this.rack.reset();this.align.reset();}
}
