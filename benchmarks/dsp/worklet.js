import {EffectRack} from "../../web/js/realtime/effects/rack.js";
// Messpfad mit synthetischem Stereo-Signal, gleicher Rack-Code wie im Core-Hook.
class DSPProbe extends AudioWorkletProcessor {
    constructor(options){
        super();const {profile,stems}=options.processorOptions;
        this.racks=Array.from({length:stems},()=>new EffectRack(profile));
        this.probe=new EffectRack(profile);this.dryRef=new EffectRack(profile);this.wetRef=new EffectRack(profile);
        this.wetRef.setParameter(2,"wet",1);
        this.latency=this.racks[0].latencyFrames;this.frame=new Float32Array(2);
        this.a=new Float32Array(2);this.b=new Float32Array(2);this.c=new Float32Array(2);
        this.t=0;this.first=-1;this.pending=-1;this.active=false;this.mode=false;
        this.port.onmessage=({data})=>{
            if(data.type==="load"){
                for(const rack of this.racks)rack.applyPreset("cloud");
                this.mode=true;
            }else if(data.type==="probe"&&this.pending===-1){
                this.probe.setParameter(2,"wet",this.active?0:1);
                this.active=!this.active;this.pending=data.id;
                this.receivedFrame=currentFrame;this.firstChange=null;
            }
        };
    }
    process(_inputs,outputs){
        const out=outputs[0];
        for(let i=0;i<out[0].length;i++){
            const t=this.t++,x=t===512?.25:t>this.latency+1024?.05*Math.sin(2*Math.PI*375*t/sampleRate):0;
            let l=0,r=0;
            for(let j=0;j<this.racks.length;j++){
                this.racks[j].process(x,-x,this.frame);l+=this.frame[0];r+=this.frame[1];
            }
            l/=this.racks.length;r/=this.racks.length;
            if(this.first<0&&Math.abs(l)>0.1){
                this.first=t;this.port.postMessage({type:"impulse",frames:t-512,declared:this.latency,rate:sampleRate});
            }
            this.probe.process(x,-x,this.a);
            this.dryRef.process(x,-x,this.b);this.wetRef.process(x,-x,this.c);
            // Beide Referenzen laufen stationär und synchron. Die Differenz
            // misst Wet-Wirkung auch bei wechselndem Vorzeichen des Signals.
            if(this.pending!==-1){
                const old=this.active?this.b[0]:this.c[0],target=this.active?this.c[0]:this.b[0];
                const span=Math.abs(target-old),frame=currentFrame+i;
                if(span>1e-6){
                    if(this.firstChange===null&&Math.abs(this.a[0]-old)>span*.01)this.firstChange=frame;
                    if(this.firstChange!==null&&Math.abs(this.a[0]-target)<=span*.1){
                        this.port.postMessage({type:"probe",id:this.pending,frame,
                            firstFrame:this.firstChange,receivedFrame:this.receivedFrame});
                        this.pending=-1;
                    }
                }
            }
            // Der gemessene Pfad ist selbst hörbar; Referenz bleibt stumm.
            if(this.mode){l=(l+this.a[0])*0.5;r=(r+this.a[1])*0.5;}
            out[0][i]=Math.max(-.89,Math.min(.89,l));out[1][i]=Math.max(-.89,Math.min(.89,r));
        }
        return true;
    }
}
registerProcessor("sirens-dsp-probe",DSPProbe);
