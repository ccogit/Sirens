import {FFT} from "./fft.js";
import {Effect,Smooth} from "./effect.js";
export const spectralProfiles=Object.freeze({fast:512,standard:1024,detail:2048});
const TAU=2*Math.PI;
const wrap=x=>x-TAU*Math.round(x/TAU);
class SpectralChannel {
    constructor(n){
        this.n=n;this.h=n/4;this.fft=new FFT(n);this.input=new Float64Array(n);this.output=new Float64Array(n*2);
        this.re=new Float64Array(n);this.im=new Float64Array(n);this.prev=new Float64Array(n/2+1);
        this.phase=new Float64Array(n/2+1);this.mag=new Float64Array(n/2+1);this.freq=new Float64Array(n/2+1);
        this.win=Float64Array.from({length:n},(_,i)=>Math.sqrt((1-Math.cos(TAU*i/n))/2));
        this.t=0;this.frozen=false;
    }
    step(x,pitch,mask,freeze){
        const n=this.n,h=this.h,t=this.t++,slot=t%(2*n);
        const y=this.output[slot];this.output[slot]=0;this.input[t%n]=x;
        if((t+1)%h!==0)return y;
        const start=t+1-n;
        for(let i=0;i<n;i++){this.re[i]=this.input[((start+i)%n+n)%n]*this.win[i];this.im[i]=0;}
        this.fft.run(this.re,this.im);
        for(let k=0;k<=n/2;k++){
            const a=Math.atan2(this.im[k],this.re[k]),expected=TAU*k*h/n;
            if(!freeze||!this.frozen){this.mag[k]=Math.hypot(this.re[k],this.im[k]);this.freq[k]=expected+wrap(a-this.prev[k]-expected);}
            this.prev[k]=a;
        }
        this.frozen=freeze;
        if(pitch!==1||freeze||mask!==1){
            this.re.fill(0);this.im.fill(0);
            for(let k=0;k<=n/2;k++){
                const source=Math.round(k/pitch);
                if(source>n/2||k>mask*n/2)continue;
                this.phase[k]=wrap(this.phase[k]+this.freq[source]*pitch);
                this.re[k]=this.mag[source]*Math.cos(this.phase[k]);this.im[k]=this.mag[source]*Math.sin(this.phase[k]);
                if(k>0&&k<n/2){this.re[n-k]=this.re[k];this.im[n-k]=-this.im[k];}
            }
            this.im[0]=this.im[n/2]=0;
        }else for(let k=0;k<=n/2;k++)this.phase[k]=this.prev[k];
        this.fft.run(this.re,this.im,true);
        for(let i=0;i<n;i++)this.output[(t+1+i)%(2*n)]+=this.re[i]*this.win[i]/2;
        return y;
    }
    reset(){for(const a of [this.input,this.output,this.prev,this.phase,this.mag,this.freq])a.fill(0);this.t=0;this.frozen=false;}
}
export class SpectralEffect extends Effect {
    constructor(profile="standard"){
        const n=spectralProfiles[profile];if(!n)throw new RangeError("FFT-Profil");
        super(n);this.channels=[new SpectralChannel(n),new SpectralChannel(n)];
        this.pitch=new Smooth(1,0.5,2,1024);this.mask=new Smooth(1,0,1,1024);this.freeze=false;
    }
    setPitch(v){this.pitch.set(v);}
    setMask(v){this.mask.set(v);}
    setFreeze(v){if(typeof v!=="boolean")throw new TypeError("Freeze");this.freeze=v;}
    render(l,r,out){const p=this.pitch.tick(),m=this.mask.tick();out[0]=this.channels[0].step(l,p,m,this.freeze);out[1]=this.channels[1].step(r,p,m,this.freeze);}
    reset(){super.reset();for(const c of this.channels)c.reset();}
}
