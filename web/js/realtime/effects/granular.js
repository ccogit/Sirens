import {Effect,Smooth,bounded} from "./effect.js";
export const grainProfiles=Object.freeze({fast:256,standard:512,detail:1024});
function grainSize(profile){const n=grainProfiles[profile];if(!n)throw new RangeError("Kornprofil");return n;}
// WSOLA für endliche Clips. Die Ausgabedauer ist exakt, die lokale Leserate bleibt eins.
// Gleiche Kornpositionen für beide Kanäle; Suche maximiert Korrelation im Überlapp.
export function stretchStereo(input,factor,profile="standard"){
    if(!(input instanceof Float32Array)||input.length%2)throw new TypeError("Stereo-PCM");
    factor=bounded(factor,0.5,2);const n=grainSize(profile),h=n/2,frames=input.length/2;
    const length=Math.round(frames*factor),out=new Float32Array(length*2),weights=new Float64Array(length);
    if(factor===1)return input.slice();
    let last=0;
    for(let pos=0;pos<length;pos+=h){
        const nominal=Math.round(pos/factor);
        let start=nominal;
        if(pos>0){
            let best=-Infinity;
            for(let candidate=Math.max(0,nominal-h/2);candidate<=Math.min(frames-1,nominal+h/2);candidate++){
                let dot=0,a=0,b=0;
                for(let j=0;j<h;j+=2)for(let c=0;c<2;c++){
                    const x=input[(last+h+j)*2+c]||0,y=input[(candidate+j)*2+c]||0;
                    dot+=x*y;a+=x*x;b+=y*y;
                }
                const score=dot/Math.sqrt(a*b+1e-20)-1e-6*Math.abs(candidate-nominal);
                if(score>best){best=score;start=candidate;}
            }
        }
        for(let j=0;j<n&&pos+j<length;j++){
            const w=j<h?j/h:1-(j-h)/h;
            const gain=pos===0&&j<h?1:w;
            weights[pos+j]+=gain;
            for(let c=0;c<2;c++)out[(pos+j)*2+c]+=(input[(start+j)*2+c]||0)*gain;
        }
        last=start;
    }
    for(let i=0;i<length;i++)if(weights[i])for(let c=0;c<2;c++)out[i*2+c]/=weights[i];
    return out;
}
// Zwei überlappende Körner mit begrenzter, deterministischer Leseposition.
// Cloud=0 ist ein exakter, um n Frames verzögerter Durchgang.
export class GranularEffect extends Effect {
    constructor(profile="standard"){
        const n=grainSize(profile);super(n);
        this.n=n;this.h=n/2;this.buffer=new Float32Array(n*8);this.t=0;this.offsets=new Int32Array(2);
        this.cloud=new Smooth(0,0,1,512);this.seed=1;
    }
    setCloud(v){this.cloud.set(v);}
    render(l,r,out){
        const n=this.n,h=this.h,t=this.t++,frames=this.buffer.length/2;
        const p=t%frames;this.buffer[p*2]=l;this.buffer[p*2+1]=r;
        const cloud=this.cloud.tick(),phase=t%h,k=Math.floor(t/h)%2;
        if(phase===0){
            this.seed=(Math.imul(this.seed,1664525)+1013904223)>>>0;
            this.offsets[k]=Math.round((this.seed/4294967296*2-1)*h*cloud);
        }
        const a=t-n+this.offsets[k],b=t-n+this.offsets[1-k],w=phase/h;
        for(let c=0;c<2;c++){
            const x=a<0?0:this.buffer[(a%frames)*2+c],y=b<0?0:this.buffer[(b%frames)*2+c];
            out[c]=w*x+(1-w)*y;
        }
    }
    reset(){super.reset();this.buffer.fill(0);this.t=0;this.seed=1;this.offsets.fill(0);}
}
