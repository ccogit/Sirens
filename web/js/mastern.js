// Vorhandenen Song wählen und ohne Songauftrag fertig machen: Mastering, Cover, Beschreibung, SoundCloud, Ableton.
import { api } from "./api.js";
import { h, meldung } from "./dom.js";
import { referenzAuswahl } from "./katalog.js";

const SCHRITTE = [["mastering", "Mastern", "Studio mit Analyse, Empfehlungen und Reglern", true],
  ["cover", "Cover", "Claude erstellt ein Cover", false],
  ["text", "Songbeschreibung", "Claude legt Beschreibung und Songtext beim Song ab", false],
  ["soundcloud", "SoundCloud", "Upload nach deiner Entscheidung, privat als Standard", false]];

export function masternAnsicht(el) {
  let unterwegs = false;
  const haken = SCHRITTE.map(([name, titel, text, an]) => {
    const eingabe = h("input", { type: "checkbox", id: `schritt-${name}`, checked: an });
    return { name, eingabe, el: h("div", { class: "schalter" }, eingabe,
      h("div", {}, h("label", { for: `schritt-${name}` }, titel), h("p", { class: "hinweis" }, text))) };
  });
  const auswahl = referenzAuswahl({
    beschriftung: "Song suchen",
    gewaehlt: () => [],
    hinzu: async (pfade) => {
      if (unterwegs || !pfade.length) return;
      unterwegs = true;
      try {
        const schritte = haken.filter((s) => s.eingabe.checked).map((s) => s.name);
        location.hash = `#/auftrag/${(await api.mastern(pfade[0], schritte)).id}`;
      } catch (fehler) {
        unterwegs = false;
        meldung(fehler.meldung, "fehler");
      }
    },
  });
  el.append(
    h("h1", { class: "seitenkopf" }, "Vorhandenen Song fertig machen"),
    h("div", { class: "zweispaltig links" },
      h("section", { class: "block" }, h("h2", {}, "Was soll passieren?"), haken.map((s) => s.el),
        h("p", { class: "hinweis" }, "Der Export nach Ableton ist danach immer per Knopf möglich, auch ohne Haken.")),
      h("section", { class: "block" }, h("h2", {}, "Welcher Song?"),
        h("p", { class: "hinweis" }, "Einen Take anhören. „Wählen“ legt sofort los."), auswahl)));
  return () => auswahl.beenden();
}
