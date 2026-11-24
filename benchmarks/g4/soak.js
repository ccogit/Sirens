// DevTools-Snippet auf der lokalen Sirens-Seite; beobachtet den echten AudioCore.
// Vorher Performance-Profil wählen, Wiedergabe mit ausreichender Loop-Dauer starten.
// Kein Start eines Modells, keine Audiodaten, kein Token im Bericht.
(async()=>{
  const {AudioCore}=await import("/js/realtime/audio_core.js");
  const core=AudioCore.owner;
  if(!core || !core.status || !core.clock.playing)throw Error("Aktive Wiedergabe erforderlich");
  const seconds=Number(prompt("Messdauer: 7200 (Performance) oder 1800 (Streaming-Modell)","7200"));
  if(![7200,1800].includes(seconds))throw Error("Ungültige Messdauer");
  const raw={zeitpunkt:new Date().toISOString(),requested_seconds:seconds,elapsed_seconds:0,
    audio_seconds:0,underruns:0,interruptions:0,visibility_changes:0,epoch_changes:0,
    completed:false,error:null};
  const started=performance.now(), firstFrame=core.status.cursor;
  let previous=core.status, hidden=document.hidden;
  const visibility=()=>{raw.visibility_changes++;};
  document.addEventListener("visibilitychange",visibility);
  try {
    while(performance.now()-started<seconds*1000){
      await new Promise(r=>setTimeout(r,100));
      if(AudioCore.owner!==core||core.closed)throw Error("AudioCore gewechselt oder beendet");
      if(!core.clock.playing||core.context.state!=="running")throw Error("Wiedergabe unterbrochen");
      const status=core.status;
      if(!status||!Array.isArray(status.streams))throw Error("Telemetrie fehlt");
      if(status.epoch!==previous.epoch)raw.epoch_changes++;
      if(status.streams.length!==previous.streams.length)throw Error("Spurzahl geändert");
      status.streams.forEach((s,i)=>{
        const old=previous.streams[i].underruns;
        if(!Number.isInteger(s.underruns)||!Number.isInteger(old))throw Error("Underrun-Zähler fehlt");
        raw.underruns+=s.underruns>=old?s.underruns-old:s.underruns;
      });
      if(document.hidden&&!hidden)raw.interruptions++;
      hidden=document.hidden;
      previous=status;
    }
    raw.completed=true;
  }catch(e){raw.error=String(e);raw.interruptions++;}
  finally {
    raw.elapsed_seconds=(performance.now()-started)/1000;
    raw.audio_seconds=(previous.cursor-firstFrame)/core.rate;
    document.removeEventListener("visibilitychange",visibility);
    const url=URL.createObjectURL(new Blob([JSON.stringify(raw,null,2)],{type:"application/json"}));
    const a=document.createElement("a");a.href=url;a.download="wp19-soak-roh.json";a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);console.log(raw);
  }
})();
