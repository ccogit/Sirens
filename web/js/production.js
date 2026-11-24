// Signal Room session; API is supplied by the K08 integration, not by this module.
export function productionAnsicht({ api = null, document: doc = globalThis.document } = {}) {
  const controller = new AbortController();
  const el = doc.createElement("section");
  el.className = "production-session";
  let destroyed = false, busy = false, run = null, exchange = null, ready = false;
  const node = (tag, text, parent = el) => {
    const item = doc.createElement(tag);
    if (text) item.textContent = text;
    parent.append(item);
    return item;
  };
  node("h2", "Song erstellen");
  const prompt = node("textarea");
  prompt.placeholder = "Wie soll dein Song klingen?";
  prompt.setAttribute("aria-label", "Songbeschreibung");
  const status = node("p", "Produktion: nicht verfügbar");
  status.setAttribute("role", "status");
  const error = node("p", "");
  error.setAttribute("role", "alert");
  const create = node("button", "Song erstellen");
  const audio = node("audio");
  audio.controls = true;
  audio.preload = "none";
  audio.autoplay = false;
  const revision = node("textarea");
  revision.placeholder = "Was möchtest du verbessern?";
  revision.setAttribute("aria-label", "Verbesserungswunsch");
  const improve = node("button", "Verbessern");
  const like = node("button", "Gefällt mir");
  const save = node("button", "In Katalog übernehmen");
  const open = node("button", "In Ableton öffnen");
  const returned = node("button", "Ableton-Fassung übernehmen");
  const details = node("details");
  node("summary", "Details", details);
  const mode = node("select", "", details);
  mode.setAttribute("aria-label", "Produktionsumfang");
  for (const name of ["full", "preview"]) {
    const option = node("option", name === "full" ? "Vollsong" : "Preview", mode);
    option.value = name;
  }
  mode.value = "full";
  const info = node("pre", "", details);
  const check = node("button", "Ableton-Eingang prüfen", details);

  const available = api && ["mock", "real"].includes(api.mode) && typeof api.create === "function";
  const method = name => available && typeof api[name] === "function";
  function sync() {
    create.disabled = !available || busy;
    audio.hidden = !run;
    revision.hidden = improve.hidden = like.hidden = save.hidden = !run;
    improve.disabled = busy || !method("revise");
    like.disabled = busy || !method("like");
    save.disabled = busy || !method("save") || api.mode !== "real";
    open.hidden = !run || !method("exportAbleton");
    open.disabled = busy;
    returned.hidden = !run || !ready || !method("importAbleton");
    returned.disabled = busy;
    check.hidden = !exchange || !method("checkReturn");
    check.disabled = busy;
  }
  status.textContent = available ? "Produktion: " + (api.mode === "mock" ? "Mock – Testbetrieb" : "Real") : "Produktion: nicht verfügbar";
  function stop() {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }
  function setRun(next) {
    if (!next || next.status !== "succeeded" || next.validated !== true ||
        typeof next.run_id !== "string" || typeof next.audio_url !== "string" ||
        !next.audio_url.startsWith("/") || next.audio_url.startsWith("//")) {
      throw new Error("Kein validiertes abspielbares Ergebnis");
    }
    stop();
    run = next;
    exchange = null;
    ready = false;
    audio.src = run.audio_url;
    info.textContent = JSON.stringify({ references: run.references ?? null,
      report: run.report ?? null, backend: run.backend ?? null,
      blind_pairs: run.blind_pairs ?? null }, null, 2);
  }
  async function action(fn, accept) {
    if (busy || destroyed) return;
    busy = true;
    error.textContent = "";
    sync();
    try {
      const result = await fn(controller.signal);
      if (!destroyed) accept(result);
    } catch (e) {
      if (!destroyed) error.textContent = e?.message || "Aktion fehlgeschlagen";
    } finally {
      busy = false;
      if (!destroyed) sync();
    }
  }
  create.onclick = () => action(signal => api.create({ prompt: prompt.value, mode: mode.value }, signal), setRun);
  improve.onclick = () => action(signal => api.revise(run.run_id, revision.value, signal), setRun);
  like.onclick = () => action(signal => api.like(run.run_id, signal), () => { status.textContent += " · Gefällt mir erfasst"; });
  save.onclick = () => action(signal => api.save(run.run_id, signal), () => { status.textContent += " · Übernommen"; });
  open.onclick = () => action(signal => api.exportAbleton(run.run_id, signal), result => {
    if (!result || result.validated !== true || !result.export_id) throw new Error("Ableton-Export nicht validiert");
    if (result.mode === "set" && result.project_file?.endsWith(".als")) {
      status.textContent = "Ableton-Set: " + result.project_file;
    } else if (result.mode === "import_bundle") {
      status.textContent = "Ableton-Importpaket (kein gespeichertes Set): " + (result.instructions || "WAV/MIDI ab 1.1.1 importieren");
    } else if (result.mode === "live_editable" && result.project_file == null) {
      status.textContent = "Live-Set editierbar, nicht als ALS gespeichert";
    } else throw new Error("Kein bestätigtes Set oder Importpaket");
    exchange = result;
    ready = false;
  });
  check.onclick = () => action(signal => api.checkReturn(exchange.export_id, signal), result => {
    ready = result?.validated === true && result.export_id === exchange.export_id;
    if (!ready) throw new Error("Noch kein validierter Ableton-Eingang");
  });
  returned.onclick = () => action(signal => api.importAbleton(exchange.export_id, signal), setRun);
  sync();
  return { el, destroy() {
    if (destroyed) return;
    destroyed = true;
    controller.abort();
    for (const item of [create, improve, like, save, open, check, returned]) item.onclick = null;
    stop();
    run = exchange = null;
  } };
}
