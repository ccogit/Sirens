// Startseite: ein klarer nächster Schritt, danach nur die relevanten Warteschlangen.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";
import { auftragTitel, gruppen, kurz, zeitText } from "./logic.js";
import { claudeKasten } from "./claude.js";

function ziel(a) {
  return a.status === "entwurf" ? "#/neu/" + a.id : "#/auftrag/" + a.id;
}

function karte(a) {
  const status = a.status === "entwurf" ? "Entwurf"
    : a.lage.dran === "nutzer" ? "Deine Entscheidung"
    : a.lage.dran === "claude" ? "Bei Claude"
    : a.lage.dran === "laeuft" ? "In Produktion" : "Abgeschlossen";
  return h("li", {}, h("a", { class: "karte", href: ziel(a) },
    h("span", { class: "karte-top" },
      h("span", { class: "card-state" }, status),
      h("span", { class: "klein zahlen" }, zeitText(a.updated_at))),
    h("strong", { class: "karte-titel" }, auftragTitel(a)),
    h("span", { class: "karte-text" }, kurz(a.lage.naechster_schritt, 106)),
    h("span", { class: "karte-link", "aria-hidden": "true" }, "Ansehen ↗")));
}

// Der Weg zu den Spielzeugen (Live Lab): hüpfende Buchstaben, tanzende Balken, ein Rand, der sich dreht.
function spielKnopf() {
  return h("a", { class: "spiel-knopf", href: "#/lab", "aria-label": "Spielen: DJ-Pult, Beat-Pads, Emblem, Auto-DJ, Kick-Tausch und Stem Studio" },
    h("span", { class: "spiel-knopf-takt", "aria-hidden": "true" }, [1, 2, 3, 4, 5].map(() => h("i", {}))),
    h("span", { class: "spiel-knopf-wort", "aria-hidden": "true" }, [..."SPIELEN"].map((buchstabe) => h("b", {}, buchstabe))),
    h("small", { "aria-hidden": "true" }, "DJ-Pult, Emblem, Auto-DJ, Kick-Tausch, Stem Studio"));
}

function zaehler(zahl, text, farbe) {
  return h("div", { class: "dashboard-stat " + farbe },
    h("strong", { class: "zahlen" }, String(zahl)),
    h("span", {}, text));
}

function fokus(a) {
  return h("a", { class: "focus-card", href: ziel(a) },
    h("span", { class: "focus-eyebrow" }, h("span", { class: "focus-dot" }), "DEIN NÄCHSTER SCHRITT"),
    h("h2", {}, auftragTitel(a)),
    h("p", {}, kurz(a.lage.naechster_schritt, 200)),
    h("span", { class: "focus-bottom" },
      h("span", { class: "focus-button" }, a.status === "entwurf" ? "Entwurf fortsetzen" : "Jetzt öffnen", " →"),
      h("span", { class: "focus-meta" }, zeitText(a.updated_at))));
}

function aufgaben(liste, titel, leer) {
  return h("section", { class: "queue-section", "aria-label": titel },
    h("div", { class: "queue-title" }, h("h3", {}, titel), h("span", { class: "mini-count" }, String(liste.length))),
    liste.length ? h("ul", { class: "karten" }, liste.map(karte)) : h("p", { class: "empty-small" }, leer));
}

export function startAnsicht(el) {
  let letzter = "";
  let erledigtOffen = false;
  const inhalt = h("div", { class: "dashboard" });
  el.append(inhalt);

  async function laden() {
    let daten;
    try {
      daten = await api.liste();
    } catch (fehler) {
      if (letzter !== "fehler") leeren(inhalt).append(h("p", { class: "fehler", role: "alert" }, fehler.meldung));
      letzter = "fehler";
      return;
    }
    const abdruck = JSON.stringify([
      daten.claude?.laeuft, daten.claude?.aktiv, daten.claude?.letzter?.beendet_am,
      daten.auftraege.map((a) => [a.id, a.revision])
    ]);
    if (abdruck === letzter) return;
    letzter = abdruck;
    const g = gruppen(daten.auftraege);
    const erster = g.nutzer[0];
    const inProduktion = g.claude.filter((a) => a.lage.dran !== "nutzer" && a.lage.dran !== "laeuft");
    const weitere = g.nutzer.slice(1);
    leeren(inhalt).append(
      h("header", { class: "dashboard-header" },
        h("div", {},
          h("p", { class: "eyebrow" }, "DEIN KREATIVSTUDIO"),
          h("h1", {}, "Musik entsteht hier."),
          h("p", { class: "dashboard-intro" }, "Alles im Blick. Nur das Wichtige im Fokus.")),
        h("div", { class: "dashboard-actions" }, spielKnopf(),
          h("a", { href: "#/neu", class: "knopf gross new-order" }, "＋ Neuer Auftrag"))),
      h("div", { class: "dashboard-stats", "aria-label": "Auftragsübersicht" },
        zaehler(g.nutzer.length, "Wartet auf dich", "nutzer"),
        zaehler(g.claude.length, "Bei Claude", "claude"),
        zaehler(g.laeuft.length, "In Arbeit", "laeuft")),
      h("div", { class: "dashboard-layout" },
        h("div", { class: "dashboard-primary" },
          erster ? fokus(erster)
            : h("section", { class: "focus-card focus-empty" },
                h("span", { class: "focus-eyebrow" }, h("span", { class: "focus-dot" }), daten.auftraege.length ? "ALLES ERLEDIGT" : "DEIN STARTPUNKT"),
                h("h2", {}, daten.auftraege.length ? "Du bist auf dem Laufenden." : "Dein nächster Song beginnt hier."),
                h("p", {}, daten.auftraege.length ? "Aktuell ist keine Entscheidung von dir nötig." : "Beschreibe deine Idee oder wähle einen Song als Inspiration."),
                h("a", { href: "#/neu", class: "focus-button" }, "Neuen Auftrag starten →")),
          weitere.length ? aufgaben(weitere, "Außerdem bei dir", "") : null,
          inProduktion.length || g.laeuft.length
            ? h("section", { class: "production-section" },
                h("div", { class: "section-heading" },
                  h("h2", {}, "In der Pipeline"),
                  h("p", {}, "Was gerade ohne dich weiterläuft.")),
                inProduktion.length ? aufgaben(inProduktion, "Claude übernimmt", "") : null,
                g.laeuft.length ? aufgaben(g.laeuft, "Wird produziert", "") : null)
            : null),
        h("aside", { class: "dashboard-aside", "aria-label": "Produktionsstatus" },
          h("section", { class: "status-panel" },
            h("div", { class: "status-heading" },
              h("span", { class: "status-icon", "aria-hidden": "true" }, "✦"),
              h("div", {}, h("h2", {}, "Claude Code"), h("p", {}, "Dein Produktionspartner"))),
            h("p", { class: "status-state" },
              h("span", { class: "status-indicator" + (daten.claude?.laeuft ? " online" : "") }),
              daten.claude?.laeuft ? "Arbeitet gerade" : g.claude.length ? (daten.claude?.aktiv ? "Bereit für den nächsten Lauf" : "Manueller Start nötig") : "Im Standby"),
            g.claude.length ? claudeKasten(daten.claude, "", () => { letzter = ""; laden(); })
              : h("p", { class: "status-help" }, "Sobald ein Auftrag an Claude übergeht, erscheint hier sein Status.")),
          h("section", { class: "quiet-tip" },
            h("span", { "aria-hidden": "true", class: "tip-icon" }, "♫"),
            h("p", {}, "Von der ersten Idee bis zum fertigen Master – du entscheidest, wann es weitergeht.")))),
      g.erledigt.length
        ? h("details", { class: "archive-panel", open: erledigtOffen, ontoggle: (e) => { erledigtOffen = e.target.open; } },
            h("summary", {}, h("span", {}, "Archiv"), h("span", { class: "mini-count" }, String(g.erledigt.length))),
            h("ul", { class: "karten archive-grid" }, g.erledigt.map(karte)))
        : "");
  }

  laden();
  const takt = setInterval(() => { if (!document.hidden) laden(); }, 4000);
  return () => clearInterval(takt);
}
