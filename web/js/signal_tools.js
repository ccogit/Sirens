// Add a descriptor here to register a new experiment. No navigation/CSS changes required.
import { djPult } from "./lab_pult.js";
import { spielwiese, spielAnhalten } from "./spielwiese.js";
import { autoDjAnsicht } from "./auto_dj.js";
import { kickTausch } from "./kicktausch.js";
import { stemSpiel } from "./stems.js";
import { deckArt, morphArt, transitionArt, kickArt, stemArt } from "./signal_art.js";
import { createLabShell } from "./realtime/shell.js";
import { productionAnsicht } from "./production.js";

// Gewähltes GPU-Profil des RTX Neural Lab; der Signal Room drosselt danach die Visualisierung.
export const rtZustand = { profil: null };

function productionSession() {
  const base = "/api/production/v1/";
  let active = null;
  let disposed = false;
  const controller = new AbortController();
  const cancel = document.createElement("button");
  cancel.textContent = "Produktion abbrechen";
  cancel.disabled = true;
  const message = document.createElement("p");
  message.setAttribute("role", "status");
  async function request(action, signal, data) {
    const response = await fetch(base + action, {
      signal,
      ...(data === undefined ? {} : { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.meldung || "Produktionsaktion fehlgeschlagen");
    return result;
  }
  function delay(signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) { reject(new Error("Session geschlossen")); return; }
      const onAbort = () => { clearTimeout(timer); reject(new Error("Session geschlossen")); };
      const timer = setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, 500);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }
  async function run(action, data, signal) {
    const started = await request(action, signal, data);
    active = started.run_id;
    cancel.disabled = false;
    try {
      while (!signal.aborted) {
        const result = await request("status?run=" + encodeURIComponent(active), signal);
        message.textContent = result.stage || result.status;
        if (result.status === "succeeded") return result;
        if (["failed", "cancelled"].includes(result.status)) {
          throw new Error(result.error?.next_action || result.error || "Produktion abgebrochen");
        }
        await delay(signal);
      }
      throw new Error("Session geschlossen");
    } finally {
      active = null;
      cancel.disabled = true;
    }
  }
  const tool = productionAnsicht({ api: {
    mode: "real",
    create: (data, signal) => run("start", data, signal),
    revise: (id, text, signal) => run("revise", { run: id, text }, signal),
    exportAbleton: (id, signal) => request("ableton-export", signal, { run: id }),
    checkReturn: (id, signal) => request("return?export=" + encodeURIComponent(id), signal),
    importAbleton: (id, signal) => request("ableton-import", signal, { export: id, confirm: true }),
  } });
  cancel.onclick = async () => {
    if (!active || disposed) return;
    try {
      await request("cancel", controller.signal, { run: active });
      if (!disposed) message.textContent = "Abbruch angefordert";
    } catch (e) {
      if (!disposed) message.textContent = e.message;
    }
  };
  tool.el.append(cancel, message);
  return { el: tool.el, destroy() {
    disposed = true;
    controller.abort();
    cancel.onclick = null;
    tool.destroy();
  } };
}

export const werkzeuge = [
  {
    id: "production", titel: "Production Engine", kurz: "Production", gruppe: "Sound Design",
    slogan: "CREATE\nA SONG.", sub: "Produzieren, anhören und optional in Ableton bearbeiten.",
    kategorie: "OFFLINE / PRODUCTION", farbe: "#8eb8ff",
    text: "Nutze lokal vorbereitete Songpläne und vorhandene Instrumente, Assets und Mix-Adapter.",
    tags: ["OFFLINE", "PREVIEW", "ABLETON"], voraussetzung: "LOKAL · konfigurierte Produktionsadapter",
    mount: productionSession,
  },
  {
    id: "pult", titel: "DJ-Pult & Beat-Pads", kurz: "DJ-Pult", gruppe: "Live",
    slogan: "MAKE IT\nMOVE.", sub: "Zwei Tracks. Ein eigener Groove.",
    kategorie: "LIVE MIX / PERFORMANCE", farbe: "#7debd2",
    text: "Mische zwei Songs aus dem Katalog oder vom PC, forme ihren Sound mit Filter, Drive und Echo und spiele eigene Beats dazu.",
    tags: ["2 DECKS", "CROSSFADER", "5 BEAT-PADS"], voraussetzung: "SOFORT · Song wählen oder Datei laden",
    preview: { label: "Crossfader", links: "Deck A", rechts: "Deck B", start: 50, zeichnen: deckArt },
    mount: djPult,
  },
  {
    id: "wiese", titel: "Emblem & Wellen", kurz: "Emblem & Wellen", gruppe: "Live",
    slogan: "BEND\nREALITY.", sub: "Wenn Musik eine sichtbare Form bekommt.",
    kategorie: "SOUND / VISUAL MORPHING", farbe: "#c7a4ff",
    text: "Verbiege Lieblingssongs mit Filter, Echo, Stottern, Rückwärts und Tempo. Forme das audioreaktive Emblem über seine zwölf Klangachsen.",
    tags: ["XY-FLÄCHE", "12 ACHSEN", "WEBGL"], voraussetzung: "SOFORT · Gut bewerteter Song im Katalog",
    preview: { label: "Signal Morph", links: "Organisch", rechts: "Experimentell", start: 45, zeichnen: morphArt },
    mount: () => ({ el: spielwiese(), destroy: spielAnhalten }),
  },
  {
    id: "auto", titel: "Auto-DJ & Endlos-Set", kurz: "Auto-DJ", gruppe: "Analyse",
    slogan: "NEVER\nSTOP.", sub: "Ein Set, das sich selbst weiterentwickelt.",
    kategorie: "SMART DJ / CONTINUOUS SET", farbe: "#8eb8ff",
    text: "Sirens wählt passende Titel, schätzt Tempo und Phrasen und mischt den nächsten Übergang. Steuere die Dramaturgie des gesamten Sets.",
    tags: ["BEATMATCH", "CUE-ANALYSE", "ENERGIE-REGIE"], voraussetzung: "LOKALE ANALYSE · ffmpeg · mindestens zwei Songs",
    preview: { label: "Übergang", links: "Track A", rechts: "Track B", start: 50, zeichnen: transitionArt },
    mount: ({ isProducing }) => {
      const tool = autoDjAnsicht(isProducing);
      return { el: tool.el, activate: tool.activate, destroy: tool.destroy };
    },
  },
  {
    id: "kick", titel: "Kick-Tausch", kurz: "Kick-Tausch", gruppe: "KI / Analyse",
    slogan: "NEW\nHEARTBEAT.", sub: "Ein anderer Puls für denselben Track.",
    kategorie: "SOUND DESIGN / TRANSPLANT", farbe: "#ffab79",
    text: "Übertrage den Kick-Sound eines anderen Songs, ohne den ursprünglichen Groove aufzugeben. Vergleiche das berechnete Ergebnis direkt mit dem Original.",
    tags: ["KICK-TRANSFER", "PITCH MATCH", "A/B"], voraussetzung: "VORBEREITUNG · Zwei Favoriten · Stem-Trennung",
    preview: { label: "Kick-Charakter", links: "Original", rechts: "Neue Kick", start: 65, zeichnen: kickArt },
    mount: kickTausch,
  },
  {
    id: "stems", titel: "KI Stem Studio & Warp Stage", kurz: "Stem Studio", gruppe: "KI / Analyse",
    slogan: "REWIRE\nTHE TRACK.", sub: "Ein Song ist mehr als die Summe seiner Spuren.",
    kategorie: "DECONSTRUCTION / LOCAL AI", farbe: "#d9fa76",
    text: "Trenne Gesang, Bass und Drums vom Rest, mische die Einzelspuren neu und entdecke alternative Instrumentenklänge in audioreaktiven 3D-Welten.",
    tags: ["4 / 6 STEMS", "INSTRUMENT MORPH", "WARP STAGE"], voraussetzung: "LOKALE KI · Demucs · Basic Pitch optional",
    preview: { label: "Stem-Isolation", links: "Mix", rechts: "Einzelspuren", start: 70, zeichnen: stemArt },
    mount: ({ isProducing }) => {
      const tool = stemSpiel(isProducing);
      return { el: tool.el, destroy: tool.beenden };
    },
  },
  {
    id: "rt", titel: "RTX Neural Lab", kurz: "RTX Neural Lab", gruppe: "KI / Analyse",
    slogan: "NEURAL\nPERFORMANCE.", sub: "KI-Transformation, Pads, Effekte und Aufnahme in Echtzeit.",
    kategorie: "REALTIME / LOCAL GPU", farbe: "#76b900",
    text: "Stems, DSP-Rack, Performance-Pads und neuronale Klangveränderung auf der lokalen GPU. Nicht installierte oder nicht gemessene Modelle bleiben abgeschaltet und sind benannt.",
    tags: ["GPU-PROFILE", "PADS", "STEMS", "AUFNAHME"], voraussetzung: "SIRENS_RT_ENABLED · Modelle einzeln installiert",
    preview: { label: "Dry / Wet", links: "Original", rechts: "Neural", start: 40, zeichnen: stemArt },
    mount: () => {
      const el = document.createElement("div");
      el.className = "lab-toy";
      const shell = createLabShell({ onProfile: profil => { rtZustand.profil = profil; } });
      shell.mount(el);
      return { el, destroy: () => shell.destroy() };
    },
  },
];
