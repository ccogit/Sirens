import { h } from "../dom.js";
import { api as catalogApi } from "../api.js";
import { createRtApi, MOCK_ASSET } from "./api.js";
import { AudioCore } from "./audio_core.js";
import { frameAtRate, resample } from "./transport.js";
import { Recorder } from "./recorder.js";
import { filterCatalog, sessionExport } from "./integration.js";
import { mountHookTools } from "./hook_tools.js";
import { mountSeparationJobs } from "./advanced_stems.js";
import { createOfflinePreview } from "./offline_preview.js";
import { createBeatGrid } from "./beat_grid.js";
import { deriveState, modeLabel } from "./capabilities.js";
import { gpuText, latencyText } from "./gpu_panel.js";
import { createResources, keyAction, DEFAULT_PRESET, readPresets, savePreset, normalizePreset } from "./controls.js";

// Der Mock akzeptiert ausschließlich sein synthetisches Asset. Keine Katalogpfade als RT-IDs.
export function createSessionController(api) {
  let session=null, tail=Promise.resolve(), closed=false, generation=0;
  const enqueue = fn => {
    const result=tail.then(fn);
    tail=result.catch(()=>{});
    return result;
  };
  const cancelled=Symbol("Sitzung gestoppt");
  const command = async (current,name,args={}) => {
    if (closed || current!==generation) throw cancelled;
    session=await api.command(session,name,args);
    if (closed || current!==generation) throw cancelled;
    return session;
  };
  return {
    get state() { return session?.state || "created"; },
    run(fn) {
      const current=generation;
      return enqueue(async()=>{
        if (closed || current!==generation) return;
        const send=(name,args)=>command(current,name,args);
        try {
          if (!session) {
            session=await api.create("mock");
            await send("load",{asset_id:MOCK_ASSET});
          }
          return await fn(send,()=>session.state);
        } catch(e) { if(e!==cancelled) throw e; }
      });
    },
    reset() { generation++; return enqueue(async()=>{ if(session) { await api.close(session); session=null; } }); },
    destroy() {
      closed=true;
      return enqueue(async()=>{ if(session) { await api.close(session); session=null; } });
    },
  };
}
const GPU_PROFILES=Object.freeze(["Eco","Performance","Neural","Training/Render"]);
const wait = ms => new Promise(resolve=>setTimeout(resolve,ms));
const timed = (promise,ms) => {
  let timer;
  return Promise.race([promise,new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(new Error("Zeitgrenze überschritten")),ms);
  })]).finally(()=>clearTimeout(timer));
};

const MOCK_RATE=48000;
export function decodeDry(core, raw, asset) {
  if(!(raw instanceof ArrayBuffer) || raw.byteLength!==asset.nframes*8 || asset.sample_rate!==MOCK_RATE)
    throw new Error("Ungültige PCM-Quelle");
  const view=new DataView(raw), source=new Float32Array(asset.nframes*2);
  for(let i=0;i<source.length;i++){
    const sample=view.getFloat32(i*4,true);
    source[i]=Number.isFinite(sample)?sample:0;
  }
  const pcm=core.rate===MOCK_RATE?source:resample(source,MOCK_RATE,core.rate);
  const buffer=core.context.createBuffer(2,pcm.length/2,core.rate);
  for(let channel=0;channel<2;channel++){
    const samples=buffer.getChannelData(channel);
    for(let frame=0;frame<samples.length;frame++)samples[frame]=pcm[frame*2+channel];
  }
  return buffer;
}

// Die Pumpe zählt Quell- und Wire-Frames in 48 kHz, die Ausgabefristen
// dagegen im Gerätraster. Absolute Quellgrenzen führen den Rundungsrest mit.
function deviceFrame(g, source, rate) {
  return g.frame+frameAtRate(source,MOCK_RATE,rate)-frameAtRate(g.source0,MOCK_RATE,rate);
}
function renderGeneration(epoch, frame, source, length, rate, seek=false) {
  const g={audioEpoch:epoch, frame, output:frame, source, source0:source, seq:0,
    wireFrame:frameAtRate(frame,rate,MOCK_RATE), seek};
  g.end=deviceFrame(g,length,rate);
  return g;
}
export function makeRenderPlan(state, offset, length, loop, seek=false, rate=MOCK_RATE) {
  return {current:renderGeneration(state.epoch,state.frame,offset,length,rate,seek),
    next:null, loop, length, offset, rate};
}
export async function fillRenderPlan(plan, core, session, render, active=()=>true) {
  if(!active())return;
  const now=core.frame(), capacity=core.transports[0].lookahead, rate=plan.rate;
  const lead=Math.min(12288,capacity-2048);
  let current=plan.current;
  if(core.clock.epoch>current.audioEpoch && plan.loop && core.status){
    const frame=current.end+(core.clock.epoch-current.audioEpoch-1)*plan.loop;
    current=plan.current=plan.next?.audioEpoch===core.clock.epoch?plan.next:
      renderGeneration(core.clock.epoch,frame,plan.offset,plan.length,rate);
    plan.next=null;
  }
  const upcoming=core.loopPlan;
  const latency=Math.max(Math.ceil(core.rate*.05),core.renderLatencyFrames||0);
  if(plan.loop && upcoming?.epoch===current.audioEpoch+1 && !plan.next &&
      upcoming.frame-now<=Math.max(upcoming.preroll,capacity)+latency){
    // Die ursprüngliche 48-kHz-Quellposition ist genauer als eine Rückrundung.
    if(upcoming.source!==frameAtRate(plan.offset,MOCK_RATE,rate))
      throw new Error("Loop-Quellposition stimmt nicht überein");
    plan.next=renderGeneration(upcoming.epoch,upcoming.frame,plan.offset,plan.length,rate);
  }
  if(current.output<now && current.output<current.end){
    const absolute=frameAtRate(current.source0,MOCK_RATE,rate)+now-current.frame;
    current.source=Math.min(plan.length,Math.max(current.source,frameAtRate(absolute,rate,MOCK_RATE)));
    while(current.source<plan.length && deviceFrame(current,current.source,rate)<now)current.source++;
    current.output=deviceFrame(current,current.source,rate);
  }
  for(let i=0;i<6 && active();i++){
    const next=plan.next;
    const g=current.output<Math.min(current.end,now+lead)?current:
      next && next.output<next.end && (next.seq===0 || next.output<now+lead)?next:null;
    if(!g)break;
    const remaining=plan.length-g.source;
    let n=Math.min(2048,remaining);
    if(remaining>2048 && remaining-2048<256)n=remaining-256;
    if(n<256)break;
    const payload={epoch:session.epoch,audio_epoch:g.audioEpoch,seq:g.seq,
      source_frame:g.source,start_frame:g.wireFrame+g.source-g.source0,nframes:n};
    if(g.seek && g.seq===0)payload.seek=true;
    core.noteRenderRequest?.(g.audioEpoch,g.seq);
    try{await render(session,payload);}
    catch(e){
      core.forgetRenderRequest?.(g.audioEpoch,g.seq);
      if(e.status!==503 && e.error!=="stale_epoch")throw e;
      break;
    }
    if(!active())return;
    g.seq++;g.source+=n;g.output=deviceFrame(g,g.source,rate);
  }
}

// Ein gemeinsamer AudioContext, keine PCM-Übertragung über JSON. Der Client
// meldet lediglich begrenzte Quell-/Master-Frame-Aufträge; Wet kommt per Sidecar.
export function createAudioSessionController(api, selection, {openCore=()=>AudioCore.open([0]),
    onStatus=()=>{},timerHost=globalThis}={}) {
  let session=null, core=null, asset=null, buffer=null, grid=null, recorder=null;
  let tail=Promise.resolve(), closed=false, generation=0, timer=null, pumpTask=null;
  let plan=null, source=0, mix=0, bypass=false, fallback=false, fault=null, seekPending=false;
  let recorded=[], timeline=[], lastExport=null, historyFull=false;
  const enqueue=fn=>{
    const result=tail.then(fn);
    tail=result.catch(()=>{});
    return result;
  };
  const inform=()=>onStatus();
  const isCurrent=current=>!closed && current===generation;
  const cancelled=Symbol("Sitzung gestoppt");
  const stopPump=()=>{
    plan=null;
    if(timer!==null){timerHost.clearInterval(timer);timer=null;}
  };
  const silence=()=>{
    stopPump();
    if(core)core.param(1,{mix:0,bypass:true,gain:0});
  };
  const stopRecorder=async()=>{
    if(!recorder)return;
    const old=recorder;recorder=null;
    try{const result=await timed(old.stop(),5000);if(result.error)fault=new Error(result.error);}
    catch(e){old.fail(e.message);fault=e;}
    inform();
  };
  async function cleanup(){
    stopPump();
    // Ein bereits gesendeter Renderauftrag ist durch den HTTP-Timeout begrenzt.
    // Vor dem Zerstören der Ressourcen seine Pumpe vollständig abwickeln.
    await pumpTask;
    await stopRecorder();
    const c=core;core=null;
    try{if(c)await c.destroy();}
    finally{
      const old=session;session=null;
      if(old)await api.close(old);
      asset=null;buffer=null;grid=null;source=0;seekPending=false;fallback=false;recorded=[];timeline=[];lastExport=null;historyFull=false;
    }
  }
  async function initialize(current){
    if(session)return;
    const check=()=>{if(!isCurrent(current))throw cancelled;};
    // openCore wird vor dem ersten HTTP-Await aus der Nutzeraktion ausgelöst.
    core=await openCore();
    check();
    // Gleichratige AudioCore-Adapter benötigen keine zusätzliche Konfiguration.
    if(typeof core.configureSourceRate==="function")core.configureSourceRate(MOCK_RATE);
    else if(core.rate!==MOCK_RATE)throw new Error("PCM-Ratenadapter fehlt");
    const selected=selection();
    asset=selected.stem?await api.cachedStem(selected.path,selected.model,selected.stem):
      selected.path==="fixture"?await api.asset(MOCK_ASSET):await api.resolve(selected.path);
    check();
    session=await api.create("mock",MOCK_RATE);
    check();
    session=await api.command(session,"load",{asset_id:asset.id});
    check();
    const end=Date.now()+20000;
    while(session.state==="loading" && Date.now()<end && isCurrent(current)){
      await wait(50);check();session=await api.session(session);
    }
    check();
    if(session.state!=="ready")throw new Error("Mock-Sitzung nicht bereit");
    const raw=await api.dry(session);check();
    buffer=decodeDry(core,raw,asset);
    try{grid=createBeatGrid(await api.beatgrid(asset.id),asset.sample_rate);}catch{grid=null;}
    check();
    try{
      const transport=await api.transport(session);
      check();
      const ws=core.connect("ws://127.0.0.1:"+transport.port+"/pcm",transport.token);
      await timed(new Promise((resolve,reject)=>{
        ws.addEventListener("open",resolve,{once:true});
        ws.addEventListener("error",reject,{once:true});
        ws.addEventListener("close",reject,{once:true});
      }),4000);
      check();
      ws.addEventListener("close",()=>{if(isCurrent(current)){fallback=true;core?.param(1,{mix:0});inform();}});
    }catch(e){check();fallback=true;core.param(1,{mix:0});}
    check();
    timer=timerHost.setInterval(startPump,20);
  }
  function begin(offset,seek=seekPending){
    if(!core||!buffer)return;
    if(offset>=asset.nframes)offset=0;
    source=offset;
    const frame=core.frame()+Math.round(core.rate*.22);
    const deviceOffset=frameAtRate(offset,MOCK_RATE,core.rate);
    const loop=asset.id===MOCK_ASSET?buffer.length-deviceOffset:0;
    const state=core.play([buffer],{source:deviceOffset,frame,loopLength:loop,expectedSeek:seek,wireSource:offset});
    seekPending=false;
    plan=makeRenderPlan(state,offset,asset.nframes,loop,seek,core.rate);
    core.param(1,{mix:fallback?0:mix,bypass,gain:1});
    startPump();
  }
  function startPump(){
    if(pumpTask || closed || timer===null)return;
    const current=generation, active=plan;
    pumpTask=pump(current,active).catch(e=>{
      if(isCurrent(current) && plan===active){
        fault=e;fallback=true;core?.param(1,{mix:0});inform();
      }
    }).finally(()=>{pumpTask=null;});
  }
  async function pump(current,active){
    if(!isCurrent(current))return;
    if(recorder && core?.context.state==="suspended")recorder.fail("AudioContext angehalten");
    if(!active || !core || !session || session.state!=="playing" || fallback)return;
    if(!active.loop && core.frame()>=active.current.end){
      plan=null;source=0;
      core.pause();
      // Der automatische Pause-Befehl darf nach Panic keinen neuen Befehl starten.
      void enqueue(async()=>{
        if(!isCurrent(current))return;
        if(session?.state==="playing")session=await api.command(session,"pause");
        if(isCurrent(current))inform();
      }).catch(e=>{if(isCurrent(current)){fault=e;inform();}});
      return;
    }
    await fillRenderPlan(active,core,session,(s,payload)=>api.render(s,payload),
      ()=>isCurrent(current) && plan===active && !!core && !!session && !fallback);
  }
  async function command(current,name,args={}){
    if(closed||current!==generation)throw cancelled;
    const before=session;
    session=await api.command(session,name,args);
    // Die HTTP-Antwort bleibt für Close erhalten, darf nach Panic aber
    // weder eine lokale Wiedergabe starten noch weitere Befehle auslösen.
    if(closed||current!==generation)throw cancelled;
    if(timeline.length<4096)timeline.push({frame:Math.max(timeline.at(-1)?.frame??0,core.frame()),command:{command:name,args:{...args},epoch:before.epoch,seq:before.seq===null?0:before.seq+1}});
    else historyFull=true;
    if(name==="play")begin(source);
    else if(name==="pause"){
      plan=null;
      if(core.status)source=Math.min(asset.nframes,frameAtRate(core.status.source,core.rate,MOCK_RATE));
      core.pause();
    }else if(name==="seek"){
      source=args.source_frame;plan=null;seekPending=true;
      if(before.state==="playing")begin(source);
    }else if(name==="bypass"){
      bypass=args.enabled;core.param(1,{bypass,mix:fallback?0:mix});
    }
    return session;
  }
  return {
    get state(){return session?.state||"created";},
    get detail(){return {fallback,grid,recording:!!recorder,recorded:recorded.length,lastExport,fault,underruns:core?.status?.streams?.[0]?.underruns};},
    run(fn){
      const current=generation;
      return enqueue(async()=>{
        if(closed||current!==generation)return;
        try{
          await initialize(current);
          if(closed||current!==generation)return;
          await fn((name,args)=>command(current,name,args),()=>session.state);
        }catch(e){
          if(e===cancelled||closed||current!==generation)return;
          fault=e;silence();await cleanup().catch(()=>{});throw e;
        }
      });
    },
    mix(value){mix=value;core?.param(1,{mix:fallback?0:mix,bypass});},
    silence,
    record(){
      const currentGeneration=generation;
      return enqueue(async()=>{
        if(closed||currentGeneration!==generation)return;
        if(recorder){await stopRecorder();return;}
        if(!session||!core||session.state!=="playing")throw new Error("Zuerst Testaudio abspielen");
        const current=session;
        const record=await api.record(current,"mock",core.rate);
        try{
          if(closed||currentGeneration!==generation){
            await api.recordClose(current,record.id);
            return;
          }
          recorder=await Recorder.attach(core,
            async(start,bytes)=>(await api.recordBlock(current,record.id,start,bytes)).next_frame,
            async()=>{const result=await api.recordClose(current,record.id);recorded.push(...result.assets.map(item=>item.id));});
          if(closed||currentGeneration!==generation){await stopRecorder();return;}
          recorder.start();
        }catch(e){await api.recordClose(current,record.id).catch(()=>{});throw e;}
        inform();
      });
    },
    export(preset){
      const current=generation;
      return enqueue(async()=>{
        if(closed||current!==generation)return;
        if(!session||!asset||!core)throw new Error("Zuerst eine Quelle laden");
        if(recorder)throw new Error("Zuerst Aufnahme stoppen");
        if(historyFull)throw new Error("Befehlsverlauf zu lang; neue Sitzung beginnen");
        const info=await api.exportSource(session);
        if(info.asset_id!==asset.id)throw new Error("Quelle gewechselt");
        const data=sessionExport(info,core.rate,preset,recorded,timeline);
        lastExport=(await api.exportSession(session,data)).id;
        inform();return lastExport;
      });
    },
    reset(){
      generation++;silence();
      return enqueue(cleanup);
    },
    destroy(){
      closed=true;generation++;silence();
      return enqueue(cleanup);
    },
  };
}

export function catalogEntries(data) {
  const entries=[];
  for(const artist of data?.artists || []) for(const release of artist.releases || [])
    for(const song of release.songs || []) for(const file of song.dateien || [])
      if(typeof file.pfad==="string") entries.push({path:file.pfad,label:artist.slug+" · "+song.titel+(file.fassung?" ("+file.fassung+")":"")});
  return entries;
}

// Jede Mount-Generation hat genau einen Satz Listener und höchstens einen Poll-Timer.
// WP05 erstellt weder AudioContext noch Audioelemente und startet keine Worker.
export function createLabShell({remote=createRtApi(), mockFactory=null,
  catalog=catalogApi, timerHost=globalThis, keyboard=globalThis.window, storage,
  onProfile=()=>{}}={}) {
  let dispose=null;
  function mount(root) {
    if(dispose) return;
    const resources=createResources(timerHost), abort=new AbortController();
    let active=true, caps=null, gpu=null, mock=false, client=remote, controller=null, error=null,
      entries=[], stemGeneration=0, polling=false, busy=false, preset={...DEFAULT_PRESET}, muted=false, slot="A";
    let profile=null, profileBusy=false, profileEpoch=0, profileError="", diagnostics=null;
    const status=h("p",{role:"status","aria-live":"polite"},"Fähigkeiten werden geladen");
    const catalogStatus=h("p",{role:"status"},"Bibliothek wird geladen");
    const gpuInfo=h("p",{},"GPU-Telemetrie wird geladen");
    const capsInfo=h("ul",{});
    const latency=h("p",{},"Latenz: unbekannt");
    const transport=h("p",{role:"status"},"Transport: bereit (Testmodus)");
    const beatInfo=h("p",{},"BeatGrid: unsicher");
    const select=(label,options=[])=>h("select",{"aria-label":label},options.map(([v,t])=>h("option",{value:v},t)));
    const song=select("Song",[["","Song auswählen"]]);
    const search=h("input",{type:"search","aria-label":"Katalog durchsuchen",placeholder:"Titel, Künstler, Dateiname"});
    const model=select("Stem-Modell",[["htdemucs","Demucs · 4 Stems"],["htdemucs_6s","Demucs · 6 Stems"]]);
    const stem=select("Stem",[["","Original"]]);
    const capability=select("Fähigkeit");
    const profileSelect=select("GPU-Profil", [["","Profil nicht geladen"],...GPU_PROFILES.map(name=>[name,name])]);
    const profileInfo=h("p",{role:"status"},"GPU-Profil wird geladen");
    const btn=t=>h("button",{type:"button"},t);
    const play=btn("Abspielen / Pause"), stop=btn("Stop"), panic=btn("Panic · stumm / Dry"),
      bypass=btn("Bypass"), ab=btn("A/B: A"), save=btn("Preset speichern"), restore=btn("Preset laden"), record=btn("Aufnahme starten"), exportButton=btn("Sitzungsdatei exportieren");
    const exportInfo=h("p",{role:"status"},"Aufnahmen werden getrennt vom Musikordner gespeichert.");
    const pad=btn("Mock-Pad · Gain ½");
    const range=(label,min,max,value,step=1)=>h("input",{type:"range","aria-label":label,min,max,value:String(value),step});
    const wet=range("Dry/Wet",0,100,0), gain=range("Mock Gain",0,2,1,0.01);
    const wetValue=h("output",{},"0 %"), gainValue=h("output",{},"1");
    const seek=h("input",{type:"number",min:0,max:Number.MAX_SAFE_INTEGER,step:1,value:"0","aria-label":"Quellframe"});
    const seekButton=btn("Seek");
    const buttons=[play,stop,panic,bypass,ab,save,restore,wet,gain,seek,seekButton];
    const label=(text,el)=>h("label",{},text,el);
    const refresh=btn("Status erneut laden");
    const hookHost=h("div",{"class":"rt-grid"}), advancedHost=h("div",{});
    const previewButton=btn("Offline-Mix vorhören"), previewStatus=h("p",{role:"status"},"Kein Offline-Mix");
    let unmountAdvanced=null, operationEpoch=0, advancedClosing=null;
    const hookCards=mountHookTools(hookHost,{document:root.ownerDocument||globalThis.document});
    const preview=createOfflinePreview({beforePlay:async()=>{await controller?.reset();},onStatus:()=>paint()});
    const stopPreview=(clear=false)=>preview.stop(clear).catch(e=>{if(active){error=e;paint();}});
    const clearAdvanced=()=>{
      operationEpoch++;
      const old=unmountAdvanced;unmountAdvanced=null;
      const previous=advancedClosing;
      // Sperre setzen, bevor stopPreview synchron paint auslöst.
      advancedClosing=Promise.resolve();
      const closing=old?.();
      advancedHost.replaceChildren();
      const pending=Promise.all([previous,Promise.resolve(closing),stopPreview(true)]);
      advancedClosing=pending;
      const finished=()=>{if(advancedClosing===pending){advancedClosing=null;paint();}};
      pending.then(finished,finished);
      return pending;
    };
    const canSeparate=name=>active&&!!caps&&!error&&!!song.value&&song.value!=="fixture"&&
      (name==="htdemucs"||(diagnostics?.separation?.available&&diagnostics.separation.interpreter_present&&diagnostics.separation.gate_report_present&&caps.capabilities.some(c=>c.id==="separation"&&c.available)));
    function paintAdvanced(){
      if(advancedClosing)return;
      if(!caps||error||!song.value||song.value==="fixture"){
        if(unmountAdvanced)void clearAdvanced().catch(()=>{});
        advancedHost.textContent="Advanced Stem Studio · Offline – Song und RT-Dienst erforderlich";
      }else if(!unmountAdvanced){
        advancedHost.replaceChildren();
        unmountAdvanced=mountSeparationJobs(advancedHost,{selectedPath:()=>song.value,canStart:canSeparate,
          onMix:(samples,rate)=>preview.prepare(samples,rate).catch(e=>{if(active){error=e;paint();}})});
      }
      unmountAdvanced?.paint?.();
    }
    root.replaceChildren(h("section",{class:"rt-shell","aria-label":"RTX Neural Lab"},
      h("h2",{},"RTX Neural Lab"),status,
      h("p",{},"Testmodus: CPU-Mock mit Audio-Ausgabe, keine KI und keine Echtzeitfreigabe. 48-kHz-PCM16-WAV oder synthetisches Testsignal; Vorhandene Demucs-Cache-Stems einzeln im Mock; Offline-Trennung getrennt vom Original."),
      h("div",{class:"rt-grid"},h("section",{},h("h3",{},"Bibliothek"),catalogStatus,label("Suche",search),label("Song",song),
        label("Stem-Modell (vorhandener Cache)",model),label("Stem",stem)),
        h("section",{},h("h3",{},"Fähigkeiten"),label("Fähigkeit",capability),capsInfo,latency,
          label("GPU-Profil",profileSelect),profileInfo,refresh,
          h("p",{},"Nicht freigegebene Funktionen sind unten gesperrt."))),
      h("section",{},h("h3",{},"GPU & Warteschlange"),gpuInfo),
      h("section",{},h("h3",{},"Transport & Mischung"),transport,beatInfo,h("div",{class:"rt-actions"},play,stop,panic,bypass,ab,save,restore,record,exportButton,pad),exportInfo,
        label("Quellframe (48 kHz im Mock)",seek),seekButton,label("Dry/Wet",wet),wetValue,label("Gain (Mock)",gain),gainValue,
        h("p",{},"Tastatur: Leertaste = Transport, Esc = Panic, B = Bypass, A = A/B. MIDI-Zuordnung vorbereitet; kein Gerät verbunden.")),
      h("section",{},advancedHost,previewButton,previewStatus),hookHost,
      h("details",{},h("summary",{},"Installationshilfe"),h("p",{},
        "SIRENS_RT_ENABLED=1 und SIRENS_RT_MOCK=1 in der lokalen Konfiguration setzen und Dienst neu starten. Modelle und GPU-Worker erst nach Freigabe separat installieren. Kein automatischer Download."))));
    function selected() {return caps?.capabilities.find(c=>c.id===capability.value);}
    function paint() {
      if(!active)return;
      const state=deriveState({capabilities:caps,gpu,mock,songs:entries.length || (song.value==="fixture"?1:0),error,capabilityId:capability.value});
      status.textContent=state.text || "Bereit";
      gpuInfo.textContent=gpuText(gpu);
      profileSelect.value=profile??"";
      profileSelect.disabled=!profile||profileBusy||!!error;
      profileInfo.textContent=profileError || (profile===null?"GPU-Profil nicht verfügbar":
        "Profil: "+profile+" · GPU-Worker-Limit; Mock bleibt CPU. Keine Modellfreigabe durch Profilwechsel.");
      latency.textContent=latencyText(selected());
      const enabled=state.enabled && Boolean(song.value) && !busy && !!controller;
      for(const b of buttons)b.disabled=!enabled;
      // Panic darf während eines ausstehenden Befehls angefordert werden.
      panic.disabled=!controller&&!unmountAdvanced&&!preview.ready;
      stop.disabled=panic.disabled;
      song.disabled=!entries.length && !mock;
      model.disabled=!song.value || song.value==="fixture";
      stem.disabled=model.disabled || stem.options.length<=1;
      capability.disabled=!caps?.capabilities.length;
      play.textContent=controller?.state==="playing"?"Pause":"Abspielen (Test)";
      bypass.setAttribute("aria-pressed",String(preset.bypass));
      wet.value=String(preset.wet);wetValue.textContent=preset.wet+" %";
      gain.value=String(preset.gain);gainValue.textContent=String(preset.gain);
      ab.textContent="A/B: "+slot;
      const detail=controller?.detail;
      record.disabled=!enabled||!detail||controller.state!=="playing";
      record.textContent=detail?.recording?"Aufnahme stoppen":"Aufnahme starten";
      pad.disabled=!enabled||controller?.state!=="playing";
      exportButton.disabled=!enabled||!controller?.export||!!detail?.recording||!["ready","playing","paused"].includes(controller?.state);
      exportInfo.textContent=(detail?.recorded??0)+" Aufnahmesegmente · "+(detail?.lastExport?"Sitzungsdatei gespeichert: "+detail.lastExport:"noch kein Sitzungsexport")+" · kein vollständiges Replay";
      beatInfo.textContent=detail?.grid?"BeatGrid vorhanden (Quantisierung noch gesperrt)":"BeatGrid: unsicher / nicht verfügbar";
      hookCards.paint(caps?.capabilities,error,diagnostics);
      paintAdvanced();
      panic.disabled=!controller&&!unmountAdvanced&&!preview.ready&&!advancedClosing;
      stop.disabled=panic.disabled;
      previewButton.disabled=busy||!preview.ready||!!error;
      previewButton.textContent=preview.playing?"Offline-Vorschau stoppen":"Offline-Mix vorhören";
      previewStatus.textContent=preview.playing?"Offline-Vorschau läuft":preview.ready?"Offline-Mix vorbereitet":"Kein Offline-Mix";
      transport.textContent="Transport: "+(muted?"Panic / stumm":controller?.state || "bereit")+(detail?.fallback?" · Dry-Rückfall":"")+" · nicht gemessen"+(detail?.underruns===undefined?"":" · Underrun-Frames: "+detail.underruns)+(detail?.fault?" · "+detail.fault.message:"");
    }
    function fillSongs() {
      const previous=song.value;
      song.replaceChildren(h("option",{value:""},"Song auswählen"));
      if(mock)song.append(h("option",{value:"fixture"},"Synthetisches Testsignal (Mock)"));
      for(const e of filterCatalog(entries,search.value,previous))song.append(h("option",{value:e.path},e.label));
      if([...song.options].some(o=>o.value===previous))song.value=previous;
      paint();
    }
    async function loadCatalog() {
      try {
        const data=await catalog.katalog();
        if(!active)return;
        entries=catalogEntries(data);
        catalogStatus.textContent=entries.length?entries.length+" Katalogdateien":"Leere Bibliothek – keine Songs im Katalog";
        fillSongs();
      }catch(e){if(active){catalogStatus.textContent="Katalog nicht verfügbar";paint();}}
    }
    async function loadStems() {
      const generation=++stemGeneration;
      stem.replaceChildren(h("option",{value:""},"Original"));
      if(!song.value || song.value==="fixture"){paint();return;}
      try {
        const data=await catalog.stemStatus(song.value,model.value);
        if(!active || generation!==stemGeneration)return;
        for(const name of data?.zustand==="bereit" && Array.isArray(data?.stems)?data.stems:[])
          if(typeof name==="string")stem.append(h("option",{value:name},name));
      }catch{if(active && generation===stemGeneration)catalogStatus.textContent="Stem-Cache nicht verfügbar; Original wählbar.";}
      paint();
    }
    function acceptProfile(value) {
      if(!GPU_PROFILES.includes(value?.profile))throw new Error("Ungültiges GPU-Profil");
      profile=value.profile;profileError="";onProfile(profile);
    }
    async function refreshProfile() {
      if(!remote.profile||profileBusy)return;
      const epoch=profileEpoch;
      try{
        const value=await remote.profile(abort.signal);
        if(active&&epoch===profileEpoch&&!profileBusy)acceptProfile(value);
      }catch(e){
        if(active&&epoch===profileEpoch&&!profileBusy)profileError="GPU-Profil nicht abrufbar: "+e.message;
      }
    }
    async function changeProfile() {
      if(!active||!profile||profileBusy||!remote.setProfile)return;
      const next=profileSelect.value;
      if(!GPU_PROFILES.includes(next))return;
      profileBusy=true;profileEpoch++;paint();
      try{
        const value=await remote.setProfile(next,abort.signal);
        if(active)acceptProfile(value);
      }catch(e){
        if(active)profileError="Profilwechsel abgelehnt: "+e.message;
      }finally{profileBusy=false;paint();}
    }
    async function refreshStatus() {
      if(!active || polling)return;
      polling=true;
      try{
        let next;
        try { next=await remote.capabilities(abort.signal); } catch(e) { caps=null; throw e; }
        if(!active)return;
        const nextMock=next.capabilities.some(c=>c.mock && c.available && c.id==="mock");
        if(nextMock!==mock){
          if(controller)await controller.destroy();
          if(!active)return;
          mock=nextMock;client=mock&&mockFactory?mockFactory():remote;
          controller=mock?(mockFactory?createSessionController(client):createAudioSessionController(client,
            ()=>({path:song.value,stem:stem.value,model:model.value}),{onStatus:paint})):null;
          fillSongs();
        }
        caps=next;error=null;
        try{diagnostics=remote.hookStatus?(await remote.hookStatus(abort.signal)).models:null;}
        catch{diagnostics=null;}
        if(!active)return;
        const previous=capability.value;
        capability.replaceChildren(...caps.capabilities.map(c=>h("option",{value:c.id,disabled:!c.available},c.id+" · "+modeLabel(c.mode)+(c.mock?" · Testmodus":"")+(c.available?"":" · gesperrt"))));
        if(caps.capabilities.some(c=>c.id===previous))capability.value=previous;
        else if(mock)capability.value="mock";
        capsInfo.replaceChildren(...caps.capabilities.map(c=>h("li",{},c.id+": "+modeLabel(c.mode)+" · "+(c.available?"gemeldet verfügbar":"nicht freigegeben")+(c.mock?" · Testmodus":""))));
        const nextGpu=await client.gpu(abort.signal);
        if(active)gpu=nextGpu;
        await refreshProfile();
      }catch(e){
        if(active){
          // 503 beim ersten GET ist der ausgeschaltete oder nicht verfügbare Dienst.
          error=e;gpu=null;diagnostics=null;
          if(controller){await controller.destroy().catch(()=>{});controller=null;}
          mock=false;client=remote;
          if(!caps){capsInfo.replaceChildren();capability.replaceChildren();}
          fillSongs();
        }
      }finally{polling=false;paint();}
    }
    const run=async fn=>{
      if(!active || !controller || busy || !deriveState({capabilities:caps,gpu,mock,songs:entries.length || (song.value==="fixture"?1:0),error,capabilityId:capability.value}).enabled || !song.value)return;
      busy=true;paint();
      const current=operationEpoch;
      try{await stopPreview();if(active&&current===operationEpoch)await controller?.run(fn);}
      catch(e){if(active)error=e;}
      finally{busy=false;paint();}
    };
    const apply=async command=>{
      controller?.mix?.(preset.wet/100);
      await command("set_param",{name:"gain",value:muted?0:preset.gain});
      await command("bypass",{enabled:preset.bypass || preset.wet===0});
    };
    const doPanic=()=>{
      controller?.silence?.();muted=true;preset={...preset,wet:0,bypass:true};
      void clearAdvanced().catch(e=>{if(active){error=e;paint();}});paint();
      // Close stoppt die Sitzung auch dann, wenn gerade ein Befehl aussteht.
      controller?.reset().then(()=>{muted=true;preset={...preset,wet:0,bypass:true};paint();}).catch(e=>{if(active){error=e;paint();}});
    };
    const getStorage=()=>{try{return storage ?? globalThis.localStorage;}catch{return null;}};
    const actions={
      transport:()=>run(async(command,state)=>{if(state()==="playing")await command("pause");else{muted=false;await apply(command);await command("play");}}),
      panic:doPanic,
      bypass:()=>{preset.bypass=!preset.bypass;run(apply);paint();},
      ab:()=>{const next=slot==="A"?"B":"A";const old=readPresets(getStorage());savePreset(getStorage(),slot,preset);
        slot=next;preset=normalizePreset(old[next]);run(apply);paint();},
    };
    const on=(el,event,fn)=>resources.listen(el,event,fn);
    on(search,"input",fillSongs);
    on(pad,"click",()=>{if(controller?.state!=="playing")return;preset={...preset,gain:0.5,wet:100,bypass:false};run(apply);paint();});
    on(exportButton,"click",()=>{controller?.export?.(preset).then(paint).catch(e=>{if(active){exportInfo.textContent=e.message;}});});
    on(record,"click",()=>{controller?.record?.().then(paint).catch(e=>{if(active){error=e;paint();}});});
    on(play,"click",actions.transport);on(panic,"click",actions.panic);on(bypass,"click",actions.bypass);on(ab,"click",actions.ab);
    on(previewButton,"click",()=>{
      if(!active||busy||previewButton.disabled)return;
      if(preview.playing){void stopPreview();return;}
      busy=true;paint();preview.play().catch(e=>{if(active){error=e;}}).finally(()=>{busy=false;paint();});
    });
    on(stop,"click",()=>{void clearAdvanced().catch(()=>{});controller?.reset().then(()=>{muted=false;paint();}).catch(e=>{if(active){error=e;paint();}});});
    on(seekButton,"click",()=>{const frame=Number(seek.value);if(Number.isSafeInteger(frame)&&frame>=0)run(cmd=>cmd("seek",{source_frame:frame}));});
    on(wet,"input",()=>{preset.wet=Number(wet.value);paint();});on(wet,"change",()=>run(apply));
    on(gain,"input",()=>{preset.gain=Number(gain.value);paint();});on(gain,"change",()=>run(apply));
    on(save,"click",()=>{if(!savePreset(getStorage(),slot,preset))status.textContent="Preset konnte nicht gespeichert werden.";});
    on(restore,"click",()=>{preset=normalizePreset(readPresets(getStorage())[slot]);run(apply);paint();});
    on(song,"change",()=>{void clearAdvanced().catch(()=>{});controller?.reset().catch(e=>{if(active){error=e;paint();}});loadStems();paint();});
    on(model,"change",()=>{void clearAdvanced().catch(()=>{});controller?.reset().catch(e=>{if(active){error=e;paint();}});loadStems();});on(stem,"change",()=>{void clearAdvanced().catch(()=>{});controller?.reset().catch(e=>{if(active){error=e;paint();}});});
    on(capability,"change",()=>{void clearAdvanced().catch(()=>{});controller?.reset().catch(()=>{});paint();});on(refresh,"click",refreshStatus);
    on(profileSelect,"change",changeProfile);
    if(keyboard)on(keyboard,"keydown",event=>{
      const action=keyAction(event);
      const target={transport:play,panic,bypass,ab}[action];
      if(target && !target.disabled){event.preventDefault();actions[action]();}
    });
    resources.interval(refreshStatus,5000);
    paint();loadCatalog();refreshStatus();
    dispose=()=>{
      active=false;abort.abort();resources.clear();
      const previewClosing=clearAdvanced();hookCards.destroy();root.replaceChildren();
      const closing=controller?.destroy();
      controller=null;dispose=null;
      return Promise.allSettled([previewClosing,closing]);
    };
  }
  function destroy(){return dispose?.();}
  // Pause entfernt sämtliche Ressourcen; nächstes Mount startet eine frische Generation.
  return {mount,pause:destroy,destroy};
}
