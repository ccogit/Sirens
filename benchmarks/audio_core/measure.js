import {AudioCore} from "../../web/js/realtime/audio_core.js";
import {pack} from "../../web/js/realtime/pcm.js";
const startButton=document.querySelector("#start"), stopButton=document.querySelector("#stop");
const status=document.querySelector("#status"), link=document.querySelector("#download");
let cancel=false;
stopButton.onclick=()=>{cancel=true;};
startButton.onclick=async()=>{
    startButton.disabled=true; stopButton.disabled=false;link.hidden=true;cancel=false;
    let core, timer, url;
    try{
        core=await AudioCore.open([0]);
        const rate=core.rate,n=1024,duration=1800;
        const {epoch,frame:start}=core.reset(0,true,core.frame()+Math.round(rate*.3));
        // Trockene Referenz und deterministischer Gain-Mock, keine Musikdatei.
        const dry=core.context.createBuffer(2,rate,rate);
        for(let c=0;c<2;c++){
            const a=dry.getChannelData(c);
            for(let i=0;i<rate;i++)a[i]=.035*Math.sin(2*Math.PI*220*i/rate);
        }
        const source=core.context.createBufferSource();source.buffer=dry;source.loop=true;
        source.connect(core.node,0,0);source.start(start/rate);core.sources.push(source);
        core.param(1,{mix:.5,gain:1});
        let seq=0,next=start,missed=0,interruptions=0,wasInterrupted=false;
        const ended=await new Promise((resolve,reject)=>{
            const tick=()=>{
                try{
                    const interrupted=core.context.state!=="running"||document.hidden;
                    if(interrupted&&!wasInterrupted)interruptions++;
                    wasInterrupted=interrupted;
                    const t=core.transports[0],s=core.status;
                    if(next<t.cursor){
                        const skip=Math.ceil((t.cursor-next)/n);next+=skip*n;seq+=skip;missed+=skip;
                    }
                    while(t.pending.size<8&&next+n<=t.cursor+t.lookahead){
                        const pcm=new Uint8Array(n*8),v=new DataView(pcm.buffer);
                        for(let i=0;i<n;i++){
                            const a=.8*dry.getChannelData(0)[(next-start+i)%rate];
                            v.setFloat32(i*8,a,true);v.setFloat32(i*8+4,a,true);
                        }
                        if(!core.push(pack({protocol_version:1,stream_id:1,epoch,seq,start_frame:BigInt(next),
                            nframes:n,channels:2,flags:0,sample_rate:rate},pcm))) break;
                        seq++;next+=n;
                    }
                    const elapsed=Math.max(0,((s?.cursor??start)-start)/rate);
                    status.textContent=elapsed.toFixed(1)+" / 1800 s; Underrun-Frames: "+(s?.streams[0].underruns??0);
                    if(cancel||elapsed>=duration)resolve({completed:!cancel,elapsed_seconds:elapsed,
                        underruns:s?.streams[0].underruns??0,skipped_blocks:missed,interruptions,
                        sample_rate:rate,base_latency_ms:Number.isFinite(core.context.baseLatency)?core.context.baseLatency*1000:null,
                        output_latency_ms:Number.isFinite(core.context.outputLatency)?core.context.outputLatency*1000:null,
                        zeitpunkt:new Date().toISOString()});
                }catch(e){reject(e);}
            };
            timer=setInterval(tick,10);tick();
        });
        clearInterval(timer);
        url=URL.createObjectURL(new Blob([JSON.stringify(ended,null,2)],{type:"application/json"}));
        link.href=url;link.download="wp04-rohmessung.json";link.hidden=false;
        status.textContent+="\n"+JSON.stringify(ended,null,2);
    }catch(e){status.textContent=String(e);}
    finally{clearInterval(timer);await core?.destroy();startButton.disabled=false;stopButton.disabled=true;}
};
