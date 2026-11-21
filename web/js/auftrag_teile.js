// Bausteine der Einzelansicht: Plan, der eine Ablauf, Takes mit Bewertung, ursprüngliche Angaben.
import { feld, h } from "./dom.js";
import { BEZUG, SCORES, VORLAGEN, ablaufStationen, folgeHinweis, schrittLeiste, scoreText, takeName, zeitText, zusammenfassung } from "./logic.js";
import { abspielKnopf, explorerKnopf } from "./player.js";

export const LAEUFT = ["in_arbeit", "gesendet"];
const absaetze = (text) => (text || "").split("\n").map((zeile) => h("p", {}, zeile));

// Plan lesen; mit `aendern` zusätzlich je Song ein Feld „Ändern“.
export function planAnsicht(plan, aendern = false) {
  return h("div", { class: "plan" },
    plan.titel ? h("h3", {}, plan.titel) : null,
    plan.konzept ? h("div", { class: "konzept" }, absaetze(plan.konzept)) : null,
    h("ol", { class: "plan-songs" }, plan.tracks.map((t) => {
      const eingabe = h("input", { type: "text", "data-key": `plan-${t.nr}`, placeholder: "leer = passt so" });
      return h("li", { value: t.nr },
        h("strong", {}, t.titel || `Song ${t.nr}`),
        t.idee ? h("p", {}, t.idee) : null,
        t.stil_kurz ? h("p", { class: "klein" }, `Stil: ${t.stil_kurz}`) : null,
        t.text ? h("details", { "data-auf": `text-${t.nr}` }, h("summary", {}, "Songtext"), h("pre", { class: "songtext" }, t.text)) : null,
        aendern ? feld(`Ändern an „${t.titel || `Song ${t.nr}`}“`, eingabe) : null);
    })));
}

// Alle Arbeitsschritte bis zum Versand; zeigt, was erledigt ist, was läuft und was der Auftrag verkürzt oder auslässt.
export function ablaufListe(schritte) {
  const marke = { erledigt: "✓", aktiv: "▶", entfaellt: "–", offen: "" };
  return h("ol", { class: "ablauf" }, schritte.map((s) => {
    const zustand = s.zustand || (s.art === "entfaellt" ? "entfaellt" : "offen");
    return h("li", { class: `${zustand}${s.art === "kurz" ? " kurz" : ""}`, "aria-current": zustand === "aktiv" ? "step" : null },
      h("span", { class: "ablauf-marke", "aria-hidden": "true" }, marke[zustand]),
      h("span", { class: "ablauf-titel" }, s.titel),
      s.art === "entfaellt" ? h("span", { class: "ablauf-art" }, `entfällt${s.hinweis ? ` · ${s.hinweis}` : ""}`)
        : s.art === "kurz" ? h("span", { class: "ablauf-art kurz" }, `verkürzt · ${s.hinweis}`) : null,
      h("span", { class: "klein" }, s.wer));
  }));
}

// Je Song eine Zeile mit den Schritten Text → Paket → Geprüft → Gesendet → Fertig. Läuft der Auftrag, steht sie groß im
// Hauptblock, sonst im Ablauf unter „Prüfen und Senden“ – nie an beiden Stellen.
export function songs(tracks) {
  return h("ul", { class: "fortschritt", "aria-label": "Stand je Song" }, tracks.map((t) =>
    h("li", {},
      h("span", { class: "song-titel" }, `${t.nr}. ${t.titel || "Song"}`),
      t.schritt === "fehler" ? h("span", { class: "wertung schlecht" }, "Fehler") : null,
      h("ol", { class: "schritte", "aria-label": `Stand von Song ${t.nr}` }, schrittLeiste(t.schritt).map((s) =>
        h("li", { class: s.zustand, "aria-current": s.zustand === "aktiv" ? "step" : null }, s.text))))));
}

// Der eine Ablauf des Auftrags: zehn Stationen; in jeder ihre Arbeitsschritte und was dort geschah, bei „Prüfen und Senden“ der Stand je Song.
export function ablaufGesamt(order, klasse) {
  const art = { rueckfrage: "Frage", antwort: "Antwort", plan_aenderung: "Änderung am Plan", notiz: "Notiz", status: "" };
  const marke = { erledigt: "✓", aktiv: "▶", ausgelassen: "–", offen: "" };
  return h("section", { class: "block", "aria-label": "Ablauf" },
    h("h2", {}, "Ablauf", order.wunsch.optionen.tempo === "schnell" ? " (Fast Mode)" : ""),
    h("ol", { class: `kette ${klasse}` }, ablaufStationen(order).map((st) => {
      const kopf = [h("span", { class: "ablauf-marke", "aria-hidden": "true" }, marke[st.zustand]),
        h("span", { class: "nr" }, String(st.nr)), h("span", { class: "station-name" }, st.name)];
      const inhalt = [
        st.nr === 4 && order.tracks_stand.length && !LAEUFT.includes(order.status) ? songs(order.tracks_stand) : null,
        st.schritte.length ? ablaufListe(st.schritte) : null,
        st.eintraege.length ? h("ol", { class: "verlauf" }, st.eintraege.map((e) =>
          h("li", { class: e.von },
            h("span", { class: "klein" }, `${e.von === "nutzer" ? "Du" : "Claude"} · ${zeitText(e.zeit)}${art[e.art] ? ` · ${art[e.art]}` : ""}`),
            h("div", {}, absaetze(e.text))))) : null,
      ].filter(Boolean);
      return h("li", { class: `station ${st.zustand}`, "aria-current": st.zustand === "aktiv" ? "step" : null },
        inhalt.length ? h("details", { "data-auf": `station-${st.nr}`, open: st.zustand === "aktiv" }, h("summary", {}, kopf), h("div", { class: "station-inhalt" }, inhalt))
          : h("div", { class: "station-kopf" }, kopf));
    })));
}

function take(order, pfad, bewerten, fertigMachen) {
  const b = order.bewertungen.find((x) => x.pfad === pfad);
  const begonnen = [order.nachlauf, ...(order.nachlauf_weitere || [])].some((n) => n && n.favorit === pfad);
  const name = takeName(pfad);
  const kommentar = h("input", { type: "text", "data-key": `k-${pfad}`, value: b?.kommentar || "", placeholder: "freiwillig",
    onchange: (e) => { if (b) bewerten(pfad, b.score, b.favorit, e.target.value); } });
  const lesen = () => kommentar.value;
  return h("li", { class: `take${b?.favorit ? " favorit" : ""}` },
    h("div", { class: "take-kopf" }, abspielKnopf(pfad), h("strong", {}, name), explorerKnopf(pfad),
      b && !b.uebernommen ? h("span", { class: "klein" }, "noch nicht von Claude übernommen") : null,
      null),
    h("div", { class: "reihe noten", role: "group", "aria-label": `Bewertung für ${name}` }, SCORES.map(([score, text]) =>
      h("button", { type: "button", "aria-pressed": String(b?.score === score), title: text,
        "aria-label": `${scoreText(score)}, ${text}`, onclick: () => bewerten(pfad, score, b?.favorit || false, lesen()) },
        h("span", { class: "zahl" }, scoreText(score)), h("span", { class: "wort" }, text)))),
    h("div", { class: "take-fuss" },
      h("button", { type: "button", class: "stern", "aria-pressed": String(Boolean(b?.favorit)), disabled: !b,
        title: b ? "Favorit dieses Songs" : "Erst bewerten, dann als Favorit markieren",
        onclick: () => bewerten(pfad, b.score, !b.favorit, lesen()) }, b?.favorit ? "★ Favorit" : "☆ Favorit"),
      h("button", { type: "button", class: begonnen ? "knopf zweit" : "klein-knopf", disabled: !begonnen && !b?.favorit,
        title: begonnen || b?.favorit ? "Mastering, Ableton, Cover, Beschreibung, SoundCloud" : "Erst als Favorit markieren",
        onclick: () => fertigMachen(pfad) }, begonnen ? "Weiter fertig machen" : "Fertig machen"),
      h("details", { class: "comment-details", "data-auf": "kommentar-" + pfad, open: Boolean(b?.kommentar) },
        h("summary", {}, b?.kommentar ? "Kommentar bearbeiten" : "Kommentar hinzufügen"), feld("Dein Kommentar", kommentar))));
}

// Station 5: Takes anhören und bewerten, darunter Folgeaufträge und Abschließen.
export function ergebnis(order, { bewerten, folge, abschliessen, fertigMachen }) {
  const songs = order.tracks_stand.filter((t) => (t.dateien || []).length);
  return h("div", {},
    songs.map((t) => h("section", { class: "song", "aria-label": `Song ${t.nr}` },
      h("h3", {}, `${t.nr}. ${t.titel || "Song"}`),
      h("ul", { class: "takes" }, t.dateien.map((pfad) => take(order, pfad, bewerten, fertigMachen))))),
    h("div", { class: "weiter" },
      h("h3", {}, "Dein nächster Move"),
      h("p", { class: "hinweis" }, "Lieblingsversion gefunden? Markiere sie als Favorit und wähle „Fertig machen“."),
      order.status === "fertig" ? h("button", { type: "button", class: "knopf", onclick: abschliessen }, "Auftrag abschließen") : null,
      h("details", { class: "followup-options" },
        h("summary", {}, "Eine weitere Version erstellen"),
        h("p", { class: "hinweis" }, folgeHinweis(order)),
        h("div", { class: "knopfzeile" },
          VORLAGEN.map(([vorlage, text]) => h("button", { type: "button", class: "knopf zweit", onclick: () => folge(vorlage) }, text))))));
}

export function angaben(order) {
  const w = order.wunsch;
  const o = w.optionen;
  const zeile = (name, wert) => (wert ? [h("dt", {}, name), h("dd", {}, wert)] : []);
  return h("details", { class: "klappe", "data-auf": "angaben" }, h("summary", {}, "Deine ursprünglichen Angaben"),
    h("p", {}, zusammenfassung(w)),
    w.referenzen.length ? h("ul", { class: "takes" }, w.referenzen.map((r) =>
      h("li", { class: "take-kopf" }, abspielKnopf(r.pfad),
        h("span", {}, h("strong", {}, r.titel), ` · ${r.artist_slug} / ${r.release_slug} · ${takeName(r.pfad)}`,
          r.gewicht === "stark" ? " · zählt stark" : "", r.uebernehmen ? ` · übernehmen: ${r.uebernehmen}` : "")))) : null,
    h("dl", { class: "angaben" },
      zeile("Verhältnis", w.weg === "referenz" ? BEZUG[w.bezug] + " den Referenzen" : ""),
      zeile("Wunsch", w.wunsch),
      w.track_wuensche.map((t) => zeile(`Song ${t.nr}`, t.text)),
      zeile("Zielalbum", w.ziel_release_slug), zeile("Titelwunsch", o.titelwunsch), zeile("Sprache", o.sprache),
      zeile("Gesang", { mit: "mit Gesang", instrumental: "instrumental", egal: "Claude entscheidet" }[o.gesang]),
      zeile("Nicht gewünscht", o.no_gos), zeile("Erzeugt mit", o.provider === "minimax" ? "MiniMax" : "Suno"),
      zeile("Tempo", o.tempo === "schnell" ? "Fast Mode" : ""),
      zeile("Plan vorher zeigen", o.planfreigabe === "an" ? "ja" : "nein"),
      zeile("Zusatzprüfung vor dem Senden", o.zweitgutachten === "aus" ? "ausgeschaltet" : "ja"),
      zeile("Folgeauftrag zu", order.vorgaenger_id ? h("a", { href: `#/auftrag/${order.vorgaenger_id}` }, order.vorgaenger_id) : "")));
}
