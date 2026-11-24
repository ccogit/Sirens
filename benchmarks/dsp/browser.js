const byId=id=>document.getElementById(id);
let context,node,result,interval,timeout,stopped=true;
const show=()=>{byId("output").textContent=JSON.stringify(result,null,2);};
async function stop(){
    stopped=true;clearInterval(interval);clearTimeout(timeout);
    if(context){await context.close();context=null;}
    byId("start").disabled=false;
}
byId("stop").onclick=stop;
byId("start").onclick=async()=>{
    if(!stopped)return;stopped=false;byId("start").disabled=true;byId("save").disabled=true;
    const profile=byId("profile").value,stems=Number(byId("stems").value);
    result={backend:"cpu",profile,stems,rate:null,impulse:null,control_ms:[],render_ack_ms:[],timeouts:0,device_underruns:null,output_latency_ms:null};
    try{
        context=new AudioContext();await context.resume();result.rate=context.sampleRate;
        await context.audioWorklet.addModule("./worklet.js");
        node=new AudioWorkletNode(context,"sirens-dsp-probe",{numberOfInputs:0,numberOfOutputs:1,outputChannelCount:[2],processorOptions:{profile,stems}});
        let id=0,pending=null,issued=0;
        node.port.onmessage=({data:m})=>{
            if(stopped)return;
            if(m.type==="impulse"){
                result.impulse=m;node.port.postMessage({type:"load"});
                interval=setInterval(()=>{
                    if(pending!==null)return;
                    pending=id++;issued=performance.now();node.port.postMessage({type:"probe",id:pending});
                    timeout=setTimeout(()=>{result.timeouts++;byId("save").disabled=false;show();stop();},2000);
                },250);
            }else if(m.type==="probe"&&m.id===pending){
                clearTimeout(timeout);const now=performance.now(),ts=context.getOutputTimestamp?.();
                result.render_ack_ms.push(now-issued);
                // AudioContext-Zeitstempel bildet die Renderposition auf die
                // geschätzte Ausgabezeit ab; kein physischer Loopback.
                if(ts&&ts.contextTime>0&&ts.performanceTime>0){
                    const heard=ts.performanceTime+(m.frame/context.sampleRate-ts.contextTime)*1000;
                    result.control_ms.push(Math.max(0,heard-issued));
                }
                if(Number.isFinite(context.outputLatency))result.output_latency_ms=context.outputLatency*1000;
                pending=null;show();
                if(result.render_ack_ms.length>=100){byId("save").disabled=false;stop();}
            }
        };
        node.connect(context.destination);show();
    }catch(error){byId("output").textContent=String(error);await stop();}
};
byId("save").onclick=()=>{
    const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="wp09-"+result.profile+"-"+result.stems+".json";a.click();URL.revokeObjectURL(url);
};
