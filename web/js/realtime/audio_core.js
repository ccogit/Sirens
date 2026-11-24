import {Transport} from "./transport.js";
import {Clock} from "./clock.js";

// Pro Suite ein Ausgabepfad. Erzeugung und Resume ausschließlich nach Nutzeraktion.
export class AudioCore {
    static async open(latencies=[0], Context=globalThis.AudioContext) {
        if(!Context || !latencies.length || latencies.length>8 ||
            latencies.some(n=>!Number.isInteger(n)||n<0||n>192000)) throw new RangeError("Audiokonfiguration");
        const context=new Context();
        try {
            await context.resume();
            await context.audioWorklet.addModule(new URL("./worklet_processor.js",import.meta.url));
            return new AudioCore(context,latencies);
        } catch(error) { await context.close(); throw error; }
    }
    constructor(context,latencies) {
        this.context=context; this.clock=new Clock(context.sampleRate); this.sources=[];
        this.node=new AudioWorkletNode(context,"sirens-core-v1",{
            numberOfInputs:latencies.length,numberOfOutputs:1,outputChannelCount:[2],
            channelCount:2,channelCountMode:"explicit",processorOptions:{latencies}
        });
        this.node.connect(context.destination);
        this.transports=latencies.map((_,i)=>new Transport(this.node.port,i+1,context.sampleRate));
        this.status=null; this.socket=null; this.waiting=false; this.closed=false;
        this.node.port.onmessage=({data:m})=>{
            if(m.type==="reject") this.transports[m.stream-1]?.acknowledge(m);
            if(m.type!=="status") return;
            this.waiting=false; this.status=m;
            if(m.epoch>this.clock.epoch) {
                this.clock.epoch=m.epoch;
                for(const t of this.transports) t.reset(m.epoch,m.cursor);
            }
            if(m.epoch===this.clock.epoch) this.transports.forEach((t,i)=>t.advance(m.epoch,m.streams[i].cursor));
        };
        this.timer=setInterval(()=>{
            if(!this.waiting) {this.waiting=true; this.node.port.postMessage({type:"status"});}
        },20);
    }
    get rate(){return this.context.sampleRate;}
    frame(){return Clock.frame(this.context.currentTime,this.rate);}
    reset(source=0,active=true,frame=this.frame()+Math.round(this.rate*.1),loopLength=0) {
        if(!Number.isSafeInteger(frame)||frame<this.frame()||!Number.isSafeInteger(loopLength)||loopLength<0)
            throw new RangeError("Startframe");
        const epoch=this.clock.seek(source);
        this.clock.playing=active;
        for(const t of this.transports) t.reset(epoch,frame);
        this.node.port.postMessage({type:"reset",epoch,frame,active,loopLength});
        return {epoch,frame};
    }
    stopSources(){
        for(const s of this.sources){try{s.stop();}catch{} s.disconnect();}
        this.sources=[];
    }
    play(buffers,{source=0,frame=this.frame()+Math.round(this.rate*.1),loopLength=0}={}) {
        if(buffers.length>this.transports.length) throw new RangeError("Spuren");
        this.stopSources();
        const state=this.reset(source,true,frame,loopLength);
        for(let i=0;i<buffers.length;i++){
            const s=this.context.createBufferSource();s.buffer=buffers[i];s.connect(this.node,0,i);
            if(loopLength){s.loop=true;s.loopStart=source/this.rate;s.loopEnd=(source+loopLength)/this.rate;}
            s.start(frame/this.rate,source/this.rate);this.sources.push(s);
        }
        return state;
    }
    stop(){this.stopSources();return this.reset(0,false);}
    param(stream,values){this.node.port.postMessage({...values,type:"param",stream});}
    push(block){
        if(this.closed) return false;
        const view=new DataView(block instanceof ArrayBuffer?block:block.buffer,block.byteOffset??0,block.byteLength);
        if(view.byteLength<32) return false;
        return this.transports[view.getUint32(4,true)-1]?.push(block)??false;
    }
    connect(url,token){
        const u=new URL(url);
        if(u.protocol!=="ws:"||u.hostname!=="127.0.0.1"||u.username||u.password||u.pathname!=="/pcm"||u.search||u.hash)
            throw new Error("Nur lokaler PCM-Sidecar");
        if(!/^[A-Za-z0-9_-]{22,128}$/.test(token)) throw new Error("Sitzungstoken ungültig");
        this.socket?.close();
        const ws=this.socket=new WebSocket(u,["sirens.pcm.v1",token]); ws.binaryType="arraybuffer";
        ws.onmessage=e=>{if(this.socket===ws) try{this.push(e.data);}catch{ws.close(1002);}};
        return ws;
    }
    async destroy(){
        if(this.closed)return;this.closed=true;clearInterval(this.timer);this.socket?.close();
        this.stopSources();this.node.port.onmessage=null;this.node.port.close();this.node.disconnect();
        await this.context.close();
    }
}
