// Signal Room: discovery shell and real, exclusive audio sessions.
import { api } from "./api.js";
import { h, meldung } from "./dom.js";
import { werkzeuge } from "./signal_tools.js";
import { signalArt } from "./signal_art.js";
import { toolWahl, recentAdd, filterTools, readList, validateTools, createSession } from "./signal_model.js";
export { katalogEintraege } from "./lab_pult.js";

const nummer = n => String(n).padStart(2,"0");
const keys={selected:"sirens.spielzeug",favorites:"sirens.signal.favorites",recent:"sirens.signal.recent"};
function lesen(key) { try { return localStorage.getItem(key); } catch { return null; } }
function speichern(key,value) { try { localStorage.setItem(key,value); } catch { /* private mode */ } }
function listeLesen(key,tools) { try { return readList(localStorage,key,tools); } catch { return []; } }
function button(text,attrs={}) { return h("button",{type:"button",...attrs},text); }

export function liveLabAnsicht(el) {
  const tools=validateTools(werkzeuge);
  if (!tools.length) { el.append(h("p",{},"Noch keine Lab-Werkzeuge registriert.")); return () => {}; }
  let selected=toolWahl(tools,lesen(keys.selected)||"stems"), filter="all", query="";
  let favorites=listeLesen(keys.favorites,tools), recent=listeLesen(keys.recent,tools);
  let beendet=false, produktion=false, session=false, focusMode=false;
  const state=h("span",{class:"sr-production",role:"status"},"STATUS WIRD GELADEN");
  const root=h("section",{class:"signal-room lab-page","aria-label":"Sirens Signal Room"});
  const header=h("header",{class:"sr-intro"},
    h("div",{},h("p",{class:"sr-eyebrow"},"SIRENS / EXPERIMENTAL DIVISION"),h("h1",{},"SIGNAL ",h("em",{},"ROOM."))),
    h("div",{class:"sr-intro-copy"},h("p",{},h("strong",{},"Music is material. Break the rules.")," Entdecke, forme und rekonstruiere deinen Sound."),state));
  const search=h("input",{type:"search",placeholder:"Experimente suchen …","aria-label":"Experimente suchen",autocomplete:"off"});
  const count=h("span",{class:"sr-count","aria-live":"polite"});
  const filters=h("div",{class:"sr-filters",role:"group","aria-label":"Werkzeugfilter"});
  const list=h("div",{class:"sr-list",role:"group","aria-label":"Experiment-Index"});
  const index=h("aside",{class:"sr-index"},
    h("div",{class:"sr-index-head"},h("div",{class:"sr-index-title"},h("strong",{},"Experiment-Index"),count),
      h("label",{class:"sr-search"},h("span",{"aria-hidden":"true"},"⌕"),search),filters),
    list,h("div",{class:"sr-index-foot"},"SIRENS / LAB SERIES",h("span",{},"01—"+nummer(tools.length))));
  const art=h("div",{class:"sr-art","aria-hidden":"true"});
  const category=h("p",{class:"sr-eyebrow"});
  const headline=h("h2",{class:"sr-headline"});
  const hook=h("p",{class:"sr-hook"});
  const hero=h("div",{class:"sr-hero"},art,h("span",{class:"sr-graphic-note"},"⊕  SIGNAL STUDY / DEMO"),
    h("div",{class:"sr-hero-text"},category,headline,hook));
  const name=h("h3",{class:"sr-tool-name"}), description=h("p",{class:"sr-description"});
  const star=button("☆",{class:"sr-star",onclick:toggleFavorite});
  const tags=h("div",{class:"sr-tags"}), prep=h("p",{class:"sr-prep"});
  const level=h("input",{type:"range",min:0,max:100,value:50,"aria-label":"Vorschau"});
  const levelLabel=h("span",{}), value=h("output",{}), left=h("span",{}), right=h("span",{});
  const preview=h("div",{class:"sr-preview"},h("label",{},h("span",{class:"sr-preview-label"},levelLabel,value),level),
    h("div",{class:"sr-preview-ends"},left,right),h("small",{},"VISUELLE DEMO · KEIN AUDIO"));
  const launch=button("Experiment starten →",{class:"sr-launch",onclick:openSession});
  const detail=h("div",{class:"sr-detail"},h("div",{},h("div",{class:"sr-detail-title"},name,star),description,tags),
    h("div",{class:"sr-action"},preview,launch,prep));
  const stageNumber=h("span",{class:"sr-stage-number"}), mode=h("span",{},"DISCOVERY MODE");
  const stage=h("section",{class:"sr-stage","aria-label":"Experiment-Vorschau"},
    h("div",{class:"sr-stagebar"},stageNumber,mode),hero,detail);
  const discovery=h("div",{class:"sr-discovery"},index,stage);
  const sessionTitle=h("h2",{tabindex:"-1"});
  const sessionMeta=h("p",{class:"sr-eyebrow"});
  const back=button("← Experiment-Index",{class:"sr-secondary",onclick:()=>closeSession(true)});
  const focus=button("Fokusmodus",{class:"sr-secondary","aria-pressed":"false",onclick:()=>setFocus(!focusMode)});
  const full=button("Vollbild",{class:"sr-secondary",onclick:async()=>{
    try { if(document.fullscreenElement===root) await document.exitFullscreen(); else await root.requestFullscreen(); }
    catch { meldung("Vollbild wird von diesem Browser nicht unterstützt."); }
  }});
  if(!root.requestFullscreen) full.hidden=true;
  const host=h("div",{class:"lab-toy sr-runtime"});
  const sessionPanel=h("section",{class:"sr-session",hidden:true,"aria-label":"Aktives Werkzeug"},
    h("header",{class:"sr-session-head"},h("div",{},sessionMeta,sessionTitle),
      h("div",{class:"sr-session-actions"},back,focus,full)),host);
  const footer=h("footer",{class:"sr-footer"},"LOCAL AUDIO / ORIGINALDATEIEN BLEIBEN UNVERÄNDERT",h("span",{},"SIRENS · SIGNAL ROOM"));
  root.append(header,discovery,sessionPanel,footer);el.append(root);
  const runtime=createSession(host,{isProducing:()=>produktion});
  const filterDefs=[["all","Alle"],["favorites","★ Favoriten"],["recent","Zuletzt"],
    ...[...new Set(tools.map(t=>t.gruppe))].map(g=>["group:"+g,g])];
  for(const [id,label] of filterDefs) filters.append(button(label,{class:"sr-filter","data-filter":id,
    onclick:()=>{filter=id;renderList();}}));

  function renderList(restoreId) {
    const visible=filterTools(tools,{query,filter,favorites,recent});
    count.textContent=nummer(visible.length)+" / "+nummer(tools.length);
    for(const b of filters.children)b.setAttribute("aria-pressed",String(b.dataset.filter===filter));
    list.replaceChildren();
    if(!visible.length)list.append(h("p",{class:"sr-empty"},"Keine passenden Experimente. Filter oder Suche ändern."));
    for(const tool of visible) {
      const b=h("button",{type:"button",class:"sr-tool","data-id":tool.id,"aria-pressed":String(tool.id===selected.id),
        onclick:()=>{selected=tool;speichern(keys.selected,tool.id);renderDetail();renderList(tool.id);
          if(window.matchMedia?.("(max-width: 670px)").matches) stage.scrollIntoView({block:"start",behavior:"auto"});}},
        h("span",{class:"sr-num"},"/"+nummer(tools.indexOf(tool)+1)),
        h("span",{},h("strong",{},tool.kurz||tool.titel,favorites.includes(tool.id)?" ★":""),
          h("small",{},tool.sub)),h("span",{class:"sr-arrow","aria-hidden":"true"},"↗"));
      b.style.setProperty("--sr-tool",tool.farbe);list.append(b);
    }
    if(restoreId) [...list.children].find(b=>b.dataset.id===restoreId)?.focus({preventScroll:true});
  }
  function renderArt() {
    const p=selected.preview, v=Number(level.value)/100;
    art.replaceChildren((p?.zeichnen||signalArt)(selected.farbe,v));
    value.textContent=level.value+" %";
  }
  function renderDetail() {
    root.style.setProperty("--sr-accent",selected.farbe);
    stageNumber.textContent="EXPERIMENT "+nummer(tools.indexOf(selected)+1)+" / "+nummer(tools.length);
    category.textContent=selected.kategorie;headline.textContent=selected.slogan;hook.textContent=selected.sub;
    name.textContent=selected.titel;description.textContent=selected.text;prep.textContent=selected.voraussetzung;
    tags.replaceChildren(...(selected.tags||[]).map(tag=>h("span",{},tag)));
    const fav=favorites.includes(selected.id);
    star.textContent=fav?"★":"☆";star.setAttribute("aria-pressed",String(fav));
    star.setAttribute("aria-label",fav?"Aus Favoriten entfernen":"Zu Favoriten hinzufügen");
    const p=selected.preview;
    level.value=p?.start??50;levelLabel.textContent=p?.label||"Signalform";
    level.setAttribute("aria-label",levelLabel.textContent+" (visuelle Demo)");
    left.textContent=p?.links||"Ruhig";right.textContent=p?.rechts||"Intensiv";
    renderArt();
  }
  function toggleFavorite() {
    favorites=favorites.includes(selected.id)?favorites.filter(id=>id!==selected.id):[...favorites,selected.id];
    speichern(keys.favorites,JSON.stringify(favorites));
    const fav=favorites.includes(selected.id);star.textContent=fav?"★":"☆";
    star.setAttribute("aria-pressed",String(fav));star.setAttribute("aria-label",fav?"Aus Favoriten entfernen":"Zu Favoriten hinzufügen");
    renderList();
  }
  function setFocus(on) {
    focusMode=on;root.classList.toggle("sr-focused",on);
    focus.setAttribute("aria-pressed",String(on));focus.textContent=on?"Fokus beenden":"Fokusmodus";
  }
  function openSession() {
    if(session||beendet)return;
    discovery.hidden=true;sessionPanel.hidden=false;
    sessionTitle.textContent=selected.titel;sessionMeta.textContent="SESSION / "+selected.kategorie;
    document.getElementById("player-audio")?.pause();
    try { runtime.open(selected); }
    catch(err) {
      discovery.hidden=false;sessionPanel.hidden=true;
      meldung("Experiment konnte nicht geöffnet werden: "+(err.message||err),"fehler");return;
    }
    session=true;root.classList.add("sr-in-session");
    recent=recentAdd(recent,selected.id);speichern(keys.recent,JSON.stringify(recent));
    speichern(keys.selected,selected.id);
    sessionTitle.focus();window.scrollTo(0,0);
  }
  function closeSession(focusLaunch=false) {
    if(!session)return;
    session=false;
    try { runtime.close(); } catch(err) { meldung("Werkzeug konnte nicht vollständig beendet werden: "+(err.message||err),"fehler"); }
    if(document.fullscreenElement===root)document.exitFullscreen().catch(()=>{});
    setFocus(false);root.classList.remove("sr-in-session");sessionPanel.hidden=true;discovery.hidden=false;
    renderList();if(focusLaunch)launch.focus();
  }
  function onKey(e) {
    if(e.key==="Escape"&&focusMode&&!document.fullscreenElement){e.preventDefault();setFocus(false);focus.focus();}
  }
  function fullscreenChanged(){full.textContent=document.fullscreenElement===root?"Vollbild beenden":"Vollbild";}
  document.addEventListener("fullscreenchange",fullscreenChanged);
  root.addEventListener("keydown",onKey);
  search.addEventListener("input",()=>{query=search.value;renderList();});
  level.addEventListener("input",renderArt);
  async function produktionsStand() {
    try {
      const d=await api.claude();if(beendet)return;
      produktion=Boolean(d.laeuft);const label=produktion?"CLAUDE PRODUZIERT · ECO GPU":"CLAUDE IM STANDBY";
      if(state.textContent!==label)state.textContent=label;
      state.dataset.state=produktion?"busy":"idle";
    } catch { if(!beendet){state.textContent="PRODUKTIONSSTATUS OFFLINE";state.dataset.state="offline";} }
  }
  renderDetail();renderList();produktionsStand();
  const timer=setInterval(()=>{if(!document.hidden)produktionsStand();},5000);
  return ()=>{
    beendet=true;clearInterval(timer);
    document.removeEventListener("fullscreenchange",fullscreenChanged);
    root.removeEventListener("keydown",onKey);closeSession();
  };
}
