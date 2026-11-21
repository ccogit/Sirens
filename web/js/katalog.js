// Referenzauswahl: Suche, Filter, aufklappbare Liste Künstler → Release → Song → Datei.
import { api } from "./api.js";
import { h, leeren, meldung, neueId } from "./dom.js";
import { releaseReferenzen, scoreText } from "./logic.js";
import { abspielKnopf, knoepfeAktualisieren } from "./player.js";

function bewertungsMarke(b) {
  if (!b) return null;
  const klasse = b.score > 0 ? "gut" : b.score < 0 ? "schlecht" : "neutral";
  return h("span", { class: `wertung ${klasse}`, title: b.label || "Bewertung" }, scoreText(b.score));
}

function dateiName(d) {
  const teile = [d.version != null ? `Version ${d.version}` : "Datei"];
  if (d.fassung) teile.push(d.fassung);
  if (d.unterordner) teile.push(d.unterordner);
  return teile.join(" · ");
}

// `gewaehlt()` liefert die gewählten Pfade, `hinzu(pfade)` übernimmt neue. Rückgabe: Element mit .auffrischen().
export function referenzAuswahl({ gewaehlt, hinzu, beschriftung = "Referenz suchen" }) {
  const suchId = neueId();
  const filterId = neueId();
  const suche = h("input", { id: suchId, type: "search", placeholder: "Künstler, Album oder Titel", autocomplete: "off" });
  const nurGute = h("input", { id: filterId, type: "checkbox" });
  const stand = h("p", { class: "klein", "aria-live": "polite" });
  const baum = h("div", { class: "baum" });
  let timer = null;
  let lauf = 0;
  let beendet = false;

  function auffrischen() {
    const pfade = new Set(gewaehlt());
    for (const k of baum.querySelectorAll("button[data-waehlen]")) {
      const an = pfade.has(k.dataset.waehlen);
      k.disabled = an;
      k.textContent = an ? "Gewählt ✓" : "Wählen";
    }
    knoepfeAktualisieren();
  }

  function dateiZeile(d, titel) {
    return h("li", { class: "datei" },
      abspielKnopf(d.pfad),
      h("span", { class: "datei-name" }, dateiName(d)),
      bewertungsMarke(d.bewertung),
      h("button", { type: "button", class: "klein-knopf", "data-waehlen": d.pfad, "aria-label": `${titel}, ${dateiName(d)} als Referenz wählen`,
        onclick: () => { hinzu([d.pfad]); auffrischen(); } }, "Wählen"));
  }

  function releaseBlock(release, offen) {
    const anzahl = release.songs.length;
    const inhalt = h("div", { class: "release-inhalt" });
    const fuellen = () => {
      if (inhalt.childElementCount) return;
      inhalt.append(
        h("button", { type: "button", class: "klein-knopf", onclick: () => { hinzu(releaseReferenzen(release)); auffrischen(); } },
          anzahl === 1 ? "Diesen Song übernehmen" : `Ganzes Album übernehmen (${anzahl} Songs)`),
        h("ul", { class: "songs" }, release.songs.map((song) =>
          h("li", {}, h("span", { class: "song-titel" }, song.titel),
            h("ul", { class: "dateien" }, song.dateien.map((d) => dateiZeile(d, song.titel)))))));
      auffrischen();
    };
    const block = h("details", { class: "release", open: offen, ontoggle: (e) => { if (e.target.open) fuellen(); } },
      h("summary", {}, release.slug, h("span", { class: "anzahl" }, String(anzahl))), inhalt);
    if (offen) fuellen();
    return block;
  }

  function zeichnen(daten, gesucht) {
    leeren(baum);
    if (daten.error === "music_root_missing") {
      stand.textContent = "";
      baum.append(h("p", { class: "fehler", role: "alert" }, daten.meldung));
      return;
    }
    if (daten.zustand === "laeuft" || daten.zustand === "leer") {
      stand.textContent = "Der Musikordner wird gelesen …";
      timer = setTimeout(laden, 1000);
      if (!daten.artists.length) return;
    } else {
      stand.textContent = daten.anzahl_dateien ? `${daten.anzahl_dateien} Dateien` : "Nichts gefunden.";
    }
    const allesOffen = gesucht && daten.anzahl_dateien <= 80;
    for (const artist of daten.artists) {
      const inhalt = h("div", {});
      const fuellen = () => {
        if (!inhalt.childElementCount) inhalt.append(...artist.releases.map((r) => releaseBlock(r, allesOffen || artist.releases.length === 1)));
      };
      const offen = allesOffen || daten.artists.length === 1;
      baum.append(h("details", { class: "kuenstler", open: offen, ontoggle: (e) => { if (e.target.open) fuellen(); } },
        h("summary", {}, artist.slug, h("span", { class: "anzahl" }, String(artist.releases.length))), inhalt));
      if (offen) fuellen();
    }
  }

  async function laden() {
    clearTimeout(timer);
    if (beendet) return;
    const meiner = ++lauf;
    const q = suche.value.trim();
    try {
      const daten = await api.katalog(q, nurGute.checked ? 1 : null);
      if (meiner === lauf && !beendet) zeichnen(daten, Boolean(q) || nurGute.checked);
    } catch (fehler) {
      if (meiner === lauf) stand.textContent = fehler.meldung;
    }
  }

  suche.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(laden, 250); });
  nurGute.addEventListener("change", laden);
  const neuLesen = h("button", { type: "button", class: "schlicht", onclick: async () => {
    try { await api.katalogNeuLesen(); meldung("Der Musikordner wird neu gelesen."); } catch (f) { meldung(f.meldung, "fehler"); }
    laden();
  } }, "Aktualisieren");

  const el = h("div", { class: "auswahl" },
    h("div", { class: "auswahl-kopf" },
      h("div", { class: "feld wachsen" }, h("label", { for: suchId }, beschriftung), suche),
      h("label", { class: "haken", for: filterId }, nurGute, "nur gut bewertete"),
      neuLesen),
    stand, baum);
  el.auffrischen = auffrischen;
  el.beenden = () => { beendet = true; clearTimeout(timer); };
  laden();
  return el;
}
