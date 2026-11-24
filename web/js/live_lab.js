// Live Lab: Musik während laufender Claude-Produktionen interaktiv hören und verändern.
import { api } from "./api.js";
import { h, meldung } from "./dom.js";
import { LiveAudio } from "./live_audio.js";
import { visualisieren } from "./live_visual.js";
import { spielAnhalten, spielwiese } from "./spielwiese.js";
import { autoDjAnsicht } from "./auto_dj.js";
import { kickTausch } from "./kicktausch.js";
import { stemSpiel } from "./stems.js";
import { createLabShell } from "./realtime/shell.js";

function minuten(t) {
  if (!Number.isFinite(t)) return "0:00";
  return Math.floor(t/60) + ":" + String(Math.floor(t%60)).padStart(2,"0");
}

export function katalogEintraege(daten) {
  const alle = [];
  for (const artist of daten.artists || []) {
    for (const release of artist.releases || []) {
      for (const song of release.songs || []) {
        for (const d of song.dateien || []) alle.push({
          pfad: d.pfad,
          text: artist.slug + " · " + song.titel + (d.fassung ? " (" + d.fassung + ")" : "")
        });
      }
    }
  }
  return alle;
}

// Verwendet die bestehende Drosselung (Auflösung und Bildrate), ohne
// einen zweiten Renderer anzulegen. Ohne RT-Profil unveränderte Legacy-Regel.
export function visualGpuDrosseln(producing, profile) {
  return Boolean(producing || profile === "Neural" || profile === "Eco" || profile === "Training/Render");
}

export function liveLabAnsicht(el) {
  const engine = new LiveAudio();
  let beendet = false, modus = "cosmic", katalogTimer = null, produktionLaeuft = false;
  let statusTimer = null;
  const opt = [[], []];
  const titel = [h("strong", {}, "Deck A bereit"), h("strong", {}, "Deck B bereit")];
  const canvas = h("canvas", { class: "lab-canvas", "aria-label": "Musikreaktive GPU-Visualisierung" });
  const hud = h("canvas", { class: "lab-canvas", "aria-label": "Wellenform oder Frequenzspektrum", hidden: true });
  const status = h("span", { class: "lab-working" }, "Produktionsstatus wird geladen");
  const demo = h("span", { class: "lab-demo" }, "DEMO · Sound laden oder Pads spielen");
  const cross = h("input", { type: "range", min: "0", max: "100", value: "50", "aria-label": "Crossfader zwischen Deck A und B" });
  const effectValues = {};

  function einstellungenAnwenden() {
    engine.setCrossfade(cross.value);
    engine.setFilter(effectValues.filter?.value || 100);
    engine.setDrive(effectValues.drive?.value || 0);
    engine.setEcho(effectValues.echo?.value || 0);
  }

  async function mitAudio(fn) {
    try {
      await engine.aktivieren();
      einstellungenAnwenden();
      await fn();
      demo.textContent = "LIVE · AUDIOREAKTIV";
    } catch (err) {
      meldung("Audio konnte nicht gestartet werden: " + (err.message || err), "fehler");
    }
  }

  function deck(index) {
    const a = engine.decks[index];
    const waehlen = h("select", { "aria-label": "Song für Deck " + (index ? "B" : "A") },
      h("option", { value: "" }, "Song aus dem Katalog wählen …"));
    const lokal = h("input", { type: "file", accept: "audio/*,.mp3,.wav,.ogg,.flac",
      "aria-label": "Eigene Audiodatei für Deck " + (index ? "B" : "A") });
    const play = h("button", { type: "button", class: "lab-play" }, "▶ Abspielen");
    const position = h("input", { type: "range", min: "0", max: "1000", value: "0",
      "aria-label": "Position in Deck " + (index ? "B" : "A") });
    const zeitanzeige = h("span", { class: "lab-clock" }, "0:00 / 0:00");
    const tempo = h("input", { type: "range", min: "65", max: "150", value: "100",
      "aria-label": "Abspielgeschwindigkeit Deck " + (index ? "B" : "A") });
    const tempoWert = h("output", {}, "100 %");
    const gesetzt = (name) => {
      titel[index].textContent = name;
      play.textContent = "▶ Abspielen";
      position.value = "0";
    };
    const loadSong = (src, name, file = false) => {
      engine.laden(index, src, file);
      gesetzt(name);
      demo.textContent = "LIVE · bereit zum Abspielen";
    };
    waehlen.addEventListener("change", () => {
      const hit = opt[index].find((e) => e.pfad === waehlen.value);
      if (hit) { lokal.value = ""; loadSong(api.audioUrl(hit.pfad), hit.text); }
    });
    lokal.addEventListener("change", () => {
      const f = lokal.files?.[0];
      if (!f) return;
      if (!f.type.startsWith("audio/") && !/\.(wav|mp3|ogg|flac)$/i.test(f.name)) {
        meldung("Bitte eine Audiodatei auswählen.", "fehler");
        return;
      }
      waehlen.value = "";
      loadSong(f, f.name, true);
    });
    play.addEventListener("click", () => {
      if (!a.getAttribute("src")) { meldung("Zuerst einen Song wählen oder eine Datei laden."); return; }
      mitAudio(async () => { await engine.schalten(index); });
    });
    a.addEventListener("play", () => { play.textContent = "❚❚ Pause"; });
    a.addEventListener("pause", () => { play.textContent = "▶ Abspielen"; });
    a.addEventListener("error", () => {
      if (!beendet && a.getAttribute("src")) meldung("Dieses Audioformat kann der Browser nicht abspielen.", "fehler");
    });
    a.addEventListener("timeupdate", () => {
      if (Number.isFinite(a.duration) && a.duration > 0) position.value = Math.round(a.currentTime/a.duration*1000);
      zeitanzeige.textContent = minuten(a.currentTime) + " / " + minuten(a.duration);
    });
    position.addEventListener("input", () => {
      if (Number.isFinite(a.duration)) a.currentTime = position.value/1000*a.duration;
    });
    tempo.addEventListener("input", () => {
      engine.setTempo(index, tempo.value);
      tempoWert.textContent = tempo.value + " %";
    });
    return { select: waehlen, el: h("section", { class: "lab-deck" },
      h("div", { class: "lab-deck-heading" },
        h("span", { class: "lab-deck-tag" }, "DECK " + (index ? "B" : "A")), titel[index]),
      waehlen,
      h("label", { class: "lab-file" }, "Oder Datei vom PC wählen", lokal),
      h("div", { class: "lab-transport" }, play, zeitanzeige),
      position,
      h("div", { class: "lab-tempo" }, h("label", {}, "Speed & Pitch"), tempo, tempoWert)) };
  }

  function regler(name, label, value, apply) {
    const input = h("input", { type: "range", min: "0", max: "100", value: String(value), "aria-label": label });
    const out = h("output", {}, value + " %");
    effectValues[name] = input;
    input.addEventListener("input", () => { out.textContent = input.value + " %"; apply(input.value); });
    return h("label", { class: "lab-control" }, h("span", {}, label, out), input);
  }

  const deckA = deck(0), deckB = deck(1);
  const modeButtons = [
    ["cosmic","◉ Neon-Tunnel"], ["spectrum","▥ Spektrum"], ["scope","〰 Oszilloskop"]
  ].map(([key,label]) => h("button", {
    type: "button", class: "lab-mode", "aria-pressed": String(modus === key),
    onclick: () => {
      modus = key;
      for (const b of modeButtons) b.setAttribute("aria-pressed", String(b.dataset.mode === key));
    }, "data-mode": key
  }, label));
  const pads = [
    ["kick","A","KICK"], ["snare","S","SNARE"], ["hat","D","HI-HAT"],
    ["bass","F","BASS"], ["chord","G","CHORD"]
  ].map(([art,key,label]) => h("button", {
    type: "button", class: "lab-pad", "aria-label": label + " mit Taste " + key,
    onclick: () => { mitAudio(() => engine.pad(art)); }
  }, h("span", {}, label), h("kbd", {}, key)));

  const autoToy = autoDjAnsicht(() => produktionLaeuft);
  // Spielzeuge: immer nur eines ist zu sehen und zu hören.
  let spielzeug = (() => { try { const s = localStorage.getItem("sirens.spielzeug"); return ["wiese", "auto", "kick", "stems", "rt"].includes(s) ? s : "pult"; } catch { return "pult"; } })();
  const kick = kickTausch();
  const stems = stemSpiel(() => produktionLaeuft);
  const kisten = {};
  let rtProfile = null;
  const rt = createLabShell({onProfile: profile => {rtProfile = profile;}});
  const spielzeugKnoepfe = [["pult", "🎛 DJ-Pult & Beat-Pads"], ["wiese", "🌀 Emblem & Wellen"], ["auto", "♾ Auto-DJ & Endlos-Set"], ["kick", "🥁 Kick-Tausch"], ["stems", "🎚 KI Stem Studio & Warp Stage"], ["rt", "RTX Neural Lab"]].map(([key, label]) =>
    h("button", { type: "button", class: "lab-mode", "data-toy": key, onclick: () => waehlen(key) }, label));
  function waehlen(key) {
    spielzeug = key;
    try { localStorage.setItem("sirens.spielzeug", key); } catch { /* ohne Speicher */ }
    for (const b of spielzeugKnoepfe) b.setAttribute("aria-pressed", String(b.dataset.toy === key));
    for (const [name, kiste] of Object.entries(kisten)) kiste.hidden = name !== key;
    if (key !== "pult") for (const audio of engine.decks) audio.pause();
    if (key !== "wiese") spielAnhalten();
    if (key !== "kick") kick.anhalten();
    if (key !== "stems") stems.pausieren();
    if (key === "rt") rt.mount(kisten.rt); else rt.pause();
    if (key === "auto") autoToy.activate(); else { autoToy.deactivate(); autoToy.stop(); }
  }

  el.append(h("div", { class: "lab-page" },
    h("header", { class: "lab-header" },
      h("div", {},
        h("p", { class: "lab-eyebrow" }, "SIRENS · INTERACTIVE MUSIC SPACE"),
        h("h1", {}, "Die Wartezeit wird zum Auftritt."),
        h("p", {}, "DJ-Pult, Auto-DJ, Kick-Tausch und KI Stem Studio mit audioreaktivem RTX Warp Stage.")),
      h("a", { href: "#/", class: "lab-back" }, "← Zur Übersicht")),
    h("div", { class: "lab-modes lab-toys", role: "group", "aria-label": "Spielzeug" }, spielzeugKnoepfe),
    kisten.wiese = h("div", { class: "lab-toy" }, spielwiese()),
    kisten.auto = h("div", { class: "lab-toy" }, autoToy.el),
    kisten.kick = h("div", { class: "lab-toy" }, kick.el),
    kisten.stems = h("div", { class: "lab-toy" }, stems.el),
    kisten.rt = h("div", { class: "lab-toy" }),
    kisten.pult = h("div", { class: "lab-toy" },
    h("section", { class: "lab-stage", "aria-label": "Live-Musikvisualisierung" },
      canvas, hud,
      h("div", { class: "lab-stage-top" }, h("span", { class: "lab-live" }, "● VISUAL ENGINE"), status),
      h("div", { class: "lab-stage-bottom" }, demo,
        h("span", {}, "WebGL2 · GPU / Canvas-Fallback · max. 30 FPS"))),
    h("div", { class: "lab-modes", role: "group", "aria-label": "Visualisierungsmodus" }, modeButtons),
    h("div", { class: "lab-decks" }, deckA.el, deckB.el),
    h("section", { class: "lab-mixer" },
      h("div", { class: "lab-mixer-title" }, h("h2", {}, "Live-Mixer"),
        h("p", {}, "Der Sound wird nur im Browser verändert – Originaldateien bleiben unberührt.")),
      h("div", { class: "lab-cross" },
        h("span", {}, "A"), cross, h("span", {}, "B"),
        h("small", {}, "Crossfader")),
      h("div", { class: "lab-controls" },
        regler("filter", "Low-pass Filter", 100, (v) => engine.setFilter(v)),
        regler("drive", "Analog Drive", 0, (v) => engine.setDrive(v)),
        regler("echo", "Space Echo", 0, (v) => engine.setEcho(v)))),
    h("section", { class: "lab-pads" },
      h("div", {}, h("h2", {}, "Mach deinen eigenen Beat."),
        h("p", {}, "Tippen oder Tasten A · S · D · F · G spielen. Original-Sounds, live synthetisiert.")),
      h("div", { class: "lab-pad-row" }, pads))),
    h("p", { class: "lab-foot" },
      "Performance-Modus: begrenzte Auflösung und Bildrate, um die eigentliche Musikproduktion nicht zu behindern. Audio läuft lokal im Browser.")));
  waehlen(spielzeug);
  cross.addEventListener("input", () => engine.setCrossfade(cross.value));
  const removeKeyboard = (event) => {
    if (event.repeat || event.ctrlKey || event.metaKey || event.altKey ||
        /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName || "")) return;
    const keys = { a:0, s:1, d:2, f:3, g:4 };
    const idx = keys[event.key?.toLowerCase()];
    if (idx !== undefined && spielzeug === "pult") { event.preventDefault(); pads[idx].click(); }
  };
  window.addEventListener("keydown", removeKeyboard);
  // Bestehenden Sirens-Player nicht gleichzeitig überlagern.
  document.getElementById("player-audio")?.pause();
  const stopVisual = visualisieren(canvas, hud, () => engine.analyser, () => modus,
    () => visualGpuDrosseln(produktionLaeuft, rtProfile));

  async function katalogLaden() {
    if (beendet) return;
    try {
      let daten = await api.katalog("", 1);
      if (beendet) return;
      if (daten.zustand === "laeuft" && !daten.anzahl_dateien) {
        katalogTimer = setTimeout(katalogLaden, 1800);
        return;
      }
      let liste = katalogEintraege(daten);
      if (!liste.length) {
        daten = await api.katalog();
        if (beendet) return;
        liste = katalogEintraege(daten);
      }
      for (const [index, select] of [deckA.select, deckB.select].entries()) {
        opt[index] = liste.slice(0, 400);
        for (const e of opt[index]) select.append(h("option", { value: e.pfad }, e.text));
        if (!liste.length) select.firstChild.textContent = "Keine Songs im Katalog – eigene Datei laden";
      }
    } catch (err) {
      if (!beendet) meldung("Katalog nicht verfügbar: Lokale Dateien funktionieren trotzdem.", "fehler");
    }
  }

  async function produktionsStand() {
    try {
      const d = await api.claude();
      if (!beendet) {
        produktionLaeuft = Boolean(d.laeuft);
        status.textContent = d.laeuft ? "● CLAUDE PRODUZIERT · ECO GPU" : "○ CLAUDE IM STANDBY";
      }
    } catch {
      if (!beendet) status.textContent = "○ STATUS OFFLINE";
    }
  }

  katalogLaden();
  produktionsStand();
  statusTimer = setInterval(() => { if (!document.hidden) produktionsStand(); }, 5000);
  return () => {
    beendet = true;
    clearTimeout(katalogTimer);
    clearInterval(statusTimer);
    window.removeEventListener("keydown", removeKeyboard);
    stopVisual();
    spielAnhalten();
    autoToy.destroy();
    kick.anhalten();
    stems.beenden();
    rt.destroy();
    engine.beenden();
  };
}
