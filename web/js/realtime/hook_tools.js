// WP28: Sichtbarkeit ist keine Modellfreigabe. Fehlende Deskriptoren bleiben sichtbar.
export const HOOK_TOOLS = Object.freeze([
  ["demon","DEMON Neural Remix Deck"],["roformer","RoFormer"],["drumsep","DrumSep"],
  ["rave","RAVE"],["after","AFTER"],["stable_audio","Generative Performance Pads"],
  ["sam_audio","Semantic Stem Extractor"],["magenta","Generative Companion"],
  ["dsp","DSP Rack"],["drum","Drum Architect"],["crossover","Stem Crossover"],
  ["acid","Acid Transformer"],["mutation","Infinite Mutation"]
]);
export function hookState(id, descriptors, {error=null, wired=false, measured=false, diagnostics=null}={}) {
  const registryId=id==="roformer"?"separation":id;
  const cap=descriptors?.find(c=>c.id===registryId);
  const diagnostic=diagnostics?.[registryId];
  if(error)return {enabled:false,text:"Fehler: "+(error.message||"API nicht verfügbar"),controls:cap?.controls||[]};
  if(!descriptors)return {enabled:false,text:"Fähigkeiten werden geladen",controls:[]};
  if(diagnostic){
    const reasons=[];
    if(!diagnostic.interpreter_present)reasons.push("Nicht installiert (Interpreter fehlt)");
    if(!diagnostic.gate_report_present)reasons.push("Nicht gemessen (G1-Bericht fehlt)");
    if(reasons.length)return {enabled:false,text:reasons.join(" · "),controls:cap?.controls||[]};
  }
  if(!cap)return {enabled:false,text:"Nicht installiert / nicht gemessen",controls:[]};
  if(!cap.available)return {enabled:false,text:"Nicht installiert oder nicht gemessen / freigegeben",controls:cap.controls||[]};
  if(id==="roformer"&&diagnostic?.available)return {enabled:false,text:"Registry: verfügbar · Bedienung im Advanced Stem Studio (Offline)",controls:cap.controls||[]};
  if(!wired||!measured)return {enabled:false,text:"Registry: verfügbar · Bedienpfad oder Hörprüfung nicht freigegeben",controls:cap.controls||[]};
  return {enabled:true,text:"Verfügbar",controls:cap.controls||[]};
}
export function descriptorControls(controls) {
  return controls.filter(c=>typeof c.name==="string" && Number.isFinite(c.min) &&
    Number.isFinite(c.max) && Number.isFinite(c.default) && c.min<=c.default && c.default<=c.max)
    .map(c=>({...c,step:/^(seed|steps|bypass)$/.test(c.name)?1:"any"}));
}

const ACTIONS = Object.freeze({
  demon:["Remix"],roformer:["Trennen"],drumsep:["Drums trennen"],rave:["Mutation"],
  after:["Struktur / Timbre"],stable_audio:["Rise","Fill","Drop","Break","Bassline","Extend"],
  sam_audio:["Ziel / Rest trennen"],magenta:["Begleitspur erzeugen"],
  dsp:["DSP aktivieren"],drum:["Drum vorbereiten"],crossover:["Stems mischen"],
  acid:["Acid vorbereiten"],mutation:["Automation starten"]
});
const PROMPTS = Object.freeze({demon:"Prompt",sam_audio:"Zielbeschreibung",magenta:"Stilreferenz"});
// Die Karten sind bewusst nicht selbst ein Worker-/Audio-Einstieg. Nur ein vom
// Shell-Controller bereitgestellter, freigegebener Pfad darf Aktionen aktivieren.
export function mountHookTools(host, {document=host.ownerDocument}={}) {
  const cards=new Map();
  const el=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
  for(const [id,label] of HOOK_TOOLS){
    const card=el("section"), title=el("h3",label), status=el("p"), fields=el("div");
    status.setAttribute("role","status");
    const actions=ACTIONS[id].map(name=>{const button=el("button",name);button.type="button";button.disabled=true;return button;});
    card.append(title,status,fields,...actions);host.append(card);
    cards.set(id,{status,fields,actions,signature:null});
  }
  return {
    paint(descriptors,error=null,diagnostics=null){
      for(const [id,card] of cards){
        const state=hookState(id,descriptors,{error,diagnostics});
        card.status.textContent=state.text;
        const controls=descriptorControls(state.controls);
        const signature=JSON.stringify(controls);
        if(card.signature===signature)continue;
        card.signature=signature;
        card.fields.replaceChildren();
        for(const c of controls){
          const label=el("label",c.name+" "), input=el("input");
          input.type="range";input.min=String(c.min);input.max=String(c.max);
          input.step=String(c.step);input.value=String(c.default);input.disabled=true;
          input.setAttribute("aria-label",c.name);
          label.append(input);card.fields.append(label);
        }
        if(PROMPTS[id]){
          const label=el("label",PROMPTS[id]+" "), input=el("input");
          input.type="text";input.maxLength=512;input.disabled=true;
          label.append(input);card.fields.append(label);
        }
      }
    },
    destroy(){host.replaceChildren();cards.clear();}
  };
}
