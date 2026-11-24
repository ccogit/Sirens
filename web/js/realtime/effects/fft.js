// Radix-2 FFT, vorberechnete Drehfaktoren; keine Allokation im Rechenpfad.
export class FFT {
    constructor(n) {
        if (!Number.isInteger(n) || n < 2 || n > 32768 || (n & (n - 1))) throw new RangeError("FFT-Größe");
        this.n = n;
        this.rev = new Uint32Array(n);
        this.cos = new Float64Array(n/2);
        this.sin = new Float64Array(n/2);
        for (let i=1;i<n;i++) this.rev[i]=(this.rev[i>>1]>>1)|((i&1)*(n>>1));
        for (let i=0;i<n/2;i++) {
            this.cos[i]=Math.cos(2*Math.PI*i/n);
            this.sin[i]=Math.sin(2*Math.PI*i/n);
        }
    }
    run(re, im, inverse=false) {
        const n=this.n;
        for(let i=0;i<n;i++){
            const j=this.rev[i];
            if(j>i){let v=re[i];re[i]=re[j];re[j]=v;v=im[i];im[i]=im[j];im[j]=v;}
        }
        for(let len=2;len<=n;len*=2){
            const h=len/2, step=n/len;
            for(let i=0;i<n;i+=len) for(let j=0;j<h;j++){
                const k=j*step,a=i+j,b=a+h,c=this.cos[k],s=this.sin[k]*(inverse?1:-1);
                const x=re[b]*c-im[b]*s,y=re[b]*s+im[b]*c;
                re[b]=re[a]-x;im[b]=im[a]-y;re[a]+=x;im[a]+=y;
            }
        }
        if(inverse) for(let i=0;i<n;i++){re[i]/=n;im[i]/=n;}
    }
}
