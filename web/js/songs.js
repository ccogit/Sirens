// Songbibliothek mit Alben, gemeinsamen Singles und abspielbaren Fassungen.
import { api } from "./api.js";
import { h, leeren, meldung } from "./dom.js";
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

function songZeile(song, stil, auftraege, gewaehlt, tagWaehlen) {
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
  const tags = [...new Set((song.soundcloud || []).flatMap(info => info.tags || []))];
  return h("li", { class: "library-song" },
    h("span", { class: "library-song-art", "aria-hidden": "true" },
      cover ? h("img", { src: api.bildUrl(cover), alt: "", loading: "lazy" }) : "♫"),
    player, h("div", { class: "library-song-identity" }, titel,
      h("div", { class: "library-song-meta" },
        stil ? h("span", { class: "klein" }, "Stilreferenz " + stil) : null, status),
      tags.length ? h("div", { class: "library-tags" },
        tags.slice(0, 3).map(tag => h("button", { type: "button", title: "Nach " + tag + " filtern",
          onclick: () => tagWaehlen(tag) }, tag))) : null),
    fassung, aktionen);
}

const filterFelder = [
  ["typ", "Alben / Singles", ["Album", "Singles"]],
  ["stil", "Stilreferenz"],
  ["genre", "SoundCloud-Genre"],
  ["tags", "SoundCloud-Tag"],
  ["format", "Dateiformat"],
  ["wertung", "Bewertung", ["Positiv", "Bewertet", "Ohne Bewertung"]],
  ["sc", "SoundCloud", ["Öffentlich zugeordnet", "Ohne Zuordnung"]],
  ["cover", "Songcover", ["Mit Cover", "Ohne Cover"]],
];

function songMerkmale(release, song) {
  const soundcloud = song.soundcloud || [];
  const scores = song.dateien.map(d => d.bewertung?.score).filter(score => score != null);
  return {
    typ: [release.single ? "Singles" : "Album"],
    stil: release.stilreferenz ? [release.stilreferenz] : [],
    genre: [...new Set(soundcloud.map(info => info.genre).filter(Boolean))],
    tags: [...new Set(soundcloud.flatMap(info => info.tags || []))],
    format: [...new Set(song.dateien.map(d => d.pfad.split(".").pop().toUpperCase()))],
    wertung: scores.length ? (scores.some(score => score > 0) ? ["Positiv", "Bewertet"] : ["Bewertet"]) : ["Ohne Bewertung"],
    sc: [soundcloud.length ? "Öffentlich zugeordnet" : "Ohne Zuordnung"],
    cover: [song.cover ? "Mit Cover" : "Ohne Cover"],
  };
}

export function songsAnsicht(el) {
  let beendet = false;
  let katalog;
  let aktiv;
  let lauf = 0;
  let wartezeit;
  const auftraege = new Map();
  const fassungen = new Map();
  const suche = h("input", { type: "search", placeholder: "Bibliothek durchsuchen", "aria-label": "Bibliothek durchsuchen" });
  const filterStand = h("summary", {}, "Filter und Tags");
  const filterBox = h("details", { class: "library-filters" }, filterStand);
  const filter = Object.fromEntries(filterFelder.map(([name, titel]) => [name,
    h("select", { "aria-label": titel, onchange: zeichnen })]));
  filterBox.append(h("div", { class: "library-filter-grid" },
    filterFelder.map(([name, titel]) => h("label", {}, titel, filter[name]))),
    h("p", { class: "klein" }, "SoundCloud-Merkmale sind nur bei zugeordneten Songs verfügbar."),
    h("button", { type: "button", class: "schlicht", onclick: () => {
      for (const feld of Object.values(filter)) feld.value = "";
      zeichnen();
    } }, "Filter zurücksetzen"));
  function tagWaehlen(tag) {
    filterBox.open = true;
    filter.tags.value = tag;
    zeichnen();
  }
  const stand = h("p", { class: "klein library-catalog-status", "aria-live": "polite" });
  const navigation = h("nav", { class: "library-navigation", "aria-label": "Alben und Singles" });
  const inhalt = h("section", { class: "library-detail", "aria-label": "Titelliste" });
  const gruppierung = h("select", { "aria-label": "Singles gruppieren", onchange: () => {
    gruppe.value = "";
    detailZeichnen();
    gruppierung.focus();
  } }, h("option", { value: "alphabet" }, "Alphabetisch"), h("option", { value: "stil" }, "Nach Stilreferenz"));
  const gruppe = h("select", { "aria-label": "Single-Gruppe auswählen", onchange: () => { detailZeichnen(); gruppe.focus(); } });

  function auswahl() {
    const worte = suche.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const aktivFilter = Object.entries(filter).filter(([, feld]) => feld.value);
    const releases = (katalog?.releases || []).flatMap(release => {
      const basis = [release.titel, release.stilreferenz].join(" ").toLowerCase();
      const songs = release.songs.filter(song => {
        const merkmale = songMerkmale(release, song);
        const text = [basis, song.titel, ...merkmale.tags, ...merkmale.genre].join(" ").toLowerCase();
        return worte.every(wort => text.includes(wort)) &&
          aktivFilter.every(([name, feld]) => merkmale[name].includes(feld.value));
      });
      const leerPassend = !release.songs.length && worte.every(wort => basis.includes(wort)) &&
        !aktivFilter.length;
      return songs.length || leerPassend ? [{ ...release, songs }] : [];
    });
    const alben = releases.filter(release => !release.single);
    const singles = releases.filter(release => release.single)
      .flatMap(release => release.songs.map(song => ({ song, stil: release.stilreferenz })))
      .sort((a, b) => a.song.titel.localeCompare(b.song.titel, "de"));
    return { alben, singles };
  }

  function detailZeichnen() {
    const { alben, singles } = auswahl();
    const album = alben.find(eintrag => eintrag.pfad === aktiv);
    leeren(inhalt);
    if (!album && aktiv !== "Singles") return;
    const istSingles = !album;
    const titel = album?.titel || "Singles";
    const stil = album?.stilreferenz;
    const songs = album ? album.songs.map(song => ({ song, stil: "" })) : singles;
    const kopf = h("header", { class: "library-release-header" },
      album?.cover ? h("img", { src: api.bildUrl(album.cover), alt: "" }) : null,
      h("div", {}, h("h2", {}, titel),
        h("p", { class: "klein" }, [stil && "Stilreferenz " + stil, songs.length + (songs.length === 1 ? " Song" : " Songs")]
          .filter(Boolean).join(" · "))));
    let sichtbar = songs;
    if (istSingles) {
      const schluessel = ({ song, stil }) => gruppierung.value === "stil" ? stil || "Ohne Stilreferenz"
        : song.titel.normalize("NFD").replace(/\p{M}/gu, "").toUpperCase().match(/^[A-Z]/)?.[0] || "#";
      const gruppen = [...new Set(songs.map(schluessel))].sort((a, b) => a.localeCompare(b, "de"));
      const bisher = gruppe.value;
      gruppe.replaceChildren(h("option", { value: "" }, "Alle Singles"),
        ...gruppen.map(name => h("option", { value: name }, name)));
      gruppe.value = gruppen.includes(bisher) ? bisher : "";
      if (gruppe.value) sichtbar = songs.filter(song => schluessel(song) === gruppe.value);
      kopf.append(h("div", { class: "library-single-controls" }, gruppierung, gruppe));
    }
    inhalt.append(kopf, sichtbar.length ? h("ul", { class: "library-song-list" },
      sichtbar.map(({ song, stil }) => songZeile(song, stil, auftraege, fassungen, tagWaehlen)))
      : h("p", { class: "library-album-empty klein" }, "In diesem Albumordner liegt keine Audiodatei."));
    knoepfeAktualisieren();
  }

  function navigationAktualisieren() {
    for (const knopf of navigation.querySelectorAll("button")) {
      if (knopf.dataset.release === aktiv) knopf.setAttribute("aria-current", "true");
      else knopf.removeAttribute("aria-current");
    }
  }

  function navigationZeile(id, titel, anzahl, cover) {
    return h("button", { type: "button", "data-release": id, onclick: () => {
      aktiv = id;
      navigationAktualisieren();
      detailZeichnen();
    } }, cover ? h("img", { src: api.bildUrl(cover), alt: "", loading: "lazy" })
      : h("span", { class: "library-navigation-art", "aria-hidden": "true" }, "♫"),
    h("span", { class: "library-navigation-name" }, titel), h("span", { class: "klein" }, String(anzahl)));
  }

  function filterFuellen() {
    const merkmale = (katalog.releases || []).flatMap(release =>
      release.songs.map(song => songMerkmale(release, song)));
    for (const [name, titel, werte] of filterFelder) {
      const anzahl = new Map();
      for (const song of merkmale)
        for (const wert of song[name]) anzahl.set(wert, (anzahl.get(wert) || 0) + 1);
      const sortiert = werte || [...anzahl.keys()].sort((a, b) => a.localeCompare(b, "de"));
      const vorher = filter[name].value;
      filter[name].replaceChildren(h("option", { value: "" }, "Alle"),
        ...sortiert.filter(wert => anzahl.has(wert)).map(wert =>
          h("option", { value: wert }, wert + " (" + anzahl.get(wert) + ")")));
      filter[name].value = anzahl.has(vorher) ? vorher : "";
    }
  }

  function zeichnen() {
    if (!katalog) return;
    const filterAnzahl = Object.values(filter).filter(feld => feld.value).length;
    filterStand.textContent = "Filter und Tags" + (filterAnzahl ? " · " + filterAnzahl + " aktiv" : "");
    const { alben, singles } = auswahl();
    if (!alben.some(album => album.pfad === aktiv) && !(aktiv === "Singles" && singles.length))
      aktiv = alben.find(album => album.songs.length)?.pfad || alben[0]?.pfad || (singles.length ? "Singles" : null);
    stand.textContent = katalog.meldung || (katalog.zustand !== "bereit" ? "Der Musikordner wird gelesen …"
      : !alben.length && !singles.length ? "Keine passenden Songs oder Alben gefunden."
      : alben.length + " Alben · " + singles.length + " Singles");
    leeren(navigation).append(
      singles.length ? navigationZeile("Singles", "Singles", singles.length) : h("span", { hidden: true }),
      ...alben.map(album => navigationZeile(album.pfad, album.titel, album.songs.length, album.cover)));
    navigationAktualisieren();
    detailZeichnen();
  }

  async function laden() {
    clearTimeout(wartezeit);
    const nummer = ++lauf;
    try {
      const daten = await api.katalog();
      if (beendet || nummer !== lauf) return;
      katalog = daten;
      filterFuellen();
      zeichnen();
      if (daten.zustand === "leer" || daten.zustand === "laeuft") wartezeit = setTimeout(laden, 700);
    } catch (fehler) {
      if (!beendet && nummer === lauf) stand.textContent = fehler.meldung;
    }
  }

  suche.addEventListener("input", zeichnen);
  const aktualisieren = h("button", { type: "button", class: "klein-knopf", onclick: async () => {
    try { await api.katalogNeuLesen(); await laden(); }
    catch (fehler) { if (!beendet) stand.textContent = fehler.meldung; }
  } }, "Neu einlesen");
  el.append(h("div", { class: "songs-library" },
    h("header", { class: "library-header" }, h("h1", {}, "Songbibliothek"),
      h("a", { class: "knopf", href: "#/mastern" }, "Vorhandenen Song bearbeiten")),
    h("div", { class: "library-desktop" },
      h("aside", { class: "library-sidebar" }, h("div", { class: "library-toolbar" }, suche, aktualisieren), filterBox, stand, navigation),
      inhalt)));
  laden();
  api.liste().then(daten => {
    if (beendet) return;
    for (const auftrag of daten.auftraege) {
      for (const song of auftrag.songs || []) {
        if (!auftraege.has(song.pfad)) auftraege.set(song.pfad, { auftrag, song });
      }
    }
    detailZeichnen();
  }).catch(() => {});
  return () => { beendet = true; clearTimeout(wartezeit); };
}
