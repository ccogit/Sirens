// Bausteine des Formulars „Neuer Auftrag“: gewählte Referenzen, Songwünsche, weitere Angaben.
import { feld, h, knopfReihe, leeren, neueId } from "./dom.js";
import { dateiInfo, takeName } from "./logic.js";
import { abspielKnopf, knoepfeAktualisieren } from "./player.js";

// Gewählte Dateien als entfernbare Karten, je Karte „normal/stark“ und „Was übernehmen?“.
export function referenzKarten(w, geaendert) {
  const liste = h("ul", { class: "gewaehlt" });
  const leer = h("p", { class: "hinweis" }, "Noch keine Referenz gewählt. Oben suchen und „Wählen“ drücken.");
  const el = h("div", {}, h("h3", {}, "Deine Referenzen"), leer, liste);

  function zeichnen() {
    leeren(liste);
    leer.hidden = w.referenzen.length > 0;
    w.referenzen.forEach((ref) => {
      const d = dateiInfo(ref.pfad);
      const eingabe = h("input", { type: "text", value: ref.uebernehmen || "", placeholder: "z. B. nur den Bass und das Tempo",
        oninput: (e) => { ref.uebernehmen = e.target.value; geaendert(); } });
      liste.append(h("li", { class: "ref-karte" },
        h("div", { class: "ref-kopf" },
          abspielKnopf(ref.pfad),
          h("div", { class: "ref-titel" }, h("strong", {}, d.titel), h("span", { class: "klein" }, `${d.artist} / ${d.release} · ${takeName(ref.pfad)}`)),
          h("button", { type: "button", class: "schlicht", "aria-label": `${d.titel} entfernen`,
            onclick: () => { w.referenzen.splice(w.referenzen.indexOf(ref), 1); zeichnen(); geaendert(true); } }, "Entfernen")),
        h("div", { class: "ref-fuss" },
          knopfReihe(`Gewicht von ${d.titel}`, [["normal", "normal"], ["stark", "stark", "Diese Referenz zählt besonders"]],
            ref.gewicht || "normal", (wert) => { ref.gewicht = wert; geaendert(); }, "klein"),
          feld("Was übernehmen? (freiwillig)", eingabe))));
    });
    knoepfeAktualisieren();
  }
  zeichnen();
  return { el, zeichnen };
}

// Wünsche zu einzelnen Songs eines Albums.
export function trackWuensche(w, geaendert) {
  const liste = h("ul", { class: "songwuensche" });

  function zeichnen() {
    leeren(liste);
    w.track_wuensche.forEach((eintrag) => {
      const nr = h("input", { type: "number", min: 1, max: 20, value: eintrag.nr, class: "schmal",
        oninput: (e) => { eintrag.nr = Number(e.target.value); geaendert(); } });
      const text = h("input", { type: "text", value: eintrag.text, placeholder: "z. B. ein Instrumental mit langem Intro",
        oninput: (e) => { eintrag.text = e.target.value; geaendert(); } });
      liste.append(h("li", { class: "songwunsch" }, feld("Song Nr.", nr), feld("Wunsch", text),
        h("button", { type: "button", class: "schlicht", "aria-label": `Wunsch zu Song ${eintrag.nr} entfernen`,
          onclick: () => { w.track_wuensche.splice(w.track_wuensche.indexOf(eintrag), 1); zeichnen(); geaendert(); } }, "Entfernen")));
    });
  }
  const hinzu = h("button", { type: "button", class: "klein-knopf", onclick: () => {
    const belegt = w.track_wuensche.map((t) => t.nr);
    let nr = 1;
    while (belegt.includes(nr) && nr < 20) nr += 1;
    w.track_wuensche.push({ nr, text: "" });
    zeichnen();
    liste.lastElementChild?.querySelector("input[type=text]")?.focus();
  } }, "Wunsch für einen Song hinzufügen");
  zeichnen();
  const el = h("details", { class: "klappe" }, h("summary", {}, "Wünsche zu einzelnen Songs"),
    h("p", { class: "hinweis" }, "Freiwillig. Alles, was du offen lässt, entscheidet Claude."), liste, hinzu);
  return { el, zeichnen };
}

function schalter(titel, erklaerung, an, beiWechsel) {
  const id = neueId();
  const box = h("input", { id, type: "checkbox", checked: an, onchange: (e) => beiWechsel(e.target.checked) });
  return h("div", { class: "schalter" }, box, h("div", {}, h("label", { for: id }, titel), h("p", { class: "hinweis" }, erklaerung)));
}

// Einklappbar „Weitere Angaben“. `releaseListe` ist ein <datalist> mit den Alben des Künstlers.
export function optionenBlock(w, geaendert, releaseListe) {
  const o = w.optionen;
  const text = (name, attrs = {}) => h("input", { type: "text", value: o[name] || "", ...attrs,
    oninput: (e) => { o[name] = e.target.value; geaendert(); } });
  const wahl = (name, werte) => {
    const s = h("select", { onchange: (e) => { o[name] = e.target.value; geaendert(); } },
      werte.map(([wert, beschriftung]) => h("option", { value: wert }, beschriftung)));
    s.value = o[name];
    return s;
  };
  const ziel = h("input", { type: "text", value: w.ziel_release_slug || "", list: releaseListe.id, placeholder: "leer = neues Album bzw. neue Single",
    oninput: (e) => { w.ziel_release_slug = e.target.value.trim(); geaendert(); } });
  const zielFeld = feld("Zu einem bestehenden Album hinzufügen", ziel, { name: "ziel_release_slug",
    hinweis: "Nur für einen einzelnen Song: Name des Albumordners." });
  // Im Fast Mode entfallen Planfreigabe und Zusatzprüfung ohnehin; ihre Schalter verschwinden dann.
  const nurNormal = [
    schalter("Plan vorher zeigen",
      "An: Claude hält an, bevor etwas erzeugt wird, und zeigt dir Titel, Idee und Stil je Song. Du gibst frei oder schreibst Änderungen. Aus: Claude läuft ohne Halt durch, du hörst das Ergebnis.",
      o.planfreigabe === "an", (an) => { o.planfreigabe = an ? "an" : "aus"; geaendert(); }),
    schalter("Zusatzprüfung vor dem Senden",
      "An (empfohlen): Ein zweites, unabhängiges Gutachten prüft Text und Klangbeschreibung, bevor der Song kostenpflichtig erzeugt wird. Aus: Diese eine Prüfung entfällt auf deinen Wunsch; alle anderen bleiben.",
      o.zweitgutachten !== "aus", (an) => { o.zweitgutachten = an ? "an" : "aus"; geaendert(); })];
  const anpassen = () => { for (const s of nurNormal) s.hidden = o.tempo === "schnell"; };
  const schnell = schalter("Fast Mode",
    "An: Der Song geht deutlich schneller raus. Dafür entfallen Rückfrage, Planfreigabe, Zusatzprüfung, die Web-Stichprobe auf ähnliche Songs und bei Alben der Abgleich der Texte untereinander. Die Qualität kann darunter leiden.",
    o.tempo === "schnell", (an) => { o.tempo = an ? "schnell" : "normal"; anpassen(); geaendert(); });
  anpassen();
  const el = h("details", { class: "klappe" }, h("summary", {}, "Weitere Angaben und Fast Mode"),
    h("div", { class: "raster" },
      feld("Titelwunsch", text("titelwunsch", { placeholder: "leer = Claude schlägt vor" }), { name: "titelwunsch" }),
      feld("Sprache", text("sprache", { placeholder: "z. B. Englisch, Deutsch" }), { name: "sprache" }),
      feld("Gesang", wahl("gesang", [["mit", "mit Gesang"], ["instrumental", "instrumental"], ["egal", "egal – Claude entscheidet"]]), { name: "gesang" }),
      feld("Erzeugt mit", wahl("provider", [["suno", "Suno (Standard)"], ["minimax", "MiniMax"]]), { name: "provider" }),
      zielFeld,
      feld("Was auf keinen Fall vorkommen soll", text("no_gos", { placeholder: "z. B. kein Klavier, keine Streicher" }), { name: "no_gos" })),
    schnell, nurNormal);
  el.zielZeigen = (sichtbar) => { zielFeld.hidden = !sichtbar; };
  return el;
}
