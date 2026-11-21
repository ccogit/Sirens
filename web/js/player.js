// Ein gemeinsamer Player: Es läuft immer nur eine Datei.
import { api } from "./api.js";
import { h, meldung } from "./dom.js";
import { dateiInfo, takeName } from "./logic.js";

const leiste = () => document.getElementById("player");
const audio = () => document.getElementById("player-audio");
let aktuell = null;

function knoepfeAktualisieren() {
  const laeuft = aktuell && !audio().paused;
  for (const k of document.querySelectorAll("button[data-abspielen]")) {
    const an = laeuft && k.dataset.abspielen === aktuell;
    k.setAttribute("aria-pressed", String(Boolean(an)));
    k.textContent = an ? "❚❚" : "▶";
    k.setAttribute("aria-label", `${an ? "Anhalten" : "Anhören"}: ${k.dataset.name}`);
  }
}

export function abspielen(pfad) {
  const a = audio();
  if (aktuell === pfad) {
    if (a.paused) a.play().catch(() => {}); else a.pause();
    return;
  }
  aktuell = pfad;
  const d = dateiInfo(pfad);
  document.getElementById("player-titel").textContent = `${d.titel} – ${takeName(pfad)}`;
  leiste().hidden = false;
  a.src = api.audioUrl(pfad);
  a.play().catch(() => {});
}

export function abspielKnopf(pfad) {
  const d = dateiInfo(pfad);
  return h("button", { type: "button", class: "abspielen", "data-abspielen": pfad, "data-name": `${d.titel}, ${takeName(pfad)}`,
    "aria-pressed": "false", "aria-label": `Anhören: ${d.titel}, ${takeName(pfad)}`, onclick: () => abspielen(pfad) }, "▶");
}

// Zeigt die Datei im Windows-Explorer (markiert in ihrem Ordner).
export function explorerKnopf(pfad) {
  return h("button", { type: "button", class: "klein-knopf", title: "Im Explorer zeigen", "aria-label": `Im Explorer zeigen: ${pfad.split("/").pop()}`,
    onclick: async () => { try { await api.explorer(pfad); } catch (f) { meldung(f.meldung, "fehler"); } } }, "Ordner");
}

export function playerEinrichten() {
  const a = audio();
  for (const ereignis of ["play", "pause", "ended"]) a.addEventListener(ereignis, knoepfeAktualisieren);
  a.addEventListener("error", () => {
    if (aktuell) document.getElementById("player-titel").textContent = "Diese Datei lässt sich nicht abspielen.";
  });
  document.getElementById("player-zu").addEventListener("click", () => {
    a.pause();
    a.removeAttribute("src");
    aktuell = null;
    leiste().hidden = true;
    knoepfeAktualisieren();
  });
}

export { knoepfeAktualisieren };
