// Ein AudioContext, kein Timer für den Einsatz. Shell liefert den exakten
// Anker von AudioCore.play() sowie den Dry-Gain vor dem Worklet-Eingang.
export function createPadAudio({core, dryGain, anchor, input=0, previewInput=1, safetyFrames=256}) {
  const ctx=core.context, rate=core.rate;
  let active=null, preview=null;
  const time=f=>f/rate;
  function mapping(){
    const a=anchor();
    if(!a || !core.clock.playing || a.epoch!==core.clock.epoch || core.loopLength ||
        !Number.isSafeInteger(a.frame) || !Number.isSafeInteger(a.source))return null;
    return a;
  }
  function now(){
    const a=mapping();
    if(!a)throw new Error("Keine gültige Audio-Zeitachse");
    return Math.max(a.source,a.source+core.frame()-a.frame);
  }
  function remove(s){if(!s)return;try{s.stop();}catch{}s.disconnect();}
  function stopPreview(){remove(preview);preview=null;}
  function reset(){
    stopPreview();
    if(active){remove(active.source);active.gain.disconnect();active=null;}
    dryGain.gain.cancelScheduledValues(ctx.currentTime);
    dryGain.gain.setValueAtTime(1,ctx.currentTime);
  }
  return {
    now,stopPreview,reset,
    preview(buffer){
      if(!mapping() || previewInput===input || !core.transports[previewInput])
        throw new Error("Vorhörbus nicht verfügbar");
      stopPreview();preview=ctx.createBufferSource();preview.buffer=buffer;
      preview.connect(core.node,0,previewInput);
      preview.start();
    },
    schedule(plan,buffer){
      const a=mapping();
      if(!a || buffer.sampleRate!==rate || plan.status!=="scheduled" ||
         !Number.isSafeInteger(plan.startFrame) || !Number.isSafeInteger(plan.durationFrames) ||
         plan.durationFrames<=0 || !Number.isSafeInteger(plan.crossfadeFrames) ||
         plan.crossfadeFrames<0 || plan.crossfadeFrames*2>plan.durationFrames ||
         !Number.isFinite(plan.strength) || plan.strength<0 || plan.strength>1 ||
         !Number.isFinite(plan.playbackRate) || plan.playbackRate<=0)return false;
      const start=a.frame+plan.startFrame-a.source, end=start+plan.durationFrames;
      if(start<core.frame()+safetyFrames || (active && core.frame()<active.end))return false;
      if(active){active.gain.disconnect();active=null;}
      const s=ctx.createBufferSource(), g=ctx.createGain(), fade=plan.crossfadeFrames;
      s.buffer=buffer;s.playbackRate.value=plan.playbackRate;
      s.connect(g);g.connect(core.node,0,input);
      const envelope=(param,base,peak)=>{
        param.setValueAtTime(base,time(start));
        param.linearRampToValueAtTime(peak,time(start+fade));
        param.setValueAtTime(peak,time(end-fade));
        param.linearRampToValueAtTime(base,time(end));
      };
      g.gain.value=0;
      envelope(g.gain,0,plan.strength);envelope(dryGain.gain,1,1-plan.strength);
      active={source:s,gain:g,end};
      s.onended=()=>{s.disconnect();g.disconnect();if(active?.source===s)active=null;};
      try{s.start(time(start));s.stop(time(end));}
      catch{reset();return false;}
      return true;
    }
  };
}
