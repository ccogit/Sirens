// Reine Zustandsableitung, keine Freigabe durch eine Modusbezeichnung allein.
export const modeLabel = mode => ({streaming:"Live",lookahead:"Lookahead",offline:"Offline"}[mode] || "Unbekannt");
export function deriveState({capabilities, gpu, mock=false, songs=0, error=null, capabilityId=null}) {
  const list = capabilities?.capabilities || [];
  const selected = capabilityId ? list.find(c => c.id === capabilityId) : list.find(c => c.available);
  const flags = [];
  if (mock) flags.push("Testmodus – kein Ton, keine KI");
  if (gpu?.available === false) flags.push("Keine GPU verfügbar");
  if (songs === 0) flags.push("Leere Bibliothek");
  const state = (text,enabled=false) => ({text:[text,...flags].filter(Boolean).join(" · "),enabled,selected});
  if (error?.error === "busy_gpu") return state("GPU beschäftigt");
  if (error) return state(error.status === 503 && !capabilities ? "Schalter aus oder RT nicht verfügbar (503)" : "API-Fehler: " + (error.message || error.status || "unbekannt"));
  if (!capabilities) return state("Fähigkeiten werden geladen");
  if (!selected?.available) return state("Kein Modell installiert oder freigegeben");
  if (!mock && !gpu?.available) return state("Keine GPU");
  if (songs === 0) return state("");
  if (!mock || !selected.mock) return state("Audio-Anbindung folgt in WP06 – Bedienung gesperrt");
  return state("",true);
}
