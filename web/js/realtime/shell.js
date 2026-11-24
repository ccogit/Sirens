import { h } from "../dom.js";
import { api as catalogApi } from "../api.js";
import { createRtApi, MOCK_ASSET } from "./api.js";
import { deriveState, modeLabel } from "./capabilities.js";
import { gpuText, latencyText } from "./gpu_panel.js";
import { createResources, keyAction, DEFAULT_PRESET, readPresets, savePreset, normalizePreset } from "./controls.js";

// Der Mock akzeptiert ausschließlich sein synthetisches Asset. Keine Katalogpfade als RT-IDs.
export function createSessionController(api) {
  let session=null, tail=Promise.resolve(), closed=false;
  const enqueue = fn => {
    const result=tail.then(fn);
    tail=result.catch(()=>{});
    return result;
  };
  const command = async (name,args={}) => {
    session=await api.command(session,name,args);
    return session;
  };
  return {
    get state() { return session?.state || "created"; },
    run(fn) { return enqueue(async()=>{
      if (closed) return;
      if (!session) {
        session=await api.create("mock");
        await command("load",{asset_id:MOCK_ASSET});
      }
      if (!closed) return fn(command,()=>session.state);
    }); },
    reset() { return enqueue(async()=>{ if(session) { await api.close(session); session=null; } }); },
    destroy() {
      closed=true;
      return enqueue(async()=>{ if(session) { await api.close(session); session=null; } });
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
export function createLabShell({remote=createRtApi(), mockFactory=()=>createRtApi({mock:true}),
  catalog=catalogApi, timerHost=globalThis, keyboard=globalThis.window, storage}={}) {
  let dispose=null;
  function mount(root) {
    if(dispose) return;
    const resources=createResources(timerHost), abort=new AbortController();
    let active=true, caps=null, gpu=null, mock=false, client=remote, controller=null, error=null,
      entries=[], stemGeneration=0, polling=false, busy=false, preset={...DEFAULT_PRESET}, muted=false, slot="A";
    const status=h("p",{role:"status","aria-live":"polite"},"Fähigkeiten werden geladen");
    const catalogStatus=h("p",{role:"status"},"Bibliothek wird geladen");
    const gpuInfo=h("p",{},"GPU-Telemetrie wird geladen");
    const capsInfo=h("ul",{});
    const latency=h("p",{},"Latenz: unbekannt");
    const transport=h("p",{role:"status"},"Transport: bereit (kein Ton)");
    const select=(label,options=[])=>h("select",{"aria-label":label},options.map(([v,t])=>h("option",{value:v},t)));
    const song=select("Song",[["","Song auswählen"]]);
    const model=select("Stem-Modell",[["htdemucs","Demucs · 4 Stems"],["htdemucs_6s","Demucs · 6 Stems"]]);
    const stem=select("Stem",[["","Original"]]);
    const capability=select("Fähigkeit");
    const btn=t=>h("button",{type:"button"},t);
    const play=btn("Abspielen / Pause"), stop=btn("Stop"), panic=btn("Panic · stumm / Dry"),
      bypass=btn("Bypass"), ab=btn("A/B: A"), save=btn("Preset speichern"), restore=btn("Preset laden");
    const range=(label,min,max,value,step=1)=>h("input",{type:"range","aria-label":label,min,max,value:String(value),step});
    const wet=range("Dry/Wet",0,100,0), gain=range("Mock Gain",0,2,1,0.01);
    const wetValue=h("output",{},"0 %"), gainValue=h("output",{},"1");
    const seek=h("input",{type:"number",min:0,max:Number.MAX_SAFE_INTEGER,step:1,value:"0","aria-label":"Quellframe"});
    const seekButton=btn("Seek");
    const buttons=[play,stop,panic,bypass,ab,save,restore,wet,gain,seek,seekButton];
    const label=(text,el)=>h("label",{},text,el);
    const refresh=btn("Status erneut laden");
    root.replaceChildren(h("section",{class:"rt-shell","aria-label":"RTX Neural Lab"},
      h("h2",{},"RTX Neural Lab"),status,
      h("p",{},"WP05: Steueroberfläche ohne Tonpfad. Testmodus verwendet nur synthetische Daten, auch bei Katalogauswahl."),
      h("div",{class:"rt-grid"},h("section",{},h("h3",{},"Bibliothek"),catalogStatus,label("Song",song),
        label("Stem-Modell (vorhandener Cache)",model),label("Stem",stem)),
        h("section",{},h("h3",{},"Fähigkeiten"),label("Fähigkeit",capability),capsInfo,latency,
          h("p",{},"Qualitätsprofil: Offline-Mock; weitere Profile erst nach Freigabe."),refresh)),
      h("section",{},h("h3",{},"GPU & Warteschlange"),gpuInfo),
      h("section",{},h("h3",{},"Transport & Mischung"),transport,h("div",{class:"rt-actions"},play,stop,panic,bypass,ab,save,restore),
        label("Quellframe (48 kHz im Mock)",seek),seekButton,label("Dry/Wet",wet),wetValue,label("Gain (Mock)",gain),gainValue,
        h("p",{},"Tastatur: Leertaste = Transport, Esc = Panic, B = Bypass, A = A/B. MIDI-Zuordnung vorbereitet; kein Gerät verbunden.")),
      h("details",{},h("summary",{},"Installationshilfe"),h("p",{},
        "SIRENS_RT_ENABLED=1 und SIRENS_RT_MOCK=1 in der lokalen Konfiguration setzen und Dienst neu starten. Modelle und GPU-Worker erst nach Freigabe separat installieren. Kein automatischer Download."))));
    function selected() {return caps?.capabilities.find(c=>c.id===capability.value);}
    function paint() {
      if(!active)return;
      const state=deriveState({capabilities:caps,gpu,mock,songs:entries.length || (song.value==="fixture"?1:0),error,capabilityId:capability.value});
      status.textContent=state.text || "Bereit";
      gpuInfo.textContent=gpuText(gpu);
      latency.textContent=latencyText(selected());
      const enabled=state.enabled && Boolean(song.value) && !busy && !!controller;
      for(const b of buttons)b.disabled=!enabled;
      // Panic darf während eines ausstehenden Befehls angefordert werden.
      panic.disabled=!controller || !state.enabled;
      song.disabled=!entries.length && !mock;
      model.disabled=!song.value || song.value==="fixture";
      stem.disabled=model.disabled || stem.options.length<=1;
      capability.disabled=!caps?.capabilities.length;
      play.textContent=controller?.state==="playing"?"Pause":"Abspielen (Test)";
      bypass.setAttribute("aria-pressed",String(preset.bypass));
      wet.value=String(preset.wet);wetValue.textContent=preset.wet+" %";
      gain.value=String(preset.gain);gainValue.textContent=String(preset.gain);
      ab.textContent="A/B: "+slot;
      transport.textContent="Transport: "+(muted?"Panic / stumm":controller?.state || "bereit")+" (kein Ton)";
    }
    function fillSongs() {
      const previous=song.value;
      song.replaceChildren(h("option",{value:""},"Song auswählen"));
      if(mock)song.append(h("option",{value:"fixture"},"Synthetisches Testsignal (Mock)"));
      for(const e of entries)song.append(h("option",{value:e.path},e.label));
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
        for(const name of Array.isArray(data?.stems)?data.stems:[])
          if(typeof name==="string")stem.append(h("option",{value:name},name));
      }catch{if(active && generation===stemGeneration)catalogStatus.textContent="Stem-Cache nicht verfügbar; Original wählbar.";}
      paint();
    }
    async function refreshStatus() {
      if(!active || polling)return;
      polling=true;
      try{
        const next=await remote.capabilities(abort.signal);
        if(!active)return;
        const nextMock=next.capabilities.some(c=>c.mock && c.available && c.id==="mock");
        if(nextMock!==mock){
          if(controller)await controller.destroy();
          if(!active)return;
          mock=nextMock;client=mock?mockFactory():remote;controller=mock?createSessionController(client):null;
          fillSongs();
        }
        caps=next;error=null;
        const previous=capability.value;
        capability.replaceChildren(...caps.capabilities.map(c=>h("option",{value:c.id},c.id+" · "+modeLabel(c.mode)+(c.mock?" · Testmodus":"")+(c.available?"":" · gesperrt"))));
        if(caps.capabilities.some(c=>c.id===previous))capability.value=previous;
        else if(mock)capability.value="mock";
        capsInfo.replaceChildren(...caps.capabilities.map(c=>h("li",{},c.id+": "+modeLabel(c.mode)+" · "+(c.available?"gemeldet verfügbar":"nicht freigegeben")+(c.mock?" · Testmodus":""))));
        gpu=await client.gpu(abort.signal);
      }catch(e){
        if(active){
          // 503 beim ersten GET ist der ausgeschaltete oder nicht verfügbare Dienst.
          error=e;gpu=null;
          if(controller){await controller.destroy().catch(()=>{});controller=null;}
          mock=false;client=remote;
          caps=null;capsInfo.replaceChildren();capability.replaceChildren();fillSongs();
        }
      }finally{polling=false;paint();}
    }
    const run=async fn=>{
      if(!active || !controller || busy || !deriveState({capabilities:caps,gpu,mock,songs:entries.length || (song.value==="fixture"?1:0),error,capabilityId:capability.value}).enabled || !song.value)return;
      busy=true;paint();
      try{await controller.run(fn);}
      catch(e){if(active)error=e;}
      finally{busy=false;paint();}
    };
    const apply=async command=>{
      // Dry/Wet ist ein UI-Mischwert; WP06 bindet ihn an den Audio-Kern an.
      await command("set_param",{name:"gain",value:muted?0:preset.gain});
      await command("bypass",{enabled:preset.bypass || preset.wet===0});
    };
    const doPanic=()=>{
      if(!controller)return;
      muted=true;preset={...preset,wet:0,bypass:true};paint();
      // Close stoppt die Sitzung auch dann, wenn gerade ein Befehl aussteht.
      controller.reset().catch(e=>{if(active){error=e;paint();}});
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
    on(play,"click",actions.transport);on(panic,"click",actions.panic);on(bypass,"click",actions.bypass);on(ab,"click",actions.ab);
    on(stop,"click",()=>{controller?.reset().then(()=>{muted=false;paint();}).catch(e=>{if(active){error=e;paint();}});});
    on(seekButton,"click",()=>{const frame=Number(seek.value);if(Number.isSafeInteger(frame)&&frame>=0)run(cmd=>cmd("seek",{source_frame:frame}));});
    on(wet,"input",()=>{preset.wet=Number(wet.value);paint();});on(wet,"change",()=>run(apply));
    on(gain,"input",()=>{preset.gain=Number(gain.value);paint();});on(gain,"change",()=>run(apply));
    on(save,"click",()=>{if(!savePreset(getStorage(),slot,preset))status.textContent="Preset konnte nicht gespeichert werden.";});
    on(restore,"click",()=>{preset=normalizePreset(readPresets(getStorage())[slot]);run(apply);paint();});
    on(song,"change",()=>{controller?.reset().catch(e=>{if(active){error=e;paint();}});loadStems();paint();});
    on(model,"change",loadStems);on(stem,"change",()=>{controller?.reset().catch(e=>{if(active){error=e;paint();}});});
    on(capability,"change",paint);on(refresh,"click",refreshStatus);
    if(keyboard)on(keyboard,"keydown",event=>{
      const action=keyAction(event);
      const target={transport:play,panic,bypass,ab}[action];
      if(target && !target.disabled){event.preventDefault();actions[action]();}
    });
    resources.interval(refreshStatus,5000);
    paint();loadCatalog();refreshStatus();
    dispose=()=>{
      active=false;abort.abort();resources.clear();root.replaceChildren();
      const closing=controller?.destroy();
      controller=null;dispose=null;
      return closing?.catch(()=>{});
    };
  }
  function destroy(){return dispose?.();}
  // Pause entfernt sämtliche Ressourcen; nächstes Mount startet eine frische Generation.
  return {mount,pause:destroy,destroy};
}
