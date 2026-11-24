// Songbibliothek mit Alben, gemeinsamen Singles und abspielbaren Fassungen.
import { api } from "./api.js";
import { h, leeren, meldung, neueId } from "./dom.js";
import { abspielKnopf, knoepfeAktualisieren } from "./player.js";

function auftragOeffnen(datei, treffer, mastern = false) {
  const { auftrag, song } = treffer;
  const starten = song.bearbeitbar && song.waehlbar;
  return h("button", { type: "button", class: "klein-knopf", onclick: async (e) => {
    const taste = e.currentTarget;
    taste.disabled = true;
    try {
      const frisch = await api.lesen(auftrag.id);
      const schonOffen = frisch.status === "nachlauf" && frisch.nachlauf?.favorit === datei.pfad;
      if (starten && !schonOffen) await api.aktion(auftrag.id, "nachlauf", frisch.revision, { pfad: datei.pfad });
      location.hash = "#/auftrag/" + auftrag.id + (mastern ? "/mastering" : "");
    } catch (fehler) {
      meldung(fehler.meldung, "fehler");
      taste.disabled = false;
    }
  } }, mastern ? "Neu mastern" : starten ? "Bearbeiten" : "Auftrag öffnen");
}

function fassungsname(datei) {
  return [datei.version == null ? "Originaldatei" : "Version " + datei.version,
    datei.fassung, datei.pfad.split(".").pop().toUpperCase(), datei.unterordner].filter(Boolean).join(" · ");
}

function masterKnopf(datei) {
  return h("button", { type: "button", class: "klein-knopf", onclick: async (e) => {
    const taste = e.currentTarget;
    taste.disabled = true;
    try {
      const auftrag = await api.mastern(datei.pfad, ["mastering"]);
      location.hash = "#/auftrag/" + auftrag.id + "/mastering";
    } catch (fehler) {
      meldung(fehler.meldung, "fehler");
      taste.disabled = false;
    }
  } }, "Mastern");
}

function songZeile(song, stil, auftraege, gewaehlt) {
  const cover = song.cover || song.dateien.map(d => auftraege.get(d.pfad)?.song.cover).find(Boolean);
  const titel = h("strong", {}, song.titel);
  const status = h("span", { class: "klein library-song-status", "aria-live": "polite" });
  const player = h("div", { class: "library-song-play" });
  const aktionen = h("div", { class: "library-song-actions" });
  const id = song.dateien[0].pfad;
  const auswahl = song.dateien.length > 1 ? h("select", {
    "aria-label": "Fassung für " + song.titel,
    onchange: () => {
      gewaehlt.set(id, song.dateien[Number(auswahl.value)].pfad);
      fassungZeigen();
    },
  }, song.dateien.map((datei, index) => h("option", { value: String(index) }, fassungsname(datei)))) : null;
  if (auswahl) {
    const index = song.dateien.findIndex(datei => datei.pfad === gewaehlt.get(id));
    auswahl.value = String(Math.max(0, index));
  }
  const fassung = h("div", { class: "library-song-version" }, auswahl ||
    h("span", { class: "klein" }, fassungsname(song.dateien[0])));

  function fassungZeigen() {
    const datei = song.dateien[Number(auswahl?.value || 0)];
    const treffer = auftraege.get(datei.pfad);
    const knopf = abspielKnopf(datei.pfad);
    knopf.dataset.name = song.titel + ", " + fassungsname(datei);
    knopf.setAttribute("aria-label", "Anhören: " + knopf.dataset.name);
    player.replaceChildren(knopf);
    if (auswahl) auswahl.title = fassungsname(datei);
    status.textContent = treffer?.song.sync_offen ? "SoundCloud-Update offen"
      : treffer?.song.soundcloud ? "Auf SoundCloud" : "";
    status.hidden = !status.textContent;
    aktionen.replaceChildren(treffer ? auftragOeffnen(datei, treffer) : masterKnopf(datei));
    if (treffer?.song.bearbeitbar && treffer.song.waehlbar) aktionen.append(auftragOeffnen(datei, treffer, true));
    if (player.isConnected) knoepfeAktualisieren();
  }
  fassungZeigen();
  return h("li", { class: "library-song" },
    h("span", { class: "library-song-art", "aria-hidden": "true" },
      cover ? h("img", { src: api.bildUrl(cover), alt: "", loading: "lazy" }) : "♫"),
    player, h("div", { class: "library-song-identity" }, titel,
      h("div", { class: "library-song-meta" },
        stil ? h("span", { class: "klein" }, "Stilreferenz " + stil) : null, status)),
    fassung, aktionen);
}

export function songsAnsicht(el) {
  let beendet = false;
  let katalog = null;
  const auftraege = new Map();
  const fassungen = new Map();
  let lauf = 0;
  let wartezeit;
  const suchId = neueId();
  const suche = h("input", { id: suchId, type: "search", placeholder: "Song, Album oder Stilreferenz" });
  const gruppierung = h("select", { id: neueId(), onchange: () => zeichnen() },
    h("option", { value: "alphabet" }, "Alphabetisch"),
    h("option", { value: "stil" }, "Nach Stilreferenz"));
  const stand = h("p", { class: "klein library-catalog-status", "aria-live": "polite" });
  const inhalt = h("div", { class: "library-groups" });
  const geoeffnet = new Set();

  function gruppe(id, titel, anzahl, stil, render, offen, cover = null) {
    const body = h("ul", { class: "library-song-list" });
    const details = h("details", { class: "library-group", open: offen || geoeffnet.has(id) },
      h("summary", {}, cover ? h("img", { class: "library-album-cover", src: api.bildUrl(cover), alt: "", loading: "lazy" }) : null,
        h("span", {}, titel), stil ? h("span", { class: "klein" }, "Stilreferenz " + stil) : null,
        h("span", { class: "mini-count" }, String(anzahl))), body);
    const fuellen = () => { if (!body.childElementCount) body.append(...render()); knoepfeAktualisieren(); };
    details.addEventListener("toggle", () => {
      if (!details.isConnected) return;
      if (details.open) { geoeffnet.add(id); fuellen(); } else geoeffnet.delete(id);
    });
    if (details.open) fuellen();
    return details;
  }

  function singlesCluster(singles, gesucht) {
    const clusters = new Map();
    const nachStil = gruppierung.value === "stil";
    for (const eintrag of singles) {
      const anfang = eintrag.song.titel.normalize("NFD").replace(/\p{M}/gu, "").charAt(0).toUpperCase();
      const titel = nachStil ? (eintrag.stil || "Ohne Stilreferenz") : (/^[A-Z]$/.test(anfang) ? anfang : "#");
      if (!clusters.has(titel)) clusters.set(titel, []);
      clusters.get(titel).push(eintrag);
    }
    return [...clusters].sort(([a], [b]) => a.localeCompare(b, "de")).map(([titel, eintraege]) =>
      h("li", {}, gruppe("single:" + gruppierung.value + ":" + titel, titel, eintraege.length, "",
        () => eintraege.map(({ song, stil }) => songZeile(song, stil, auftraege, fassungen)), gesucht)));
  }

  function zeichnen() {
    if (!katalog) return;
    leeren(inhalt);
    const releases = katalog.releases || [];
    const singles = releases.filter(r => r.single).flatMap(r => r.songs.map(song => ({ song, stil: r.stilreferenz })))
      .sort((a, b) => a.song.titel.localeCompare(b.song.titel, "de"));
    const alben = releases.filter(r => !r.single);
    const sonst = alben.reduce((zahl, r) => zahl + r.songs.length, 0);
    const gesucht = Boolean(suche.value.trim());
    stand.textContent = katalog.meldung || (katalog.zustand !== "bereit" ? "Der Musikordner wird gelesen …"
      : singles.length + sonst + alben.length
        ? (singles.length + sonst) + " Songs · " + alben.length + " Alben"
        : gesucht ? "Keine passenden Songs gefunden." : "Der Musikordner enthält keine Songs.");
    for (const album of alben) {
      inhalt.append(gruppe(album.pfad, album.titel, album.songs.length, album.stilreferenz,
        () => album.songs.length ? album.songs.map(s => songZeile(s, "", auftraege, fassungen))
          : [h("li", { class: "library-album-empty klein" }, "In diesem Albumordner liegt derzeit keine Audiodatei.")],
        gesucht && releases.length < 8, album.cover));
    }
    if (singles.length) inhalt.append(gruppe("Singles", "Singles", singles.length, "",
      () => [h("li", { class: "library-single-grouper" },
        h("label", { for: gruppierung.id }, "Singles gruppieren"), gruppierung),
        ...singlesCluster(singles, gesucht)], gesucht || !alben.length));
    knoepfeAktualisieren();
  }

  async function laden() {
    clearTimeout(wartezeit);
    const nummer = ++lauf;
    try {
      const daten = await api.katalog(suche.value.trim());
      if (beendet || nummer !== lauf) return;
      katalog = daten;
      zeichnen();
      if (daten.zustand === "leer" || daten.zustand === "laeuft") wartezeit = setTimeout(laden, 700);
    } catch (fehler) {
      if (!beendet && nummer === lauf) stand.textContent = fehler.meldung;
    }
  }

  suche.addEventListener("input", () => {
    clearTimeout(wartezeit);
    ++lauf;
    wartezeit = setTimeout(laden, 200);
  });
  const aktualisieren = h("button", { type: "button", class: "library-toggle", onclick: async () => {
    try { await api.katalogNeuLesen(); await laden(); }
    catch (fehler) { if (!beendet) stand.textContent = fehler.meldung; }
  } }, "Neu einlesen");
  el.append(h("div", { class: "songs-library" },
    h("header", { class: "library-header" }, h("h1", {}, "Songbibliothek"),
      h("a", { class: "knopf", href: "#/mastern" }, "Vorhandenen Song bearbeiten")),
    h("section", { class: "library-panel" },
      h("div", { class: "library-toolbar" }, h("label", { for: suchId }, "Suchen"), suche, aktualisieren),
      stand, inhalt)));
  laden();
  api.liste().then(daten => {
    if (beendet) return;
    for (const auftrag of daten.auftraege) {
      for (const song of auftrag.songs || []) {
        if (!auftraege.has(song.pfad)) auftraege.set(song.pfad, { auftrag, song });
      }
    }
    zeichnen();
  }).catch(() => {});
  return () => { beendet = true; clearTimeout(wartezeit); };
}
