// Einzelansicht eines Auftrags: oben steht immer, was der Nutzer jetzt tun kann.
import { api } from "./api.js";
import { eingabenMerken, eingabenWiederherstellen, fehlerZeigen, feld, h, leeren, meldung } from "./dom.js";
import { ablaufStationen, anzeige, auftragTitel, fehlerFeld } from "./logic.js";
import { LAEUFT, ablaufGesamt, angaben, ergebnis, planAnsicht, songs } from "./auftrag_teile.js";
import { knoepfeAktualisieren } from "./player.js";
import { claudeKasten } from "./claude.js";
import { nachlaufAnsicht } from "./nachlauf.js";

const ABBRECHBAR = ["offen", "in_arbeit", "rueckfrage", "plan_wartet", "antwort_da", "fehler"];

export function auftragAnsicht(el, id) {
  let order = null;
  let beendet = false;
  const inhalt = h("div", {});
  el.append(inhalt);

  async function tun(name, body) {
    try {
      order = await api.aktion(id, name, order.revision, body);
      zeichnen();
      return true;
    } catch (fehler) {
      if (fehler.error === "revision_conflict") {
        await laden(true);
        meldung("Der Auftrag hat sich gerade geändert. Bitte noch einmal.", "fehler");
      } else if (!fehlerZeigen(inhalt, fehlerFeld(fehler.feld), fehler.meldung)) meldung(fehler.meldung, "fehler");
      return false;
    }
  }

  const wert = (key) => inhalt.querySelector(`[data-key="${key}"]`)?.value.trim() || "";
  const leerenFeld = (key) => { const f = inhalt.querySelector(`[data-key="${key}"]`); if (f) f.value = ""; };

  function jetztTun() {
    const s = order.status;
    if (s === "entwurf") return h("a", { class: "knopf", href: `#/neu/${id}` }, "Entwurf weiter ausfüllen");
    if (s === "rueckfrage") {
      const frage = [...order.verlauf].reverse().find((e) => e.art === "rueckfrage");
      const antwort = h("textarea", { rows: 4, "data-key": "antwort" });
      return h("div", {},
        h("blockquote", { class: "frage" }, (frage?.text || "").split("\n").map((z) => h("p", {}, z))),
        feld("Deine Antwort", antwort, { name: "text" }),
        h("button", { type: "button", class: "knopf", onclick: async () => {
          const text = wert("antwort");
          if (!text) { fehlerZeigen(inhalt, "text", "Bitte eine Antwort schreiben."); return; }
          leerenFeld("antwort");
          if (!(await tun("antwort", { text }))) antwort.value = text;
        } }, "Antwort schicken"));
    }
    if (s === "plan_wartet") {
      const allgemein = h("textarea", { rows: 3, "data-key": "plan-text", placeholder: "z. B. insgesamt lustiger, weniger Techno" });
      return h("div", {},
        planAnsicht(order.plan, true),
        feld("Änderung am ganzen Plan (freiwillig)", allgemein, { name: "text" }),
        h("div", { class: "knopfzeile" },
          h("button", { type: "button", class: "knopf", onclick: () => tun("plan", { entscheidung: "freigeben" }) }, "Plan freigeben"),
          h("button", { type: "button", class: "knopf zweit", onclick: async () => {
            const tracks = order.plan.tracks.map((t) => ({ nr: t.nr, text: wert(`plan-${t.nr}`) })).filter((t) => t.text);
            const text = wert("plan-text");
            if (!text && !tracks.length) { fehlerZeigen(inhalt, "text", "Bitte schreiben, was anders sein soll – oder den Plan freigeben."); return; }
            await tun("plan", { entscheidung: "aendern", text, tracks });
          } }, "Änderungen an Claude schicken")));
    }
    if (LAEUFT.includes(s)) {
      return order.tracks_stand.length ? songs(order.tracks_stand)
        : h("p", { class: "hinweis" }, "Sobald der Plan steht, erscheint hier der Stand je Song.");
    }
    if (s === "fertig" || s === "abgeschlossen") {
      return ergebnis(order, {
        bewerten: (pfad, score, favorit, kommentar) => tun("bewertung", { pfad, score, favorit, kommentar }),
        folge: async (vorlage) => {
          try { location.hash = `#/neu/${(await api.folge(id, vorlage)).id}`; } catch (f) { meldung(f.meldung, "fehler"); }
        },
        abschliessen: () => tun("abschliessen"),
        fertigMachen: (pfad) => tun("nachlauf", { pfad }),
      });
    }
    if (s === "nachlauf") return nachlaufAnsicht(order, { tun, neuLaden: () => laden(true) });
    return null;
  }

  function zeichnen() {
    const merk = eingabenMerken(inhalt);
    const auf = new Map([...inhalt.querySelectorAll("details[data-auf]")].map((d) => [d.dataset.auf, d.open]));
    const stand = anzeige(order.lage);
    const lage = order.lage;
    // Ein einziger Kasten für Claude, egal wie viele Stellen des Auftrags auf ihn warten.
    const fuerClaude = lage.dran === "claude" ? (order.status === "fehler" ? "Der Grund steht im Ablauf." : "")
      : lage.offene_bewertungen ? `Claude übernimmt noch ${lage.offene_bewertungen === 1 ? "deine neue Bewertung" : `deine ${lage.offene_bewertungen} neuen Bewertungen`}.`
        : "Auch Claude hat hier noch etwas zu erledigen.";
    const planLesen = order.plan && order.status !== "plan_wartet"
      ? h("details", { class: "klappe", "data-auf": "plan" }, h("summary", {}, "Der Plan"), planAnsicht(order.plan)) : null;
    const stationen = ablaufStationen(order);
    const fertig = stationen.filter((st) => st.zustand === "erledigt" || st.zustand === "ausgelassen").length;
    const aktuell = stationen.find((st) => st.zustand === "aktiv");
    const prozent = Math.round(fertig / Math.max(stationen.length, 1) * 100);
    leeren(inhalt).append(
      h("div", { class: "backbar" },
        h("a", { href: "#/" }, "← Alle Aufträge"),
        h("span", { class: "klein zahlen" }, order.id)),
      h("header", { class: "auftrag-kopf" },
        h("div", {},
          h("p", { class: "eyebrow" }, "DEIN MUSIKPROJEKT"),
          h("h1", {}, auftragTitel({ ...order, titel: order.plan?.titel || order.wunsch.optionen.titelwunsch }))),
        h("span", { class: "order-pill " + stand.klasse },
          h("span", { class: "order-pill-dot", "aria-hidden": "true" }), stand.text)),
      h("div", { class: "zweispaltig order-layout" },
        h("section", { class: "block jetzt " + stand.klasse, "aria-label": "Nächster Schritt" },
          h("p", { class: "eyebrow" }, "ALS NÄCHSTES"),
          h("h2", { class: "next-action" }, lage.naechster_schritt),
          lage.claude_auch_dran ? claudeKasten(order.claude, fuerClaude, () => laden(true)) : null,
          jetztTun()),
        h("aside", { class: "order-sidebar", "aria-label": "Projektübersicht" },
          h("section", { class: "block order-progress", "aria-label": "Fortschritt" },
            h("div", { class: "progress-top" },
              h("h2", {}, "Fortschritt"),
              h("span", { class: "klein zahlen" }, fertig + " / " + stationen.length)),
            h("p", { class: "progress-current" }, aktuell ? aktuell.name : order.status === "abgeschlossen" ? "Abgeschlossen" : "In Vorbereitung"),
            h("div", { class: "progress-track", role: "progressbar",
              "aria-label": "Erledigte Prozessschritte", "aria-valuemin": "0",
              "aria-valuemax": String(stationen.length), "aria-valuenow": String(fertig) },
              h("span", { class: "progress-fill", style: "width: " + prozent + "%" })),
            h("p", { class: "hinweis" }, "Die Details siehst du nur, wenn du sie brauchst.")),
          h("details", { class: "order-more", "data-auf": "ablauf" },
            h("summary", {}, "Alle Schritte & Meldungen"),
            ablaufGesamt(order, stand.klasse)),
          planLesen, angaben,
          ABBRECHBAR.includes(order.status) ? h("p", { class: "abbrechen" },
            h("button", { type: "button", class: "schlicht", onclick: () => {
              const knopf = inhalt.querySelector(".abbrechen");
              leeren(knopf).append("Auftrag wirklich abbrechen? ",
                h("button", { type: "button", class: "knopf gefahr", onclick: () => tun("abbrechen") }, "Ja, abbrechen"), " ",
                h("button", { type: "button", class: "schlicht", onclick: zeichnen }, "Nein"));
            } }, "Auftrag abbrechen")) : null)));
    eingabenWiederherstellen(inhalt, merk);
    for (const d of inhalt.querySelectorAll("details[data-auf]")) if (auf.has(d.dataset.auf)) d.open = auf.get(d.dataset.auf);
    knoepfeAktualisieren();
  }

  async function laden(erzwingen = false) {
    let neu;
    try {
      neu = await api.lesen(id);
    } catch (fehler) {
      if (!order && !beendet) leeren(inhalt).append(h("p", { class: "fehler", role: "alert" }, fehler.meldung), h("p", {}, h("a", { href: "#/" }, "Zu den Aufträgen")));
      return;
    }
    if (beendet || (!erzwingen && order && neu.revision === order.revision && neu.claude?.laeuft === order.claude?.laeuft)) return;
    order = neu;
    zeichnen();
  }

  laden();
  const takt = setInterval(() => { if (!document.hidden) laden(); }, 4000);
  return () => { beendet = true; clearInterval(takt); };
}
