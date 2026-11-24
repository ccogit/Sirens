// Stereo-Frame-Schnittstelle: process(left,right,out), ohne Allokation.
export function bounded(value,min,max) {
    if(typeof value!=="number" || !Number.isFinite(value)) throw new TypeError("Ungültiger Parameter");
    return Math.min(max,Math.max(min,value));
}
export class Smooth {
    constructor(value,min,max,frames=256){
        this.min=min;this.max=max;this.frames=frames;this.value=this.target=bounded(value,min,max);this.left=0;this.step=0;
    }
    set(value){this.target=bounded(value,this.min,this.max);this.left=this.frames;this.step=(this.target-this.value)/this.frames;}
    tick(){if(this.left>0){this.value+=this.step;if(--this.left===0)this.value=this.target;}return this.value;}
}
export class Delay {
    constructor(frames){
        if(!Number.isSafeInteger(frames)||frames<0)throw new RangeError("Latenz");
        this.frames=frames;this.buf=new Float32Array(frames*2);this.pos=0;
    }
    process(l,r,out){
        if(!this.frames){out[0]=l;out[1]=r;return;}
        const p=this.pos;out[0]=this.buf[p];out[1]=this.buf[p+1];this.buf[p]=l;this.buf[p+1]=r;
        this.pos=(p+2)%this.buf.length;
    }
    reset(){this.buf.fill(0);this.pos=0;}
}
export class Effect {
    constructor(latencyFrames){
        this.latencyFrames=latencyFrames;this.delay=new Delay(latencyFrames);
        this.wet=new Smooth(1,0,1);this.bypass=false;this.dryFrame=new Float32Array(2);this.wetFrame=new Float32Array(2);
    }
    setWet(v){this.wet.set(v);}
    setBypass(v){if(typeof v!=="boolean")throw new TypeError("Bypass");this.bypass=v;}
    process(l,r,out){
        this.delay.process(l,r,this.dryFrame);this.render(l,r,this.wetFrame);
        const w=this.wet.tick();
        for(let c=0;c<2;c++){
            const d=this.dryFrame[c],v=this.wetFrame[c];
            out[c]=this.bypass||w===0?d:Math.max(-4,Math.min(4,d*(1-w)+(Number.isFinite(v)?v:0)*w));
        }
    }
    reset(){this.delay.reset();}
}
