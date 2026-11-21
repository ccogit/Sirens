// Songbibliothek: kompakte Zeilen für laufende und kürzlich bearbeitete Produktionen.
import { api } from "./api.js";
import { h, leeren, meldung } from "./dom.js";
import { kurz, zeitText } from "./logic.js";
import { abspielKnopf, knoepfeAktualisieren } from "./player.js";

const TAGE = 30;

function songZeile(auftrag, song, aktualisieren) {
  const laeuft = !song.bearbeitbar;
  const reife = song.sync_offen ? "SoundCloud-Update offen"
    : song.soundcloud ? "Auf SoundCloud" : laeuft ? "In Produktion" : "Lokal";
  const abbildung = song.cover
    ? h("img", { src: api.bildUrl(song.cover), alt: "", loading: "lazy" })
    : h("span", { class: "song-placeholder", "aria-hidden": "true" }, "♫");
  const knopf = h("button", { type: "button", class: "knopf zweit song-edit", onclick: async (e) => {
    e.target.disabled = true;
    e.target.textContent = "Öffnet …";
    try {
      const frisch = await api.lesen(auftrag.id);
      if (song.bearbeitbar) {
        await api.aktion(auftrag.id, "nachlauf", frisch.revision, { pfad: song.pfad });
      }
      location.hash = "#/auftrag/" + auftrag.id;
    } catch (fehler) {
      meldung(fehler.meldung, "fehler");
      aktualisieren();
    }
  } }, laeuft ? "Auftrag ansehen" : "Bearbeiten →");
  return h("li", { class: "library-row" },
    h("div", { class: "song-art" }, abbildung),
    h("div", { class: "song-identity" },
      h("strong", {}, song.titel),
      h("span", { class: "klein" }, auftrag.wunsch.artist_slug || "Unbekannt", " · ", kurz(auftrag.titel || "", 42))),
    h("div", { class: "song-row-state" },
      h("span", { class: "state-dot" + (song.sync_offen ? " alert" : "") }),
      reife),
    h("span", { class: "song-updated klein" }, zeitText(auftrag.updated_at)),
    h("div", { class: "song-row-actions" }, abspielKnopf(song.pfad), knopf));
}

export function songsAnsicht(el) {
  let beendet = false;
  let letzter = "";
  let alle = false;
  const inhalt = h("div", { class: "songs-library" });
  el.append(inhalt);

  async function laden() {
    try {
      const daten = await api.liste();
      if (beendet) return;
      const signature = JSON.stringify([alle, daten.auftraege.map(a => [a.id, a.revision])]);
      if (signature === letzter) return;
      letzter = signature;
      const stichtag = Date.now() - TAGE * 86400_000;
      const zeilen = daten.auftraege.flatMap(a =>
        (a.songs || []).map(song => ({ auftrag: a, song })));
      const aktuell = zeilen.filter(x => ["in_arbeit", "gesendet", "nachlauf", "fertig"].includes(x.auftrag.status)
        || Date.parse(x.auftrag.updated_at) >= stichtag);
      const sichtbar = alle ? zeilen : aktuell;
      leeren(inhalt).append(
        h("header", { class: "library-header" },
          h("div", {},
            h("p", { class: "eyebrow" }, "DEINE MUSIK"),
            h("h1", {}, "Alle Songs. Ein Blick."),
            h("p", { class: "dashboard-intro" }, "Fassungen weiterbearbeiten, Veröffentlichungen aktualisieren, Überflüssiges archivieren.")),
          h("a", { class: "knopf", href: "#/mastern" }, "＋ Vorhandenen Song bearbeiten")),
        h("section", { class: "library-panel" },
          h("div", { class: "library-toolbar" },
            h("h2", {}, "Songbibliothek"),
            h("span", { class: "mini-count" }, String(sichtbar.length)),
            h("button", { type: "button", class: "library-toggle",
              onclick: () => { alle = !alle; letzter = ""; laden(); } },
              alle ? "Nur aktuelle anzeigen" : "Auch ältere anzeigen")),
          sichtbar.length ? h("ul", { class: "library-list" }, sichtbar.map(x =>
            songZeile(x.auftrag, x.song, () => { letzter = ""; laden(); })))
            : h("div", { class: "library-empty" },
                h("h3", {}, "Hier erscheinen deine Songs."),
                h("p", {}, "Sobald Takes vorliegen, kannst du sie von hier aus öffnen und bearbeiten."),
                h("a", { href: "#/neu", class: "knopf" }, "Neuen Song starten"))),
        h("p", { class: "library-note" }, "Alte Versionen werden nur nach einer ausdrücklichen Entscheidung archiviert. Der aktuelle Master und veröffentlichte Fassungen bleiben geschützt."));
      knoepfeAktualisieren();
    } catch (fehler) {
      if (!beendet) leeren(inhalt).append(h("p", { class: "fehler", role: "alert" }, fehler.meldung));
    }
  }
  laden();
  const takt = setInterval(() => { if (!document.hidden) laden(); }, 4000);
  return () => { beendet = true; clearInterval(takt); };
}
