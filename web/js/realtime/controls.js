// Datenstrukturen für Tastatur und spätere MIDI-Anbindung.
export const KEY_BINDINGS = Object.freeze({" ":"transport",Escape:"panic",b:"bypass",a:"ab"});
export const MIDI_BINDINGS = Object.freeze({transport:{note:36},panic:{note:37},bypass:{note:38},ab:{note:39},wet:{cc:1}});
export function keyAction(event) {
  if (event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey ||
      event.target?.isContentEditable || /^(INPUT|SELECT|TEXTAREA|BUTTON|A)$/.test(event.target?.tagName || "")) return null;
  return KEY_BINDINGS[event.key] || null;
}
export const DEFAULT_PRESET = Object.freeze({wet:0,bypass:false,gain:1});
export function normalizePreset(value) {
  const clamp = (v,min,max,fallback) => typeof v==="number" && Number.isFinite(v) ? Math.max(min,Math.min(max,v)) : fallback;
  return {wet:clamp(value?.wet,0,100,0),bypass:value?.bypass===true,gain:clamp(value?.gain,0,2,1)};
}
const key = "sirens.rt.presets.v1";
export function readPresets(storage) {
  try {
    const data = JSON.parse(storage.getItem(key));
    if (!data || typeof data !== "object" || Array.isArray(data)) return {};
    return Object.fromEntries(["A","B"].filter(k => Object.hasOwn(data,k)).map(k=>[k,normalizePreset(data[k])]));
  } catch { return {}; }
}
export function savePreset(storage,slot,value) {
  if (!["A","B"].includes(slot)) return false;
  try { storage.setItem(key,JSON.stringify({...readPresets(storage),[slot]:normalizePreset(value)})); return true; }
  catch { return false; }
}
// Alle explizit registrierten Ressourcen gehören genau einer Mount-Generation.
export function createResources(timerHost=globalThis) {
  const cleaners = [];
  return {
    listen(target,type,fn) { target.addEventListener(type,fn); cleaners.push(()=>target.removeEventListener(type,fn)); },
    interval(fn,ms) { const timer=timerHost.setInterval(fn,ms); cleaners.push(()=>timerHost.clearInterval(timer)); },
    clear() { while(cleaners.length) cleaners.pop()(); },
  };
}
