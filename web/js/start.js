// Aufträge: drei Spuren nebeneinander – „Du bist dran“, „Claude ist dran“, „Läuft“ –, darunter Erledigtes.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";
import { auftragTitel, gruppen, kurz, zeitText, zusammenfassung } from "./logic.js";
import { claudeKasten } from "./claude.js";

function karte(a, spur) {
  const ziel = a.status === "entwurf" ? `#/neu/${a.id}` : `#/auftrag/${a.id}`;
  const n = a.lage.offene_bewertungen;
  let satz = a.lage.naechster_schritt;
  if (spur === "claude" && a.lage.dran !== "claude") {
    satz = n ? `Claude übernimmt noch ${n === 1 ? "eine Bewertung" : `${n} Bewertungen`}.` : "Claude hat hier nebenher zu tun.";
  }
  return h("li", {},
    h("a", { class: "karte", href: ziel },
      h("span", { class: "karte-kopf" }, h("strong", {}, auftragTitel(a)), h("span", { class: "klein zahlen" }, zeitText(a.updated_at))),
      h("span", {}, satz),
      a.frage ? h("span", { class: "zitat" }, `„${kurz(a.frage, 160)}“`) : null,
      h("span", { class: "klein" }, `${zusammenfassung(a.wunsch)} · `, h("span", { class: "zahlen" }, a.id))));
}

function spur(titel, klasse, liste, leer, davor) {
  return h("section", { class: `spur ${klasse}`, "aria-label": titel },
    h("h2", { class: "lampe" }, titel, h("span", { class: "anzahl" }, String(liste.length))),
    liste.length ? [davor, h("ul", { class: "karten" }, liste.map((a) => karte(a, klasse)))] : h("p", { class: "leer" }, leer));
}

export function startAnsicht(el) {
  let letzter = "";
  let erledigtOffen = false;
  const inhalt = h("div", {});
  el.append(h("h1", { class: "unsichtbar" }, "Aufträge"), inhalt);

  async function laden() {
    let daten;
    try {
      daten = await api.liste();
    } catch (fehler) {
      if (letzter !== "fehler") leeren(inhalt).append(h("p", { class: "fehler", role: "alert" }, fehler.meldung));
      letzter = "fehler";
      return;
    }
    const abdruck = JSON.stringify([daten.claude?.laeuft, daten.claude?.letzter?.beendet_am, daten.auftraege.map((a) => [a.id, a.revision])]);
    if (abdruck === letzter) return;  // nichts geändert: nichts neu zeichnen
    letzter = abdruck;
    const g = gruppen(daten.auftraege);
    leeren(inhalt);
    if (!daten.auftraege.length) {
      inhalt.append(h("p", { class: "leer" }, "Noch kein Auftrag. Du sagst, was entstehen soll, Claude macht den Rest."),
        h("p", {}, h("a", { class: "knopf gross", href: "#/neu" }, "Neuer Auftrag")));
      return;
    }
    inhalt.append(
      h("div", { class: "brett" },
        spur("Du bist dran", "nutzer", g.nutzer, "Gerade wartet nichts auf dich."),
        spur("Claude ist dran", "claude", g.claude, "Nichts offen.", claudeKasten(daten.claude, "", () => { letzter = ""; laden(); })),
        spur("Läuft", "laeuft", g.laeuft, "Gerade läuft nichts.")),
      g.erledigt.length ? h("details", { class: "spur niemand erledigtes", open: erledigtOffen, ontoggle: (e) => { erledigtOffen = e.target.open; } },
        h("summary", {}, h("h2", { class: "lampe" }, "Erledigt", h("span", { class: "anzahl" }, String(g.erledigt.length)))),
        h("ul", { class: "karten" }, g.erledigt.map((a) => karte(a, "niemand")))) : "");
  }

  laden();
  const takt = setInterval(() => { if (!document.hidden) laden(); }, 4000);
  return () => clearInterval(takt);
}
