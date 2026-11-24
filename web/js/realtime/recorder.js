// Stummer Worklet-Abgriff hinter dem Master-Limiter. Acht Transferpuffer.
export const BLOCK = 2048;
export const POOL = 8;
export class Capture {
    constructor(emit) {
        this.emit=emit; this.pool=[]; this.active=false;
        this.frame=0; this.used=0; this.view=null;
    }
    recycle(buffer) {
        if(buffer instanceof ArrayBuffer && buffer.byteLength===BLOCK*8 &&
            this.pool.length<POOL) this.pool.push(new DataView(buffer));
    }
    start() {
        if(this.active || this.pool.length!==POOL) throw new Error("Aufnahmepuffer fehlen");
        this.active=true;
    }
    flush() {
        if(!this.used)return;
        const buffer=this.view.buffer, frames=this.used;
        this.view=null; this.used=0;
        this.emit({type:"block",buffer,frames,startFrame:this.frame},[buffer]);
        this.frame+=frames;
    }
    stop(error=null) {
        if(!this.active)return;
        this.active=false; this.flush();
        this.emit({type:"ended",frames:this.frame,error});
    }
    process(left,right) {
        if(!this.active || !left)return;
        for(let i=0;i<left.length;i++){
            if(!this.view){
                this.view=this.pool.pop();
                if(!this.view){this.stop("Aufnahmepuffer erschöpft");return;}
            }
            this.view.setFloat32(this.used*8,left[i],true);
            this.view.setFloat32(this.used*8+4,right?right[i]:left[i],true);
            if(++this.used===BLOCK)this.flush();
        }
    }
}
if(typeof AudioWorkletProcessor!=="undefined"){
    class RecorderProcessor extends AudioWorkletProcessor {
        constructor(){
            super();
            this.capture=new Capture((m,t)=>this.port.postMessage(m,t??[]));
            this.port.onmessage=({data:m})=>{
                if(m.type==="recycle")this.capture.recycle(m.buffer);
                else if(m.type==="start")this.capture.start();
                else if(m.type==="stop")this.capture.stop();
            };
        }
        process(inputs){
            this.capture.process(inputs[0]?.[0],inputs[0]?.[1]);
            return true; // Ausgänge bleiben stumm.
        }
    }
    registerProcessor("sirens-recorder-v1",RecorderProcessor);
}
export class Recorder {
    constructor(port,send,finish,cleanup=()=>{}){
        this.port=port; this.send=send; this.finish=finish; this.cleanup=cleanup;
        this.queue=Promise.resolve(); this.next=0; this.error=null;
        this.state="idle"; this.pending=0; this.failed=false;
        this.done=new Promise(resolve=>{this.resolve=resolve;});
        port.onmessage=({data:m})=>this.receive(m);
    }
    static async attach(core,send,finish){
        await core.context.audioWorklet.addModule(new URL("./recorder.js",import.meta.url));
        const node=new AudioWorkletNode(core.context,"sirens-recorder-v1",{
            numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[2],
            channelCount:2,channelCountMode:"explicit"});
        core.node.connect(node); node.connect(core.context.destination);
        const recorder=new Recorder(node.port,send,finish,()=>{
            core.node.disconnect(node); node.disconnect(); node.port.close();
        });
        node.onprocessorerror=()=>recorder.fail("Recorder-Worklet ausgefallen");
        return recorder;
    }
    // Nur aus expliziter Nutzeraktion aufrufen; Instanz nicht wiederverwenden.
    start(){
        if(this.state!=="idle")throw new Error("Aufnahme bereits gestartet");
        this.state="recording";
        for(let i=0;i<POOL;i++){
            const buffer=new ArrayBuffer(BLOCK*8);
            this.port.postMessage({type:"recycle",buffer},[buffer]);
        }
        this.port.postMessage({type:"start"});
    }
    stop(){
        if(this.state==="recording"){
            this.state="stopping"; this.port.postMessage({type:"stop"});
        }else if(this.state==="idle")this.complete();
        return this.done;
    }
    fail(error){
        this.error??=String(error); this.failed=true; this.complete();
    }
    receive(m){
        if(this.state!=="recording" && this.state!=="stopping")return;
        if(m.type==="ended"){
            if(m.error)this.error??=m.error;
            this.complete();return;
        }
        if(m.type!=="block")return;
        if(++this.pending>POOL || !Number.isInteger(m.frames) || m.frames<1 ||
            m.frames>BLOCK || !(m.buffer instanceof ArrayBuffer) || m.buffer.byteLength!==BLOCK*8){
            this.fail("Ungültiger Aufnahmeblock");return;
        }
        this.queue=this.queue.then(async()=>{
            if(this.failed)return;
            if(m.startFrame!==this.next)throw new Error("Lücke in der Aufnahme");
            const next=await this.send(this.next,new Uint8Array(m.buffer,0,m.frames*8));
            if(next!==this.next+m.frames)throw new Error("Aufnahmebestätigung ungültig");
            this.next=next;
            if(this.state!=="closed")this.port.postMessage({type:"recycle",buffer:m.buffer},[m.buffer]);
        }).catch(error=>{
            this.error=String(error);this.failed=true;
            // Nicht auf weitere Worklet-Nachrichten warten.
            this.complete();
        }).finally(()=>{this.pending--;});
    }
    complete(){
        if(this.state==="closed")return;
        this.state="closed";
        this.queue.then(async()=>{
            try{await this.finish();}catch(error){this.error??=String(error);}
            try{this.cleanup();}catch(error){this.error??=String(error);}
            this.resolve({frames:this.next,error:this.error});
        });
    }
}
