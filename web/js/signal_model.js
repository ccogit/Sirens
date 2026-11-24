// Pure registry helpers; storage failures never prevent using the Lab.
export const limitRecent = 6;
export function toolWahl(tools, id) {
  return tools.find(t => t.id === id) || tools[0] || null;
}
export function recentAdd(recent, id) {
  return [id, ...recent.filter(x => x !== id)].slice(0, limitRecent);
}
export function filterTools(tools, { query="", filter="all", favorites=[], recent=[] }={}) {
  const norm = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
  const terms = norm(query).trim().split(/\s+/).filter(Boolean);
  const list = tools.filter(t => {
    const matchesFilter = filter === "all" || (filter === "favorites" ? favorites.includes(t.id) :
      filter === "recent" ? recent.includes(t.id) : filter === "group:"+t.gruppe);
    const haystack = norm([t.titel,t.kurz,t.gruppe,t.sub,t.kategorie,t.slogan,t.text,t.voraussetzung,...(t.tags||[])].join(" "));
    return matchesFilter && terms.every(term=>haystack.includes(term));
  });
  if (filter === "recent") list.sort((a,b)=>recent.indexOf(a.id)-recent.indexOf(b.id));
  return list;
}
export function readList(storage,key,tools) {
  try {
    const raw=JSON.parse(storage.getItem(key)||"[]");
    return Array.isArray(raw) ? [...new Set(raw.filter(id=>tools.some(t=>t.id===id)))] : [];
  } catch { return []; }
}
export function validateTools(tools) {
  const ids=new Set();
  for(const t of tools) {
    if(!/^[a-z][a-z0-9-]*$/.test(t.id)||ids.has(t.id)||typeof t.mount!=="function"||
       !["titel","gruppe","slogan","sub","kategorie","text","voraussetzung"].every(k=>typeof t[k]==="string"&&t[k])||
       !/^#[0-9a-f]{6}$/i.test(t.farbe)) throw new Error("Ungültiges Lab-Werkzeug: "+t.id);
    ids.add(t.id);
  }
  return tools;
}
// Only one runtime exists at a time. Close before mounting another; cleanup on failed activation.
export function createSession(host, context) {
  let active=null;
  function close() {
    const old=active; active=null;
    try { old?.destroy(); } finally { host.replaceChildren(); }
  }
  function open(tool) {
    close();
    const instance=tool.mount(context);
    if(!instance?.el||typeof instance.destroy!=="function") {
      instance?.destroy?.();
      throw new Error("Werkzeug benötigt el und destroy()");
    }
    active=instance;
    try { host.append(instance.el); instance.activate?.(); }
    catch(err) { close(); throw err; }
  }
  return {open,close};
}
