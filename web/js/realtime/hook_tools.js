// WP28: Sichtbarkeit ist keine Modellfreigabe. Fehlende Deskriptoren bleiben sichtbar.
export const HOOK_TOOLS = Object.freeze([
  ["demon","DEMON Neural Remix Deck"],["roformer","RoFormer"],["drumsep","DrumSep"],
  ["rave","RAVE"],["after","AFTER"],["stable_audio","Generative Performance Pads"],
  ["sam_audio","Semantic Stem Extractor"],["magenta","Generative Companion"],
  ["dsp","DSP Rack"],["drum","Drum Architect"],["crossover","Stem Crossover"],
  ["acid","Acid Transformer"],["mutation","Infinite Mutation"]
]);
export function hookState(id, descriptors, {error=null, wired=false, measured=false}={}) {
  const cap=descriptors?.find(c=>c.id===id);
  if(error)return {enabled:false,text:"Fehler: "+(error.message||"API nicht verfügbar"),controls:cap?.controls||[]};
  if(!descriptors)return {enabled:false,text:"Fähigkeiten werden geladen",controls:[]};
  if(!cap)return {enabled:false,text:"Nicht installiert / nicht gemessen",controls:[]};
  if(!cap.available)return {enabled:false,text:"Nicht installiert oder nicht gemessen / freigegeben",controls:cap.controls||[]};
  if(!wired||!measured)return {enabled:false,text:"Registry: verfügbar · Bedienpfad oder Hörprüfung nicht freigegeben",controls:cap.controls||[]};
  return {enabled:true,text:"Verfügbar",controls:cap.controls||[]};
}
export function descriptorControls(controls) {
  return controls.filter(c=>typeof c.name==="string" && Number.isFinite(c.min) &&
    Number.isFinite(c.max) && Number.isFinite(c.default) && c.min<=c.default && c.default<=c.max)
    .map(c=>({...c,step:/^(seed|steps|bypass)$/.test(c.name)?1:"any"}));
}
