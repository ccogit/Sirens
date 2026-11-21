// Kick-Tausch: ein Song bekommt die Kick eines anderen. Der Dienst trennt die Spuren und rechnet; hier wird gewählt und verglichen.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";
import { lieblingsDateien } from "./logic.js";

const zahl = (wert) => String(wert).replace(".", ",").replace("-", "−");

// Was der Tausch vom Zielsong übernommen hat, in Sätzen.
function bericht(b) {
  const stimmung = b.halbtoene ? `Die fremde Kick ist um ${zahl(Math.abs(b.halbtoene))} Halbtöne ${b.halbtoene > 0 ? "höher" : "tiefer"} gestimmt, damit sie zum Bass passt.`
    : "Die fremde Kick passt in der Tonhöhe schon; sie ist nicht umgestimmt.";
  return [
    `${b.treffer_ziel} Schläge ersetzt – jeder an der Stelle und in der Stärke des bisherigen.`,
    b.pausen.length ? `${b.pausen.length} Pausen und Breaks des Songs bleiben ohne Kick.` : "Der Song hat keine längere Pause ohne Kick.",
    stimmung,
    b.muster > 1 ? `Aus dem Spender stammen ${b.muster} Kick-Klänge (leise bis laut), verteilt nach der Stärke im Zielsong.` : null,
  ].filter(Boolean);
}

// Liefert { el, anhalten() }.
export function kickTausch() {
  let takt = null;
  let tausch = null;   // laufender oder fertiger Tausch
  const original = h("audio", { controls: true, preload: "none" });
  const getauscht = h("audio", { controls: true, preload: "none", hidden: true });
  const wahl = (titel) => h("select", { "aria-label": titel }, h("option", { value: "" }, "Song wählen …"));
  const ziel = wahl("Dieser Song bekommt eine neue Kick");
  const spender = wahl("Von diesem Song kommt die Kick");
  const los = h("button", { type: "button", class: "knopf" }, "Kick tauschen");
  const stand = h("p", { class: "hinweis", role: "status" }, "Wähle zwei Songs, die du kennst. Beim ersten Mal werden je Song die Spuren getrennt; das dauert etwa eine Minute.");
  const ergebnis = h("div", { class: "kick-ergebnis", hidden: true });
  const anhalten = () => { original.pause(); getauscht.pause(); };

  // Zwischen Original und Tausch an derselben Stelle wechseln.
  const umschalter = [["getauscht", "Mit neuer Kick"], ["original", "Original"]].map(([art, text]) =>
    h("button", { type: "button", class: "lab-mode", "data-art": art, onclick: () => hoeren(art) }, text));
  function hoeren(art) {
    const [an, aus] = art === "getauscht" ? [getauscht, original] : [original, getauscht];
    const lief = !aus.paused;
    if (Number.isFinite(aus.currentTime) && aus.currentTime > 0) an.currentTime = aus.currentTime;
    aus.pause(); aus.hidden = true; an.hidden = false;
    for (const k of umschalter) k.setAttribute("aria-pressed", String(k.dataset.art === art));
    if (lief) an.play().catch(() => {});
  }
  for (const audio of [original, getauscht]) audio.addEventListener("play", () => document.getElementById("player-audio")?.pause());

  function zeigen(job) {
    tausch = job;
    los.disabled = job.stand === "wartet" || job.stand === "laeuft";
    if (job.stand === "fehler") { stand.textContent = `Das hat nicht geklappt: ${job.fehler}`; return; }
    if (job.stand !== "fertig") { stand.textContent = `${job.schritt} …`; return; }
    clearInterval(takt);
    stand.textContent = "Fertig. Hör beide Fassungen im Wechsel:";
    original.src = api.audioUrl(job.ziel);
    getauscht.src = api.kickUrl(job.id);
    leeren(ergebnis).append(h("div", { class: "lab-modes", role: "group", "aria-label": "Fassung" }, umschalter), getauscht, original,
      h("ul", { class: "kick-bericht" }, bericht(job.bericht).map((satz) => h("li", {}, satz))));
    ergebnis.hidden = false;
    hoeren("getauscht");
  }

  los.addEventListener("click", async () => {
    if (!ziel.value || !spender.value) { stand.textContent = "Bitte beide Songs wählen."; return; }
    anhalten(); ergebnis.hidden = true; clearInterval(takt);
    try {
      zeigen(await api.kickStart(ziel.value, spender.value));
      if (tausch.stand !== "fertig") takt = setInterval(async () => { try { zeigen(await api.kickStand(tausch.id)); } catch { /* nächster Versuch */ } }, 1500);
    } catch (fehler) { stand.textContent = fehler.meldung; los.disabled = false; }
  });

  (async () => {
    try {
      const [einstellungen, katalog] = await Promise.all([api.einstellungen(), api.katalog("", 1)]);
      const songs = lieblingsDateien(katalog).sort((a, b) => a.titel.localeCompare(b.titel, "de"));
      for (const s of songs) for (const liste of [ziel, spender]) liste.append(h("option", { value: s.pfad }, `${s.titel} · ${s.artist}`));
      if (!einstellungen.kicktausch) { los.disabled = true; stand.textContent = "Die Stem-Trennung ist auf diesem Rechner nicht eingerichtet (SIRENS_STEMS_CMD in der .env oder ein installiertes demucs)."; }
      else if (!songs.length) stand.textContent = "Noch kein gut bewerteter Song da. Bewerte einen Take mit +1 oder +2, dann steht er hier zur Wahl.";
    } catch (fehler) { stand.textContent = fehler.meldung; }
  })();

  const el = h("section", { class: "kicktausch", "aria-label": "Kick-Tausch" },
    h("h2", {}, "Kick-Tausch"),
    h("p", { class: "hinweis" }, "Ein Song bekommt die Kick eines anderen. Groove, Pausen und Steigerungen bleiben die des Songs – nur der Klang der Kick ist fremd."),
    h("div", { class: "kick-wahl" },
      h("label", {}, h("span", {}, "Dieser Song …"), ziel),
      h("label", {}, h("span", {}, "… bekommt die Kick von"), spender),
      los),
    stand, ergebnis);
  return { el, anhalten: () => { anhalten(); } };
}
