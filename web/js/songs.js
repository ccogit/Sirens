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

function beschreibung(text, klasse, leer) {
  if (!text) return h("p", { class: "klein library-no-description" }, leer);
  return h("section", { class: klasse, "aria-label": "Albumbeschreibung" },
    h("div", { class: "library-description-text" },
      text.split(/\n\n+/).map(absatz => h("p", {}, absatz))));
}

function albumEigenschaften(album) {
  const profile = album.songs.map(song => song.kurzprofil).filter(Boolean);
  const formate = [...new Set(profile.flatMap(p => p.formate))].sort();
  const tempo = profile.map(p => p.tempo_bpm).filter(Number.isFinite).sort((a, b) => a - b);
  const genres = [...new Set(profile.flatMap(p => p.soundcloud_genres))];
  const tags = new Map();
  for (const p of profile)
    for (const tag of p.soundcloud_tags) tags.set(tag, (tags.get(tag) || 0) + 1);
  const haeufigeTags = [...tags].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "de"))
    .slice(0, 5).map(([tag]) => tag);
  const vonBis = tempo.length && tempo[0] !== tempo.at(-1) ? tempo[0] + "–" + tempo.at(-1) : tempo[0];
  const felder = [
    ["Stilreferenz", album.stilreferenz],
    ["Lokaler Bestand", album.songs.length + " Songs · " + profile.reduce((summe, p) => summe + p.fassungen, 0) + " Fassungen"],
    ["Audioformate", formate.join(", ")],
    ["Lyrics lokal", profile.length ? profile.filter(p => p.lyrics_lokal).length + " von " + profile.length + " Songs" : ""],
    ["SoundCloud", profile.length ? profile.filter(p => p.soundcloud_status === "Öffentlich zugeordnet").length +
      " von " + profile.length + " Songs öffentlich zugeordnet" : ""],
    ["Belegtes Tempo", tempo.length ? vonBis + " BPM · " + tempo.length + " Songs" : ""],
    ["SoundCloud-Genres", genres.join(", ")],
    ["Häufigste Tags", haeufigeTags.join(", ")],
  ];
  return h("aside", { class: "library-album-facts", "aria-label": "Albumeigenschaften" },
    h("h3", {}, "Albumeigenschaften"),
    h("dl", {}, felder.filter(([, wert]) => wert).map(([name, wert]) =>
      h("div", {}, h("dt", {}, name), h("dd", {}, wert)))));
}

function profilAnsicht(profil, details, tagWaehlen) {
  if (!profil) return beschreibung(details, "library-track-description", "Keine Songbeschreibung hinterlegt");
  const felder = [
    ["Stilreferenz", profil.stilreferenz],
    ["Tempo", profil.tempo_bpm ? profil.tempo_bpm + " BPM" : null],
    ["SoundCloud-Genre", profil.soundcloud_genres.join(", ")],
    ["Fassungen", profil.fassungen + " · " + profil.formate.join(", ")],
    ["Lyrics", profil.lyrics_lokal ? "Lokal vorhanden" : null],
    ["Bewertung", profil.beste_bewertung],
  ].filter(([, wert]) => wert != null && wert !== "");
  return h("details", { class: "library-description library-track-description" },
    h("summary", {}, h("span", {}, details ? profil.beschreibung : "Songinfo")),
    h("div", { class: "library-profile-content" },
      h("p", {}, details || profil.beschreibung),
      h("div", { class: "library-profile-facts" },
        h("dl", { class: "library-profile" }, felder.map(([name, wert]) =>
          h("div", {}, h("dt", {}, name), h("dd", {}, wert)))),
        profil.soundcloud_tags.length ? h("div", { class: "library-tags" },
          profil.soundcloud_tags.map(tag => h("button", { type: "button", onclick: () => tagWaehlen(tag) }, tag))) : null)));
}

function soundcloudSymbol(song) {
  const tracks = song.soundcloud || [];
  if (!tracks.length) return null;
  const öffentlich = tracks.filter(track => track.sharing !== "private");
  const bezeichnung = öffentlich.length ? "Öffentlich auf SoundCloud" : "Privat auf SoundCloud";
  const link = öffentlich.length === 1 && /^https:\/\/soundcloud\.com\//i.test(öffentlich[0].url || "");
  const attrs = { class: "library-sc-symbol" + (öffentlich.length ? "" : " privat"), title: bezeichnung,
    "aria-label": bezeichnung };
  return link ? h("a", { ...attrs, href: öffentlich[0].url, target: "_blank", rel: "noopener noreferrer" }, "☁")
    : h("span", { ...attrs, role: "img" }, "☁");
}

const scZaehler = [
  ["playback_count", "Plays", "▶"], ["likes_count", "Likes", "♥"], ["reposts_count", "Reposts", "↻"],
  ["comment_count", "Kommentare", "▤"], ["download_count", "Downloads", "↓"],
];
const zahlenformat = new Intl.NumberFormat("de-DE");
const datumsformat = new Intl.DateTimeFormat("de-DE", { dateStyle: "medium", timeStyle: "short" });

function soundcloudZahlen(song) {
  const tracks = (song.soundcloud || []).filter(track => track.zahlen &&
    scZaehler.some(([key]) => Number.isFinite(track.zahlen[key])));
  if (!tracks.length) return null;
  const zeile = track => {
    const datum = new Date(track.zahlenstand || "");
    const stand = Number.isFinite(datum.getTime()) ? "Stand " + datumsformat.format(datum) : "";
    return h("div", { class: "library-sc-numbers", title: stand },
      tracks.length > 1 ? h("span", { class: "library-sc-track-name" }, track.title) : null,
      ...scZaehler.map(([key, label, symbol]) => {
        if (!Number.isFinite(track.zahlen[key])) return h("span", {
          class: "library-sc-unavailable", "aria-label": label + ": Kein Messwert" }, "–");
        const zahl = zahlenformat.format(track.zahlen[key]);
        const rang = track.rang?.[key];
        const vergleich = Number.isFinite(rang) ? "Katalogvergleich: " + rang + " von 100" : "";
        const balken = vergleich ? h("meter", { class: "library-sc-meter " + key,
          min: 0, max: 100, value: String(rang), "aria-label": label + " im Katalogvergleich" }) : null;
        return h("span", { class: "library-sc-metric" + (track.zahlen[key] === 0 ? " leer" : ""),
          title: [zahl + " " + label, vergleich, stand].filter(Boolean).join(" · ") },
        h("span", { class: "library-sc-glyph " + key, "aria-hidden": "true" }, symbol),
        h("strong", { "aria-label": zahl + " " + label }, zahl), balken);
      }));
  };
  if (tracks.length === 1) return zeile(tracks[0]);
  return h("details", { class: "library-sc-versions" }, h("summary", {}, "SoundCloud-Zahlen · " + tracks.length + " Tracks"),
    tracks.map(zeile));
}

function songZeile(song, albumCover, auftraege, gewaehlt, tagWaehlen) {
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
    cover && cover !== albumCover ? h("img", { class: "library-song-art", src: api.bildUrl(cover), alt: "", loading: "lazy" }) : player,
    cover && cover !== albumCover ? player : null,
    h("div", { class: "library-song-identity" }, h("div", { class: "library-song-heading" },
      titel, soundcloudSymbol(song), status)),
    profilAnsicht(song.kurzprofil, song.beschreibung, tagWaehlen),
    h("div", { class: "library-song-stats" }, soundcloudZahlen(song) ||
      h("span", { class: "library-sc-unavailable", "aria-label": "Keine SoundCloud-Zahlen verfügbar" }, "–")), fassung, aktionen);
}

const filterFelder = [
  ["typ", "Alben / Singles", ["Album", "Singles"]],
  ["stil", "Stilreferenz"],
  ["genre", "SoundCloud-Genre"],
  ["tags", "SoundCloud-Tag"],
  ["format", "Dateiformat"],
  ["wertung", "Bewertung", ["Positiv", "Bewertet", "Ohne Bewertung"]],
  ["sc", "SoundCloud", ["Öffentlich zugeordnet", "Privat", "Keine Zuordnung"]],
  ["cover", "Songcover", ["Mit Cover", "Ohne Cover"]],
  ["lyrics", "Lyrics", ["Lokal vorhanden", "Lokal nicht zugeordnet"]],
  ["tempo", "Tempo", ["Unter 100 BPM", "100–119 BPM", "120–139 BPM", "140 BPM und mehr", "Nicht belegt"]],
];

function tempoGruppe(bpm) {
  if (!bpm) return "Nicht belegt";
  if (bpm < 100) return "Unter 100 BPM";
  if (bpm < 120) return "100–119 BPM";
  if (bpm < 140) return "120–139 BPM";
  return "140 BPM und mehr";
}

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
    sc: [song.kurzprofil?.soundcloud_status || "Keine Zuordnung"],
    cover: [song.cover ? "Mit Cover" : "Ohne Cover"],
    lyrics: [song.lyrics_vorhanden ? "Lokal vorhanden" : "Lokal nicht zugeordnet"],
    tempo: [tempoGruppe(song.kurzprofil?.tempo_bpm)],
  };
}

export function songsAnsicht(el) {
  document.body.classList.add("songs-page");
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
        const text = [basis, song.titel, song.beschreibung, ...merkmale.tags, ...merkmale.genre].join(" ").toLowerCase();
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
    const zeile = ({ song }) => songZeile(song, album?.cover, auftraege, fassungen, tagWaehlen);
    const haupttitel = [], weitere = [];
    for (const eintrag of sichtbar) {
      const extra = album && eintrag.song.dateien.every(datei =>
        /^(weitere songs|notpublished)(?:\/|$)/i.test(datei.unterordner));
      (extra ? weitere : haupttitel).push(eintrag);
    }
    const extraListe = weitere.length ? h("li", { class: "library-extra" },
      h("details", { open: !haupttitel.length },
        h("summary", {}, "Weitere lokale Songs (" + weitere.length + ")"),
        h("ul", { class: "library-song-list" }, weitere.map(zeile)))) : null;
    const spalten = h("div", { class: "library-song-columns" },
      h("span", { class: "library-song-identity" }, "Song"),
      h("div", { class: "library-song-stats library-sc-numbers" },
        scZaehler.map(([, label]) => h("span", { title: label, "aria-label": label },
          label === "Kommentare" ? "Komm." : label))),
      h("span", { class: "library-song-version" }, "Fassung"));
    inhalt.append(kopf, h("div", { class: "library-detail-body" },
      album ? h("div", { class: "library-album-overview" },
        beschreibung(album.beschreibung, "library-album-description", "Keine Albumbeschreibung hinterlegt"),
        albumEigenschaften(katalog.releases.find(release => release.pfad === album.pfad) || album)) : null,
      sichtbar.length ? [spalten, h("ul", { class: "library-song-list" }, haupttitel.map(zeile), extraListe)]
        : h("p", { class: "library-album-empty klein" }, "In diesem Albumordner liegt keine Audiodatei.")));
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
  return () => { beendet = true; clearTimeout(wartezeit); document.body.classList.remove("songs-page"); };
}
