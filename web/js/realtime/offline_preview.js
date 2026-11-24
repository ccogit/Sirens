import {AudioCore} from "./audio_core.js";

// Nur explizites Vorhören startet einen Core. Alle Wechsel werden serialisiert;
// Panic invalidiert auch ein noch ausstehendes open() und stoppt sofort die Quelle.
export function createOfflinePreview({openCore=()=>AudioCore.open([0]),beforePlay=()=>{},onStatus=()=>{}}={}) {
  let prepared=null, core=null, epoch=0, tail=Promise.resolve(), playing=false;
  const enqueue=fn=>{
    const next=tail.then(fn);tail=next.catch(()=>{});return next;
  };
  const release=async()=>{
    const old=core;core=null;playing=false;
    try{if(old)await old.destroy();}finally{onStatus();}
  };
  function stop(clear=false){
    epoch++;if(clear)prepared=null;
    if(core){core.stopSources();core.param(1,{mix:0,gain:0,bypass:true});}
    playing=false;onStatus();return enqueue(release);
  }
  return {
    get ready(){return !!prepared;},get playing(){return playing;},
    prepare(samples,rate){
      if(!(samples instanceof Float32Array)||!samples.length||samples.length%2||
        !samples.every(Number.isFinite)||![44100,48000].includes(rate))throw new Error("Ungültige Vorhördaten");
      const closing=stop();prepared={samples,rate};onStatus();return closing;
    },
    stop,
    play(){
      const current=++epoch, data=prepared;
      if(!data)return Promise.resolve();
      return enqueue(async()=>{
        await release();
        if(current!==epoch)return;
        await beforePlay();
        if(current!==epoch)return;
        try{
          core=await openCore();
          if(current!==epoch){await release();return;}
          const buffer=core.context.createBuffer(2,data.samples.length/2,data.rate);
          for(let ch=0;ch<2;ch++){
            const out=buffer.getChannelData(ch);
            for(let i=0;i<out.length;i++)out[i]=Math.max(-1,Math.min(1,data.samples[2*i+ch]));
          }
          core.param(1,{mix:0,gain:1,bypass:true});
          core.play([buffer]);playing=true;onStatus();
          // Das Ende der Quelle gibt auch den exklusiven Core frei.
          const source=core.sources[0];
          if(source)source.onended=()=>{if(epoch===current)void stop().catch(()=>{});};
        }catch(e){await release();throw e;}
      });
    }
  };
}
