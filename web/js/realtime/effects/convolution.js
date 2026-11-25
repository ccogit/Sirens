import {FFT} from "./fft.js";
import {Effect,Smooth} from "./effect.js";
export const irProfiles=Object.freeze({fast:512,standard:2048,detail:8192});
export function generatedIR(length,decay=5){
    if(!Number.isInteger(length)||length<1||length>8192)throw new RangeError("IR-Länge");
    const a=new Float32Array(length);a[0]=1;
    let seed=17;
    for(let i=1;i<length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;a[i]=(seed/4294967296*2-1)*Math.exp(-decay*i/length)*0.25/Math.sqrt(length);}
    return a;
}
function spectrum(n){return {re:new Float64Array(n),im:new Float64Array(n)};}
class PartitionedChannel {
    constructor(a,b,size){
        this.size=size;this.n=size*2;this.fft=new FFT(this.n);
        this.parts=Math.ceil(Math.max(a.length,b.length)/size);
        this.ir=[a,b].map(ir=>Array.from({length:this.parts},(_,p)=>{
            const s=spectrum(this.n);for(let i=0;i<size;i++)s.re[i]=ir[p*size+i]||0;
            this.fft.run(s.re,s.im);return s;
        }));
        this.history=Array.from({length:this.parts},()=>spectrum(this.n));
        this.sum=[spectrum(this.n),spectrum(this.n)];
        this.tail=[new Float64Array(size),new Float64Array(size)];
        this.out=[new Float64Array(size),new Float64Array(size)];
        this.input=new Float64Array(size);this.pos=0;this.head=0;
    }
    step(x,morph){
        const p=this.pos,y=this.out[0][p]*(1-morph)+this.out[1][p]*morph;
        this.input[p]=x;
        if(++this.pos===this.size){
            this.pos=0;const s=this.history[this.head];s.re.fill(0);s.im.fill(0);s.re.set(this.input);
            this.fft.run(s.re,s.im);
            for(let q=0;q<2;q++){
                const acc=this.sum[q];acc.re.fill(0);acc.im.fill(0);
                for(let j=0;j<this.parts;j++){
                    const h=this.ir[q][j],v=this.history[(this.head-j+this.parts)%this.parts];
                    for(let k=0;k<this.n;k++){
                        acc.re[k]+=h.re[k]*v.re[k]-h.im[k]*v.im[k];
                        acc.im[k]+=h.re[k]*v.im[k]+h.im[k]*v.re[k];
                    }
                }
                this.fft.run(acc.re,acc.im,true);
                for(let k=0;k<this.size;k++){this.out[q][k]=acc.re[k]+this.tail[q][k];this.tail[q][k]=acc.re[k+this.size];}
            }
            this.head=(this.head+1)%this.parts;
        }
        return y;
    }
    reset(){for(const s of this.history){s.re.fill(0);s.im.fill(0);}for(const a of [...this.out,...this.tail,this.input])a.fill(0);this.pos=this.head=0;}
}
export class ConvolutionEffect extends Effect {
    constructor(profile="standard",a=null,b=null){
        const len=irProfiles[profile];if(!len)throw new RangeError("IR-Profil");
        const size=128;super(size);
        a=a??generatedIR(len,8);b=b??generatedIR(len,2);
        for(const ir of [a,b])if(!(ir instanceof Float32Array)||!ir.length||ir.length>len||ir.some(v=>!Number.isFinite(v)||Math.abs(v)>1))throw new TypeError("Ungültige IR");
        this.channels=[new PartitionedChannel(a,b,size),new PartitionedChannel(a,b,size)];
        this.morph=new Smooth(0,0,1,profile==="fast"?128:512);
    }
    setMorph(v){this.morph.set(v);}
    render(l,r,out){const m=this.morph.tick();out[0]=this.channels[0].step(l,m);out[1]=this.channels[1].step(r,m);}
    reset(){super.reset();for(const c of this.channels)c.reset();}
}
