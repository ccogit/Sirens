// Bedienoberfläche des Auto-DJ: Kataloglisten, Zufallsset und hörbare Dramaturgie.
import { api } from "./api.js";
import { h } from "./dom.js";
import { katalogSongs, klassifizierung } from "./auto_logic.js";
import { AutoMixer } from "./auto_mix.js";
import { visualisieren } from "./live_visual.js";

function uhr(sekunden) {
  if (!Number.isFinite(sekunden)) return "0:00";
  const t=Math.floor(Math.max(0,sekunden));
  return Math.floor(t/60)+":"+String(t%60).padStart(2,"0");
}

function timeline(inhalt,info) {
  inhalt.replaceChildren();
  if(!info?.timeline?.length) return;
  const cues=info.cues_out||[];
  for(const eintrag of info.timeline) {
    const isCue=cues.some(c=>Math.abs(c.zeit-eintrag.zeit)<.6);
    const bar=h("span",{class:"auto-energy-bar"+(isCue?" auto-energy-cue":""),
      title:uhr(eintrag.zeit)+" · "+eintrag.phase+" · Energie "+Math.round(eintrag.energie*100)+"%"});
    bar.style.height=(9+eintrag.energie*85)+"%";
    inhalt.append(bar);
  }
}

export function autoDjAnsicht(isProducing=()=>false) {
  let beendet=false, katalogTimer=null, alle=[], selected=new Set(), aktuell=null, laufend=false;
  const stand=h("p",{class:"auto-status",role:"status"},"Katalog wird geladen …");
  const now=h("strong",{},"Noch kein Song gestartet");
  const meta=h("span",{},"Song-Analyse und Ein-/Ausstiegspunkte erscheinen hier.");
  const arc=h("div",{class:"auto-arc",role:"img","aria-label":"Analysierter Songverlauf mit Energie und möglichen Übergängen"});
  const neon=h("canvas",{class:"auto-canvas","aria-label":"Audioreaktiver GPU-Neontunnel"});
  const scope=h("canvas",{class:"auto-canvas",hidden:true});
  let stopVisual=null;
  const next=h("div",{class:"auto-next"},"Noch kein Übergang geplant.");
  const history=h("ol",{class:"auto-history"});
  const duration=h("output",{},"0:00 / 0:00");
  const position=h("div",{class:"auto-position"},h("span",{class:"auto-progress"}));
  const start=h("button",{type:"button",class:"lab-play"},"▶ Endlos-Set starten");
  const stop=h("button",{type:"button",class:"lab-stop",disabled:true},"■ Stopp");
  const nextBeat=h("button",{type:"button",class:"lab-stop",disabled:true},"⇥ Am nächsten Takt mixen");
  const mode=h("select",{"aria-label":"Songliste für den Auto-DJ"},
    h("option",{value:"favoriten"},"Meine Favoriten (+1 / +2)"),
    h("option",{value:"alle"},"Alle Songs aus dem Katalog"),
    h("option",{value:"auswahl"},"Nur manuell ausgewählte Songs"));
  const genre=h("select",{"aria-label":"Stichwort-Filter"},h("option",{value:""},"Alle Stil-Stichwörter"));
  const search=h("input",{type:"search",placeholder:"Künstler, Album oder Song suchen …","aria-label":"Songliste durchsuchen"});
  const list=h("div",{class:"auto-songlist",role:"group","aria-label":"Songs für das Set"});
  const count=h("span",{class:"auto-count"},"0 Songs");
  const bars=h("select",{"aria-label":"Länge der Überblendung in Takten"},
    ...[4,8,16].map(n=>h("option",{value:String(n),selected:n===8},n+" Takte")));
  const tolerance=h("select",{"aria-label":"Erlaubte Tempoanpassung"},
    h("option",{value:".10"},"±10 % – präzise"),
    h("option",{value:".19",selected:true},"±19 % – ausgewogen"),
    h("option",{value:".30"},"±30 % – experimentell"));
  const random=h("input",{type:"checkbox",checked:true,"aria-label":"Abwechslungsreiche Zufallsauswahl"});
  const toy=h("section",{class:"auto-dj"},
    h("header",{class:"auto-head"},
      h("div",{},
        h("p",{class:"lab-eyebrow"},"AUTO DJ · PHRASE-AWARE MUSIC DIRECTOR"),
        h("h2",{},"Ein Set, das sich selbst weiterspielt."),
        h("p",{},"Sirens sucht Übergänge nach Beat, 4-Takt-Phrasen, Breaks, Build-ups und Energieverlauf."))),
    h("section",{class:"auto-now"},
      neon,scope,
      h("div",{class:"auto-now-top"},
        h("span",{class:"auto-air"},"● ON AIR / AUTO MIX"),
        duration),
      now,meta,arc,position,
      h("div",{class:"auto-transport"},start,stop,nextBeat)),
    h("section",{class:"auto-director"},
      h("div",{},
        h("p",{class:"lab-eyebrow"},"DER NÄCHSTE ÜBERGANG"),
        h("h3",{},"DJ-Dramaturgie"),
        next),
      h("div",{},
        h("p",{class:"lab-eyebrow"},"SET-VERLAUF"),
        history)),
    h("section",{class:"auto-controls"},
      h("div",{class:"auto-controls-title"},h("h3",{},"Set zusammenstellen"),
        h("p",{},"Katalog, Favoriten oder deine persönliche Auswahl. Der nächste Song wird selbstständig gesucht.")),
      h("div",{class:"auto-settings"},
        h("label",{},"Quelle",mode),
        h("label",{},"Stil nach Dateiname",genre),
        h("label",{},"Mix-Länge",bars),
        h("label",{},"Tempo-Spielraum",tolerance)),
      h("label",{class:"auto-random"},random,"Musikalisch gewichtete Zufallsauswahl – keine festen Trackfolgen"),
      h("div",{class:"auto-search"},search,count),
      h("p",{class:"auto-selection-help"},"Mit den Häkchen kannst du Songs für „Nur manuell ausgewählte Songs“ vormerken."),
      list),
    stand,
    h("p",{class:"auto-privacy"},"Lokal: Analyse durch ffmpeg, Mixing mit Web Audio. BPM und Phrasengrenzen sind Schätzungen – keine echten Genre-, Stimm- oder Harmonietags. Originale bleiben unverändert."));
  const mixer=new AutoMixer(api,{
    status:text=>{ if(!beendet) stand.textContent=text; },
    song:(song,info)=>{
      if(beendet)return;
      aktuell={song,info};
      now.textContent=song.text;
      meta.textContent=info.bpm.toFixed(1)+" BPM · "+klassifizierung(info).join(" · ")+
        " · Beat-Sicherheit "+Math.round(info.confidence*100)+" %";
      timeline(arc,info);
    },
    plan:plan=>{
      if(beendet)return;
      next.replaceChildren();
      if(!plan){next.textContent="Ich suche den nächsten musikalischen Einstieg …";return;}
      const cue=plan.cue;
      next.append(
        h("strong",{},plan.song.text),
        h("p",{},"Übergang bei "+uhr(cue.startA)+" → Einstieg "+uhr(cue.startB)),
        h("p",{},"Ausgang: "+cue.ausgang+" · Eingang: "+cue.eingang),
        h("p",{},cue.bpm.toFixed(1)+" BPM · "+"Tempo B: "+
          (cue.rateB*100).toFixed(1)+" % · "+cue.bars+" Takte überblenden"),
        h("p",{class:"auto-confidence"},"Struktur-Schätzung "+Math.round(cue.confidence*100)+" % · Energiematch "+
          Math.round((1-Math.abs(cue.energieA-cue.energieB))*100)+" %"));
    },
    history:entries=>{
      if(beendet)return;
      history.replaceChildren(...entries.slice(-9).reverse().map((item,i)=>
        h("li",{},h("span",{},String(entries.length-i).padStart(2,"0")),item.text)));
    },
    progress:(t,d)=>{
      if(beendet)return;
      duration.textContent=uhr(t)+" / "+uhr(d);
      position.firstChild.style.width=(Number.isFinite(d)&&d>0?Math.min(100,100*t/d):0)+"%";
    }
  });

  function pool() {
    const token=search.value.trim().toLocaleLowerCase("de");
    return alle.filter(s=>!token||s.text.toLocaleLowerCase("de").includes(token)||
      s.release.toLocaleLowerCase("de").includes(token));
  }
  function erlaubt() {
    const stil=genre.value;
    let songs=alle.filter(s=>!stil||s.genres.includes(stil));
    if(mode.value==="favoriten") songs=songs.filter(s=>s.rating>0);
    if(mode.value==="auswahl") songs=songs.filter(s=>selected.has(s.pfad));
    return songs;
  }
  function aktualisieren() {
    const sichtbar=pool();
    const filter=genre.value;
    const zeilen=sichtbar.filter(s=>!filter||s.genres.includes(filter)).slice(0,150);
    list.replaceChildren(...zeilen.map(s=>{
      const check=h("input",{type:"checkbox",checked:selected.has(s.pfad),"aria-label":s.text+" für persönliche Auswahl"});
      check.addEventListener("change",()=>{if(check.checked)selected.add(s.pfad);else selected.delete(s.pfad);count.textContent=selected.size+" vorgemerkt · "+erlaubt().length+" im Set";});
      return h("label",{class:"auto-songrow"},check,
        h("span",{},h("strong",{},s.titel),h("small",{},s.artist+" · "+s.release)),
        s.rating>0?h("em",{},"♥ "+s.rating):null,
        s.genres.length?h("small",{},s.genres.slice(0,2).join(", ")):null);
    }));
    count.textContent=selected.size+" vorgemerkt · "+erlaubt().length+" im Set";
    if(!zeilen.length) list.append(h("p",{},"Keine passenden Songs gefunden."));
  }

  async function katalogLaden() {
    if(beendet)return;
    try {
      const data=await api.katalog();
      if(beendet)return;
      if(data.zustand==="laeuft"&&!data.anzahl_dateien){
        katalogTimer=setTimeout(katalogLaden,1600); return;
      }
      alle=katalogSongs(data);
      const genres=[...new Set(alle.flatMap(s=>s.genres))].sort();
      genre.append(...genres.map(g=>h("option",{value:g},g)));
      aktualisieren();
      stand.textContent=alle.length?
        alle.length+" einzigartige Songs gefunden. Auto-Set kann gestartet werden.":
        "Noch keine Songs im lokalen Sirens-Katalog.";
    }catch(err){if(!beendet)stand.textContent="Katalog nicht verfügbar: "+(err.meldung||err.message);}
  }
  search.addEventListener("input",aktualisieren);
  mode.addEventListener("change",aktualisieren);
  genre.addEventListener("change",aktualisieren);
  random.addEventListener("change",()=>{stand.textContent=random.checked?
    "Zufallsmodus aktiv: musikalisch gewichtete Auswahl.":
    "Die Übergänge werden weiterhin bewertet; weniger zufällige Reihenfolge.";});
  start.addEventListener("click",async()=>{
    const songs=erlaubt();
    if(songs.length<2){stand.textContent="Mindestens zwei passende Songs erforderlich. Quelle/Filter prüfen.";return;}
    start.disabled=true; stop.disabled=false;
    start.textContent="▶ Läuft …";
    try {
      const started=await mixer.starten(songs,{bars:Number(bars.value),
        tolerance:Number(tolerance.value),randomness:random.checked});
      if(!started||beendet)return;
      laufend=true; nextBeat.disabled=false;
    }catch(err){
      stand.textContent=err.meldung||err.message||String(err);
      laufend=false;stop.disabled=true;start.disabled=false;start.textContent="▶ Endlos-Set starten";
    }
  });
  stop.addEventListener("click",()=>{
    mixer.stop();laufend=false;
    start.disabled=false;stop.disabled=true;nextBeat.disabled=true;
    start.textContent="▶ Endlos-Set starten";
    stand.textContent="Set angehalten.";
  });
  nextBeat.addEventListener("click",()=>mixer.naechsterTakt());
  katalogLaden();
  return {el:toy, activate:()=>{
    if(!stopVisual)stopVisual=visualisieren(neon,scope,
      ()=>mixer.engine.analyser,()=>"cosmic",isProducing);
  }, deactivate:()=>{stopVisual?.();stopVisual=null;}, stop:()=>{
    mixer.stop();laufend=false;
    start.disabled=false;stop.disabled=true;nextBeat.disabled=true;
    start.textContent="▶ Endlos-Set starten";
  }, destroy:()=>{
    beendet=true;clearTimeout(katalogTimer);stopVisual?.();stopVisual=null;mixer.destroy();
  }};
}
