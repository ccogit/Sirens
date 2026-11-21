// Stem Studio: ein Song wird vorab lokal mit Demucs getrennt, danach live im Browser gemischt.
// Mehrere Audioelemente bleiben anhand einer Masterspur synchron; keine externen Dienste.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";

const NAMEN = { vocals: "Gesang", drums: "Schlagzeug", bass: "Bass",
                other: "Übrige Instrumente", piano: "Klavier", guitar: "Gitarre" };
const SYMBOLE = { vocals: "🎤", drums: "🥁", bass: "🎸",
                  other: "🎹", piano: "🎹", guitar: "🎸" };

function zeit(sekunden) {
  return Number.isFinite(sekunden) ? Math.floor(sekunden / 60) + ":" +
    String(Math.floor(sekunden % 60)).padStart(2, "0") : "0:00";
}

export function stemSpiel() {
  let beendet = false, token = 0, timer = null, takt = null, spuren = [], solo = null;
  const song = h("select", { "aria-label": "Song für Stem Studio" },
    h("option", { value: "" }, "Songs werden geladen …"));
  const modell = h("select", { "aria-label": "KI-Trennmodell" },
    h("option", { value: "htdemucs" }, "4 Stems · Standard"),
    h("option", { value: "htdemucs_6s" }, "6 Stems · auch Gitarre & Klavier (experimentell)"));
  const status = h("p", { class: "stems-status", role: "status", "aria-live": "polite" },
    "Song aus dem Katalog wählen.");
  const trennen = h("button", { class: "stems-primary", type: "button", disabled: true }, "KI-Trennung starten");
  const play = h("button", { class: "stems-primary", type: "button" }, "▶ Spielen");
  const position = h("input", { type: "range", min: "0", max: "1000", value: "0",
    "aria-label": "Position im Song" });
  const uhr = h("span", { class: "stems-clock" }, "0:00 / 0:00");
  const spurenEl = h("div", { class: "stems-tracks" });
  const alle = h("button", { type: "button", class: "lab-mode" }, "Alle Spuren an");
  const mixer = h("section", { class: "stems-mixer", hidden: true },
    h("div", { class: "stems-transport" }, play, uhr),
    position, h("div", { class: "stems-mix-head" }, h("h2", {}, "Instrumente live mischen"), alle),
    spurenEl);

  function pausieren() {
    for (const s of spuren) s.audio.pause();
    play.textContent = "▶ Spielen";
  }

  function stoppen() {
    pausieren();
    if (takt) clearInterval(takt);
    takt = null;
    for (const s of spuren) {
      s.audio.removeAttribute("src");
      s.audio.load();
    }
    spuren = [];
    solo = null;
    mixer.hidden = true;
    position.value = "0";
    uhr.textContent = "0:00 / 0:00";
    leeren(spurenEl);
  }

  function mischen() {
    for (const s of spuren) {
      s.audio.volume = (!s.mute && (solo === null || solo === s.name)) ? s.pegel / 100 : 0;
      s.solo.setAttribute("aria-pressed", String(solo === s.name));
      s.muteButton.setAttribute("aria-pressed", String(s.mute));
      s.muteButton.textContent = s.mute ? "Stumm ✓" : "Stumm";
    }
  }

  function sync() {
    if (!spuren.length) return;
    const master = spuren[0].audio;
    const dauer = master.duration;
    uhr.textContent = zeit(master.currentTime) + " / " + zeit(dauer);
    if (Number.isFinite(dauer) && dauer > 0) position.value = String(Math.round(master.currentTime / dauer * 1000));
    if (master.paused) return;
    for (const s of spuren.slice(1)) {
      if (s.audio.readyState >= 1 && Math.abs(s.audio.currentTime - master.currentTime) > 0.12) {
        s.audio.currentTime = master.currentTime;
      }
    }
  }

  function bereit(stems) {
    stoppen();
    for (const name of stems) {
      const audio = new Audio(api.stemAudioUrl(song.value, modell.value, name));
      audio.preload = "auto";
      const wert = h("output", {}, "100 %");
      const pegel = h("input", { type: "range", min: "0", max: "100", value: "100",
        "aria-label": "Lautstärke " + (NAMEN[name] || name) });
      const muteButton = h("button", { type: "button", class: "stems-action", "aria-pressed": "false" }, "Stumm");
      const soloButton = h("button", { type: "button", class: "stems-action", "aria-pressed": "false" }, "Solo");
      const spur = { name, audio, pegel: 100, mute: false, solo: soloButton, muteButton };
      pegel.addEventListener("input", () => { spur.pegel = Number(pegel.value); wert.textContent = pegel.value + " %"; mischen(); });
      muteButton.addEventListener("click", () => { spur.mute = !spur.mute; mischen(); });
      soloButton.addEventListener("click", () => { solo = solo === name ? null : name; mischen(); });
      spurenEl.append(h("div", { class: "stems-track" },
        h("span", { class: "stems-instrument" }, (SYMBOLE[name] || "♫") + " " + (NAMEN[name] || name)),
        pegel, wert, soloButton, muteButton));
      spuren.push(spur);
    }
    const master = spuren[0]?.audio;
    if (master) {
      master.addEventListener("ended", pausieren);
      master.addEventListener("timeupdate", sync);
      master.addEventListener("loadedmetadata", sync);
    }
    mixer.hidden = false;
    mischen();
    takt = setInterval(sync, 250);
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
      bereit(daten.stems);
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
      const daten = await api.stemStart(song.value, modell.value);
      if (!beendet && nummer === token) anzeigen(daten, nummer);
    } catch (err) {
      if (!beendet && nummer === token) {
        status.textContent = err.meldung || "Trennung konnte nicht gestartet werden.";
        trennen.disabled = false;
      }
    }
  });
  play.addEventListener("click", async () => {
    if (!spuren.length) return;
    if (!spuren[0].audio.paused) { pausieren(); return; }
    document.getElementById("player-audio")?.pause();
    try {
      await Promise.all(spuren.map((s) => s.audio.play()));
      sync();
      play.textContent = "❚❚ Pause";
    } catch {
      pausieren();
      status.textContent = "Ein Stem konnte nicht abgespielt werden. Bitte Browserformat und Datei prüfen.";
    }
  });
  position.addEventListener("input", () => {
    const dauer = spuren[0]?.audio.duration;
    if (!Number.isFinite(dauer) || dauer <= 0) return;
    const ziel = Number(position.value) / 1000 * dauer;
    for (const s of spuren) s.audio.currentTime = ziel;
    sync();
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
      const daten = await api.katalog("", 1);
      if (beendet) return;
      if (daten.zustand === "laeuft" && !daten.anzahl_dateien) {
        timer = setTimeout(katalogLaden, 1800);
        return;
      }
      let liste = [];
      for (const artist of daten.artists || [])
        for (const release of artist.releases || [])
          for (const titel of release.songs || [])
            for (const datei of titel.dateien || [])
              liste.push({ pfad: datei.pfad, text: artist.slug + " · " + titel.titel +
                (datei.fassung ? " (" + datei.fassung + ")" : "") });
      if (!liste.length) {
        const alle = await api.katalog();
        if (beendet) return;
        for (const artist of alle.artists || [])
          for (const release of artist.releases || [])
            for (const titel of release.songs || [])
              for (const datei of titel.dateien || [])
                liste.push({ pfad: datei.pfad, text: artist.slug + " · " + titel.titel });
      }
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
      h("section", { class: "stems-setup" },
        h("label", {}, "Song aus deinem Katalog", song),
        h("label", {}, "Trennmodell", modell),
        trennen, status,
        h("p", { class: "stems-hint" }, "Keine Cloud-Uploads. Original bleibt unverändert. Die Trennung dauert je nach Rechner einige Minuten und verwendet standardmäßig nur die CPU. Das 6-Stem-Modell ist bei Gitarre und Klavier experimentell.")),
      mixer),
    pausieren,
    beenden() {
      beendet = true;
      clearTimeout(timer);
      stoppen();
    },
  };
}
