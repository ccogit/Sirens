// Auf der lokalen Sirens-Seite als DevTools-Snippet ausführen.
// Keine Audio-/Token-Dateien speichern; nur Rohmesswerte.
(async()=>{
  const {AudioCore}=await import("/js/realtime/audio_core.js");
  const {createRtApi,MOCK_ASSET}=await import("/js/realtime/api.js");
  const {decodeDry}=await import("/js/realtime/shell.js");
  const {unpack}=await import("/js/realtime/pcm.js");
  const {Recorder}=await import("/js/realtime/recorder.js");
  const api=createRtApi(), delay=ms=>new Promise(r=>setTimeout(r,ms));
  const raw={zeitpunkt:new Date().toISOString(),completed:false,elapsed_seconds:0,
    underruns:null,skipped_blocks:0,interruptions:0,matched_blocks:0,invalid_blocks:0,
    alignment_max_samples:null,dry_fallback:false,worker_error:false,sample_rate:null,error:null};
  let core,session,ws,recorder;
  try{
    // 48 kHz anfordern; läuft das Gerät mit 44,1 kHz, rechnet der Browser um (digitale Prüfung unverändert).
    const C48=class extends AudioContext{constructor(o){super({...(o||{}),sampleRate:48000});}};
    core=await AudioCore.open([0],C48);
    raw.sample_rate=core.rate;
    if(core.rate!==48000)throw Error("48 kHz benötigt");
    const asset=await api.asset(MOCK_ASSET);
    session=await api.create("mock",core.rate);
    session=await api.command(session,"load",{asset_id:asset.id});
    for(let i=0;i<200&&session.state==="loading";i++){await delay(50);session=await api.session(session);}
    if(session.state!=="ready")throw Error("Sitzung nicht bereit");
    const dry=decodeDry(core,await api.dry(session),asset);
    const left=dry.getChannelData(0),right=dry.getChannelData(1);
    const transport=await api.transport(session);
    ws=core.connect("ws://127.0.0.1:"+transport.port+"/pcm",transport.token);
    await Promise.race([new Promise((ok,fail)=>{ws.onopen=ok;ws.onerror=fail;}),
      delay(5000).then(()=>{throw Error("Sidecar-Zeitgrenze");})]);
    session=await api.command(session,"set_param",{name:"gain",value:.5});
    session=await api.command(session,"play");
    const {epoch,frame:start}=core.reset(0,true,core.frame()+Math.round(core.rate*.25));
    // Kontinuierlicher Referenzloop ohne Epoch-Wechsel, isoliert die Transportdeckung.
    const player=core.context.createBufferSource();player.buffer=dry;player.loop=true;
    player.connect(core.node,0,0);player.start(start/core.rate);core.sources.push(player);
    core.param(1,{mix:1,gain:1});
    const expected=new Map();
    ws.addEventListener("message",e=>{
      try{
        const {header:h,payload:p}=unpack(new Uint8Array(e.data));
        const request=expected.get(h.seq);expected.delete(h.seq);
        if(!request||h.epoch!==epoch||h.start_frame!==BigInt(request.start_frame)||h.nframes!==request.nframes)
          throw Error("Header");
        const v=new DataView(p.buffer,p.byteOffset,p.byteLength);
        let exact=true;
        for(let i=0;i<h.nframes;i++){
          const j=request.source_frame+i;
          if(v.getFloat32(i*8,true)!==Math.fround(left[j]*.5)||
             v.getFloat32(i*8+4,true)!==Math.fround(right[j]*.5)){exact=false;break;}
        }
        if(!exact)throw Error("Fixture");
        raw.matched_blocks++;raw.alignment_max_samples=0;
      }catch{raw.invalid_blocks++;}
    });
    let next=start,seq=0,wasInterrupted=false;
    const stopAt=start+1800*core.rate;
    while((core.status?.cursor??start)<stopAt && ws.readyState===WebSocket.OPEN){
      const now=core.frame(),interrupted=document.hidden||core.context.state!=="running";
      if(interrupted&&!wasInterrupted)raw.interruptions++;
      wasInterrupted=interrupted;
      if(next<now){raw.skipped_blocks++;next=now;}
      // Angeforderte plus beim Transport wartende Blöcke zusammen höchstens 8 (Transport-Grenze), sonst verwirft er.
      while(next+1024<=now+12288 && expected.size+core.transports[0].pending.size<8){
        const source=(next-start)%asset.nframes,n=Math.min(1024,asset.nframes-source);
        if(n<256){next+=n;raw.skipped_blocks++;continue;}
        const q={epoch:session.epoch,audio_epoch:epoch,seq:seq++,source_frame:source,start_frame:next,nframes:n};
        expected.set(q.seq,q);next+=n;
        try{await api.render(session,q);}catch{expected.delete(q.seq);raw.skipped_blocks++;}
      }
      for(const [key,q] of expected)if(q.start_frame+q.nframes<now){expected.delete(key);raw.skipped_blocks++;}
      await delay(10);
    }
    raw.elapsed_seconds=Math.max(0,((core.status?.cursor??start)-start)/core.rate);
    raw.completed=raw.elapsed_seconds>=1800&&ws.readyState===WebSocket.OPEN;
    raw.underruns=core.status?.streams[0]?.underruns??null;
    // Separater Fehlerabschnitt: nach dem Soak Worker-PID manuell gezielt beenden.
    // Kein Prozesskill aus dem Browser, kein unbefugter Zugriff.
    if(raw.completed){
      console.log("Jetzt innerhalb von 120 Sekunden ausschließlich den zu dieser Sitzung gehörenden Mock-Worker beenden (siehe README).");
      const deadline=Date.now()+120000;
      while(ws.readyState===WebSocket.OPEN&&Date.now()<deadline)await delay(100);
      if(ws.readyState!==WebSocket.OPEN){
        await delay(500);
        raw.worker_error=(await api.session(session)).state==="error";
        let checked=0,peak=0;
        recorder=await Recorder.attach(core,async(startFrame,bytes)=>{
          const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
          for(let i=0;i<v.byteLength;i+=4)peak=Math.max(peak,Math.abs(v.getFloat32(i,true)));
          checked+=v.byteLength/8;return startFrame+v.byteLength/8;
        },async()=>{});
        recorder.start();await delay(1000);
        const result=await recorder.stop();recorder=null;
        raw.dry_fallback=!result.error&&checked>=4096&&peak>=.24&&peak<=.251;
      }
    }
  }catch(e){raw.error=String(e);}
  finally{
    if(recorder)recorder.fail("Messung beendet");
    try{await core?.destroy();}catch{}
    try{if(session)await api.close(session);}catch(e){raw.error??=String(e);}
    const url=URL.createObjectURL(new Blob([JSON.stringify(raw,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="wp06-g2-roh.json";a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);console.log(raw);
  }
})();
