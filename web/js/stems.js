// Stem Studio: KI-Trennung im Sirens-Dienst, danach samplegenaues Live-Mixing im Browser.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";
import { StemAudio } from "./stem_audio.js";
import { warpStage } from "./stem_visual.js";

const NAMEN = { vocals: "Gesang", drums: "Schlagzeug", bass: "Bass",
                other: "Übrige Instrumente", piano: "Klavier", guitar: "Gitarre" };
const SYMBOLE = { vocals: "🎤", drums: "🥁", bass: "🎸",
                  other: "🎹", piano: "🎹", guitar: "🎸" };

function zeit(sekunden) {
  return Number.isFinite(sekunden) ? Math.floor(sekunden / 60) + ":" +
    String(Math.floor(sekunden % 60)).padStart(2, "0") : "0:00";
}

export function stemSpiel(isProducing = () => false) {
  let beendet = false, token = 0, timer = null, takt = null, engine = null;
  let spuren = [], solo = null;
  const song = h("select", { "aria-label": "Song für Stem Studio" },
    h("option", { value: "" }, "Songs werden geladen …"));
  const modell = h("select", { "aria-label": "KI-Trennmodell" },
    h("option", { value: "htdemucs" }, "4 Stems · Standard"),
    h("option", { value: "htdemucs_6s" }, "6 Stems · Gitarre & Klavier (experimentell)"));
  const geraet = h("select", { "aria-label": "Rechenmodus" },
    h("option", { value: "cpu" }, "CPU · GPU freihalten"),
    h("option", { value: "cuda" }, "RTX 5080 · CUDA"));
  const status = h("p", { class: "stems-status", role: "status", "aria-live": "polite" },
    "Song aus dem Katalog wählen.");
  const trennen = h("button", { class: "stems-primary", type: "button", disabled: true }, "KI-Trennung starten");
  const play = h("button", { class: "stems-primary", type: "button" }, "▶ Spielen");
  const position = h("input", { type: "range", min: "0", max: "1000", value: "0",
    "aria-label": "Position im Song" });
  const uhr = h("span", { class: "stems-clock" }, "0:00 / 0:00");
  const spurenEl = h("div", { class: "stems-tracks" });
  const alle = h("button", { type: "button", class: "lab-mode" }, "Alle Spuren an");
  const visOption = { modus: "live", dichte: 1, szene: 0 };
  const buehne = h("canvas", { class: "stems-visual-canvas",
    role: "img", "aria-label": "Live gerenderter audioreaktiver 3D-Tunnel mit Lichtskulpturen" });
  const metriken = h("span", { class: "stems-perf" }, "WebGL2 · GPU wird vorbereitet");
  const live = h("span", { class: "stems-visual-live" }, "DEMO · Visuelle Vorschau");
  const qualitaet = h("select", { "aria-label": "GPU-Performance-Profil" },
    h("option", { value: "eco" }, "Eco · 15 FPS"),
    h("option", { value: "live" }, "Live · 45 FPS"),
    h("option", { value: "ultra" }, "RTX Ultra · bis 4K / 160 Steps"));
  qualitaet.value = visOption.modus;
  qualitaet.addEventListener("change", () => { visOption.modus = qualitaet.value; });
  const dichte = h("input", { type: "range", min: "50", max: "150", value: "100",
    "aria-label": "3D-Renderdichte in Prozent" });
  const dichteWert = h("output", {}, "100 %");
  dichte.addEventListener("input", () => {
    visOption.dichte = Number(dichte.value) / 100;
    dichteWert.textContent = dichte.value + " %";
  });
  const szene = [["◈ Neon-Kathedrale",0],["⬡ Hypercube",1],["✺ Quantum Nebula",2]]
    .map(([name,id]) => h("button", { type: "button", class: "stems-scene",
      "aria-pressed": String(id === 0), onclick: () => {
        visOption.szene = id;
        for (const knopf of szene) knopf.setAttribute("aria-pressed", String(knopf.dataset.scene === String(id)));
      }, "data-scene": id }, name));
  const vollbild = h("button", { type: "button", class: "stems-fullscreen",
    onclick: () => { if (buehne.requestFullscreen) buehne.requestFullscreen().catch(() => {}); } }, "⛶ Vollbild");
  const visual = h("section", { class: "stems-visual" },
    h("div", { class: "stems-visual-title" },
      h("div", {}, h("span", { class: "stems-kicker" }, "WARP STAGE · RTX EXPERIMENT"),
        h("h2", {}, "Flieg durch deinen Song.")),
      vollbild),
    h("div", { class: "stems-visual-wrap" }, buehne,
      h("div", { class: "stems-visual-hud" }, live, metriken)),
    h("div", { class: "stems-scenes", role: "group", "aria-label": "3D-Welt auswählen" }, szene),
    h("div", { class: "stems-gpu-controls" },
      h("label", {}, "GPU-Profil", qualitaet),
      h("label", {}, "Renderdichte", h("span", {}, dichte, dichteWert))),
    h("p", { class: "stems-hint" },
      "RTX Ultra ist absichtlich anspruchsvoll. WebGL2 nutzt die vom Browser gewählte GPU; Auflösung und Bildrate sind auf 4K/60 FPS begrenzt. Während Claude produziert, wird automatisch Eco erzwungen."));

  const stopVisual = warpStage(buehne,
    () => engine?.laeuft ? engine.analyser : null,
    isProducing,
    () => buehne.closest(".lab-toy")?.hidden === false,
    visOption,
    (info) => {
      metriken.textContent = info.renderer + " · " + info.w + "×" + info.h +
        " · " + info.steps + " Steps · " + info.fps + " FPS" + (info.eco ? " · CLAUDE ECO" : "");
      live.textContent = info.demo ? "DEMO · Ohne Audio" : "LIVE · AUF DEINEN SONG";
      if (info.fehler) metriken.textContent = info.fehler;
    });

  const mixer = h("section", { class: "stems-mixer", hidden: true },
    h("div", { class: "stems-transport" }, play, uhr),
    position, h("div", { class: "stems-mix-head" }, h("h2", {}, "Instrumente live mischen"), alle),
    spurenEl);

  function aktualisieren() {
    if (!engine?.bereit) return;
    const t = engine.position(), dauer = engine.dauer;
    uhr.textContent = zeit(t) + " / " + zeit(dauer);
    if (dauer > 0) position.value = String(Math.round(t / dauer * 1000));
  }

  function pausieren() {
    engine?.pause();
    play.textContent = "▶ Spielen";
  }

  function stoppen() {
    pausieren();
    if (takt) clearInterval(takt);
    takt = null;
    engine?.beenden();
    engine = null;
    spuren = [];
    solo = null;
    mixer.hidden = true;
    position.value = "0";
    uhr.textContent = "0:00 / 0:00";
    leeren(spurenEl);
  }

  function mischen() {
    for (const [i, s] of spuren.entries()) {
      engine?.pegel(i, (!s.mute && (solo === null || solo === s.name)) ? s.pegel / 100 : 0);
      s.solo.setAttribute("aria-pressed", String(solo === s.name));
      s.muteButton.setAttribute("aria-pressed", String(s.mute));
      s.muteButton.textContent = s.mute ? "Stumm ✓" : "Stumm";
    }
  }

  async function bereit(stems, nummer) {
    stoppen();
    const player = new StemAudio();
    engine = player;
    trennen.hidden = true;
    status.textContent = "Lade Stems in den samplegenauen Mixer …";
    try {
      const urls = stems.map((name) => api.stemAudioUrl(song.value, modell.value, name));
      await player.laden(urls, (i, gesamt) => {
        if (!beendet && nummer === token) status.textContent = "Lade Spur " + i + " von " + gesamt + " …";
      });
      if (beendet || nummer !== token || engine !== player) return;
      for (const name of stems) {
        const wert = h("output", {}, "100 %");
        const pegel = h("input", { type: "range", min: "0", max: "100", value: "100",
          "aria-label": "Lautstärke " + (NAMEN[name] || name) });
        const muteButton = h("button", { type: "button", class: "stems-action", "aria-pressed": "false" }, "Stumm");
        const soloButton = h("button", { type: "button", class: "stems-action", "aria-pressed": "false" }, "Solo");
        const spur = { name, pegel: 100, mute: false, solo: soloButton, muteButton };
        pegel.addEventListener("input", () => { spur.pegel = Number(pegel.value); wert.textContent = pegel.value + " %"; mischen(); });
        muteButton.addEventListener("click", () => { spur.mute = !spur.mute; mischen(); });
        soloButton.addEventListener("click", () => { solo = solo === name ? null : name; mischen(); });
        spurenEl.append(h("div", { class: "stems-track" },
          h("span", { class: "stems-instrument" }, (SYMBOLE[name] || "♫") + " " + (NAMEN[name] || name)),
          pegel, wert, soloButton, muteButton));
        spuren.push(spur);
      }
      mixer.hidden = false;
      player.onEnde = () => { play.textContent = "▶ Spielen"; aktualisieren(); };
      mischen();
      takt = setInterval(aktualisieren, 120);
      aktualisieren();
      status.textContent = "Bereit. Alle Instrumente starten samplegenau auf derselben Zeitachse.";
    } catch (err) {
      if (!beendet && nummer === token) {
        status.textContent = "Die Stems konnten nicht geladen werden: " + (err.message || err);
        trennen.hidden = false;
        trennen.disabled = false;
        trennen.textContent = "Erneut versuchen";
      }
      if (engine === player) stoppen();
      else player.beenden();
    }
  }

  function zuruecksetzen() {
    token += 1;
    clearTimeout(timer);
    timer = null;
    stoppen();
    trennen.disabled = !song.value;
    trennen.hidden = false;
    trennen.textContent = "KI-Trennung starten";
    status.textContent = song.value ? "Prüfe, ob die Instrumente bereits vorliegen …" : "Bitte einen Song auswählen.";
  }

  async function pruefen(nummer) {
    if (beendet || !song.value) return;
    const pfad = song.value, model = modell.value;
    try {
      const daten = await api.stemStatus(pfad, model);
      if (beendet || nummer !== token) return;
      anzeigen(daten, nummer);
    } catch (err) {
      if (!beendet && nummer === token) {
        status.textContent = err.meldung || "Stem-Status konnte nicht geladen werden.";
        trennen.disabled = false;
      }
    }
  }

  function anzeigen(daten, nummer) {
    status.textContent = daten.meldung || "Status unbekannt.";
    if (daten.zustand === "bereit") {
      trennen.hidden = true;
      bereit(daten.stems, nummer);
    } else if (daten.zustand === "laeuft") {
      trennen.disabled = true;
      trennen.textContent = "KI arbeitet …";
      timer = setTimeout(() => pruefen(nummer), 1800);
    } else {
      trennen.hidden = false;
      trennen.disabled = false;
      trennen.textContent = daten.zustand === "fehler" ? "Erneut versuchen" : "KI-Trennung starten";
    }
  }

  function neueAuswahl() {
    zuruecksetzen();
    if (song.value) pruefen(token);
  }
  song.addEventListener("change", neueAuswahl);
  modell.addEventListener("change", neueAuswahl);
  trennen.addEventListener("click", async () => {
    if (!song.value || trennen.disabled) return;
    const nummer = token;
    trennen.disabled = true;
    status.textContent = "Starte lokale KI-Trennung …";
    try {
      const daten = await api.stemStart(song.value, modell.value, geraet.value);
      if (!beendet && nummer === token) anzeigen(daten, nummer);
    } catch (err) {
      if (!beendet && nummer === token) {
        status.textContent = err.meldung || "Trennung konnte nicht gestartet werden.";
        trennen.disabled = false;
      }
    }
  });
  play.addEventListener("click", async () => {
    if (!engine?.bereit) return;
    document.getElementById("player-audio")?.pause();
    try {
      await engine.schalten();
      play.textContent = engine.laeuft ? "❚❚ Pause" : "▶ Spielen";
      aktualisieren();
    } catch (err) {
      pausieren();
      status.textContent = "Audio konnte nicht gestartet werden: " + (err.message || err);
    }
  });
  position.addEventListener("input", () => {
    if (!engine?.bereit) return;
    engine.springen(Number(position.value) / 1000 * engine.dauer);
    aktualisieren();
  });
  alle.addEventListener("click", () => {
    solo = null;
    for (const s of spuren) { s.mute = false; s.pegel = 100; }
    for (const el of spurenEl.querySelectorAll('input[type="range"]')) el.value = "100";
    for (const el of spurenEl.querySelectorAll("output")) el.textContent = "100 %";
    mischen();
  });

  async function katalogLaden() {
    try {
      let daten = await api.katalog("", 1);
      if (beendet) return;
      if (daten.zustand === "laeuft" && !daten.anzahl_dateien) {
        timer = setTimeout(katalogLaden, 1800);
        return;
      }
      let liste = sammeln(daten);
      if (!liste.length) { daten = await api.katalog(); if (beendet) return; liste = sammeln(daten); }
      leeren(song);
      song.append(h("option", { value: "" }, "Song auswählen …"));
      for (const eintrag of liste.slice(0, 400)) song.append(h("option", { value: eintrag.pfad }, eintrag.text));
      status.textContent = liste.length ? "Wähle einen Song und starte die lokale KI-Trennung." :
        "Keine Songs gefunden. Bitte zuerst einen Titel im Musikkatalog bereitstellen.";
    } catch {
      if (!beendet) status.textContent = "Musikkatalog nicht verfügbar.";
    }
  }
  katalogLaden();

  return {
    el: h("div", { class: "stems-page" },
      h("section", { class: "stems-intro" },
        h("p", { class: "lab-eyebrow" }, "SIRENS · STEM STUDIO"),
        h("h2", {}, "Hör jedes Instrument einzeln."),
        h("p", {}, "Demucs trennt einen Song einmalig lokal. Danach lassen sich Gesang, Schlagzeug, Bass und Instrumente während des Abspielens live solo, stumm oder lauter schalten.")),
      visual,
      h("section", { class: "stems-setup" },
        h("label", {}, "Song aus deinem Katalog", song),
        h("label", {}, "Trennmodell", modell),
        h("label", {}, "Berechnung", geraet),
        trennen, status,
        h("p", { class: "stems-hint" }, "Keine Cloud-Uploads. Das Original bleibt unverändert. Standardmäßig läuft die Trennung auf der CPU. Für die RTX 5080 wähle CUDA (mit passender PyTorch-Version); während Claude arbeitet, ist CUDA gesperrt. Das 6-Stem-Modell ist bei Gitarre und Klavier experimentell.")),
      mixer),
    pausieren,
    beenden() {
      beendet = true;
      clearTimeout(timer);
      stopVisual();
      stoppen();
    },
  };
}

function sammeln(daten) {
  const liste = [];
  for (const artist of daten.artists || [])
    for (const release of artist.releases || [])
      for (const titel of release.songs || [])
        for (const datei of titel.dateien || [])
          liste.push({ pfad: datei.pfad, text: artist.slug + " · " + titel.titel +
            (datei.fassung ? " (" + datei.fassung + ")" : "") });
  return liste;
}
