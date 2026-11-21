// Ansicht „Neuer Auftrag“: alles auf einer Seite, Entwurf wird beim Tippen zwischengespeichert.
import { api } from "./api.js";
import { feld, fehlerZeigen, h, knopfReihe, leeren, meldung, neueId } from "./dom.js";
import { BEZUG_WAHL, fehlend, fehlerFeld, hatRichtungswort, leererWunsch, referenzenErgaenzen, richtungswortUmschalten, zusammenfassung } from "./logic.js";
import { referenzAuswahl } from "./katalog.js";
import { optionenBlock, referenzKarten, trackWuensche } from "./neu_teile.js";
import { ablaufListe } from "./auftrag_teile.js";

const merkKuenstler = {
  lesen: () => { try { return localStorage.getItem("sirens.kuenstler") || localStorage.getItem("song-auftrag.kuenstler") || ""; } catch { return ""; } },
  setzen: (slug) => { try { localStorage.setItem("sirens.kuenstler", slug); } catch { /* ohne Speicher */ } },
};

export function neuAnsicht(el, id) {
  let w = leererWunsch(merkKuenstler.lesen());
  let auftragId = id || null;
  let revision = null;
  let schmutzig = false;
  let kette = Promise.resolve();
  let timer = null;
  let beendet = false;
  let auswahl = null;
  let zeichneAlles = () => {};
  const gespeichert = h("span", { class: "klein", "aria-live": "polite" });

  const daten = () => ({ ...w,
    artist_slug: w.artist_slug.trim(),
    referenzen: w.referenzen.map((r) => ({ pfad: r.pfad, gewicht: r.gewicht || "normal", uebernehmen: r.uebernehmen || "" })),
    track_wuensche: w.track_wuensche.filter((t) => t.text.trim() && t.nr >= 1 && t.nr <= 20) });

  function speichern() {
    clearTimeout(timer);
    kette = kette.then(async () => {
      if (!schmutzig) return;
      schmutzig = false;
      for (let versuch = 0; versuch < 2; versuch += 1) {
        try {
          const order = auftragId ? await api.aendern(auftragId, revision, daten()) : await api.anlegen(daten());
          auftragId = order.id;
          revision = order.revision;
          if (!beendet) history.replaceState(null, "", `#/neu/${auftragId}`);
          gespeichert.textContent = `Entwurf ${auftragId} ist gespeichert und steht unter „Aufträge“.`;
          return;
        } catch (fehler) {
          if (fehler.error === "revision_conflict" && versuch === 0) {
            revision = (await api.lesen(auftragId)).revision;
            continue;
          }
          gespeichert.textContent = "";
          if (!fehlerZeigen(el, fehlerFeld(fehler.feld), fehler.meldung)) meldung(fehler.meldung, "fehler");
          throw fehler;
        }
      }
    });
    const ergebnis = kette;
    kette = kette.catch(() => {});
    return ergebnis;
  }

  function geaendert() {
    schmutzig = true;
    zeichneAlles();
    clearTimeout(timer);
    timer = setTimeout(() => speichern().catch(() => {}), 800);
  }

  function bauen(woerter, vorgaengerId) {
    const kuenstlerListe = h("datalist", { id: neueId("liste") });
    const releaseListe = h("datalist", { id: neueId("liste") });
    let katalog = null;
    const releasesSetzen = () => {
      const artist = katalog?.artists.find((a) => a.slug === w.artist_slug.trim());
      leeren(releaseListe).append(...(artist ? artist.releases.map((r) => h("option", { value: r.slug })) : []));
    };
    api.katalog().then((k) => {
      katalog = k;
      kuenstlerListe.append(...k.kuenstler.map((slug) => h("option", { value: slug })));
      releasesSetzen();
    }).catch(() => {});

    // 1. Weg
    const kachel = (wert, titel, text) => h("button", { type: "button", class: "kachel", "data-weg": wert,
      onclick: () => { w.weg = wert; geaendert(); } }, h("strong", {}, titel), h("span", {}, text));
    const wege = h("div", { class: "kacheln", role: "group", "aria-label": "Wie soll der Auftrag entstehen?" },
      kachel("referenz", "Wie diese Songs", "Du wählst vorhandene Songs als Vorbild."),
      kachel("beschreibung", "Ich beschreibe es", "Du schreibst, was entstehen soll. Claude deutet es mit deinem Geschmack."));

    // 2. Umfang
    const anzahl = h("input", { type: "number", min: 2, max: 20, class: "schmal", value: w.track_count ?? "", placeholder: "–",
      oninput: (e) => {
        const n = Number(e.target.value);
        w.track_count = Number.isInteger(n) && n >= 2 && n <= 20 ? n : null;
        fehlerZeigen(anzahlFeld, "track_count", e.target.value && w.track_count == null ? "Zwischen 2 und 20, oder leer lassen." : "");
        geaendert();
      } });
    const anzahlFeld = feld("Anzahl Songs", anzahl, { hinweis: "leer = Claude entscheidet", name: "track_count" });
    const umfang = knopfReihe("Umfang", [["song", "Song"], ["album", "Album"]], w.umfang, (wert) => { w.umfang = wert; geaendert(); });

    // 3. Künstler
    const kuenstler = h("input", { type: "text", list: kuenstlerListe.id, value: w.artist_slug, autocomplete: "off",
      oninput: (e) => { w.artist_slug = e.target.value; releasesSetzen(); geaendert(); } });

    // 4. Referenzen (nur Weg 1)
    const karten = referenzKarten(w, () => { auswahl.auffrischen(); geaendert(); });
    auswahl = referenzAuswahl({
      gewaehlt: () => w.referenzen.map((r) => r.pfad),
      hinzu: (pfade) => {
        const { referenzen, uebrig } = referenzenErgaenzen(w.referenzen, pfade);
        w.referenzen.splice(0, w.referenzen.length, ...referenzen);
        if (uebrig) meldung(`Höchstens 12 Referenzen: ${uebrig} wurden nicht übernommen.`, "fehler");
        karten.zeichnen();
        geaendert();
      },
    });
    const bezug = knopfReihe("Verhältnis zu den Referenzen", BEZUG_WAHL.map(([wert, text]) => [wert, text]), w.bezug,
      (wert) => { w.bezug = wert; geaendert(); });
    const referenzTeil = h("section", { class: "block", "aria-label": "Referenzen" },
      h("h2", {}, "Welche Songs sind das Vorbild?"), auswahl, karten.el,
      h("p", { class: "fehler", role: "alert", hidden: true, "data-fehler": "referenzen" }),
      h("div", { class: "feld" }, h("span", { class: "label" }, "Der neue Song ist …"), bezug,
        h("p", { class: "hinweis" }, "„im Stil von“ trifft den Charakter, „Fortsetzung“ führt den Song weiter, „Neufassung“ macht denselben Song neu.")));

    // 5. Text und Richtungswörter
    const textLabel = h("label", {});
    const text = h("textarea", { rows: 4, value: w.wunsch, oninput: (e) => { w.wunsch = e.target.value; geaendert(); } });
    text.id = neueId();
    textLabel.setAttribute("for", text.id);
    const chips = h("div", { class: "chips", role: "group", "aria-label": "Richtungswörter" }, woerter.map((wort) =>
      h("button", { type: "button", class: "chip", "data-wort": wort, onclick: () => {
        w.wunsch = richtungswortUmschalten(w.wunsch, wort);
        text.value = w.wunsch;
        geaendert();
      } }, wort)));

    // 6.–7. Songwünsche und weitere Angaben
    const wuensche = trackWuensche(w, geaendert);
    const optionen = optionenBlock(w, geaendert, releaseListe);

    // 8. Zusammenfassung und Knöpfe
    const satz = h("p", { class: "zusammenfassung", "aria-live": "polite" });
    const ablauf = h("div", {});
    let ablaufStand = "";
    const ablaufLaden = async () => {
      const stand = JSON.stringify([w.umfang, w.optionen.tempo, w.optionen.planfreigabe, w.optionen.zweitgutachten]);
      if (stand === ablaufStand) return;
      ablaufStand = stand;
      try {
        const schritte = (await api.ablauf(w)).schritte;
        if (stand === ablaufStand) leeren(ablauf).append(ablaufListe(schritte));
      } catch { ablaufStand = ""; }
    };
    const ablaufVorschau = h("details", { class: "ablauf-vorschau", ontoggle: (e) => { if (e.target.open) ablaufLaden(); } },
      h("summary", {}, "So läuft die Produktion ab"), ablauf);
    const abschicken = h("button", { type: "button", class: "knopf gross", onclick: async () => {
      const luecken = fehlend(w);
      fehlerZeigen(el, "", "");
      if (luecken.length) { fehlerZeigen(el, luecken[0].feld, luecken[0].meldung); return; }
      abschicken.disabled = true;
      try {
        schmutzig = true;
        await speichern();
        await api.aktion(auftragId, "abschicken", revision);
        merkKuenstler.setzen(w.artist_slug.trim());
        beendet = true;
        location.hash = `#/auftrag/${auftragId}`;
      } catch (fehler) {
        if (!fehlerZeigen(el, fehlerFeld(fehler.feld), fehler.meldung)) meldung(fehler.meldung, "fehler");
      } finally { abschicken.disabled = false; }
    } }, "Auftrag starten →");
    const verwerfen = h("button", { type: "button", class: "schlicht", onclick: async () => {
      clearTimeout(timer);
      schmutzig = false;
      beendet = true;
      try { if (auftragId) await api.aktion(auftragId, "abbrechen", revision); } catch (f) { meldung(f.meldung, "fehler"); }
      location.hash = "#/";
    } }, "Verwerfen");

    zeichneAlles = () => {
      for (const k of wege.children) k.setAttribute("aria-pressed", String(k.dataset.weg === w.weg));
      const album = w.umfang === "album";
      anzahlFeld.hidden = !album;
      wuensche.el.hidden = !album;
      optionen.zielZeigen(!album);
      referenzTeil.hidden = w.weg !== "referenz";
      textLabel.textContent = w.weg === "referenz" ? "Was soll anders sein? (freiwillig)" : "Was soll entstehen?";
      text.placeholder = w.weg === "referenz" ? "z. B. treibender, weniger Gesang, mehr Bass-Druck"
        : "z. B. ein lustiges Electro-Funk-Album über Büroalltag, tanzbar, mit trockenem Humor";
      for (const c of chips.children) c.setAttribute("aria-pressed", String(hatRichtungswort(w.wunsch, c.dataset.wort)));
      satz.textContent = zusammenfassung(w);
      if (ablaufVorschau.open) ablaufLaden();
    };

    el.append(
      h("header", { class: "seitenkopf" },
        h("p", { class: "eyebrow" }, "NEUE KREATION"),
        h("h1", {}, vorgaengerId ? "Deine nächste Idee." : "Was möchtest du erschaffen?"),
        h("p", { class: "dashboard-intro" }, "Ein paar Angaben genügen. Den Rest übernimmt Claude."),
        vorgaengerId ? h("p", { class: "hinweis" }, "Vorausgefüllt aus ", h("a", { href: `#/auftrag/${vorgaengerId}` }, vorgaengerId), ". Ändere, was du möchtest.") : ""),
      h("form", { class: "formular zweispaltig", onsubmit: (e) => e.preventDefault(), novalidate: true },
        h("div", {},
          h("section", { class: "block creation-start" }, h("h2", {}, "Wie starten wir?"), wege),
          h("section", { class: "block zeile" },
            h("div", { class: "feld" }, h("span", { class: "label" }, "Umfang"), umfang), anzahlFeld,
            feld("Künstlerprojekt", kuenstler, { name: "artist_slug", hinweis: "Unter diesem Namen wird deine Musik abgelegt." }), kuenstlerListe, releaseListe),
          referenzTeil,
          h("section", { class: "block creation-idea" },
            h("h2", {}, "Deine kreative Richtung"),
            h("div", { class: "feld" }, textLabel, text, h("p", { class: "fehler", role: "alert", hidden: true, "data-fehler": "wunsch" })),
            h("details", { class: "inspiration" }, h("summary", {}, "Inspiration hinzufügen"),
              h("p", { class: "hinweis" }, "Wähle passende Begriffe – sie ergänzen deinen Wunsch."), chips)),
          wuensche.el, optionen),
        // Bleibt beim Ausfüllen sichtbar: der Auftrag als Satz, Abschicken und was danach passiert.
        h("aside", { class: "block abschluss haftet", "aria-label": "Dein Auftrag" },
          h("p", { class: "eyebrow" }, "DEIN BRIEFING"),
          h("h2", {}, "Bereit, wenn du es bist."),
          satz,
          h("div", { class: "knopfzeile" }, abschicken, verwerfen),
          gespeichert,
          ablaufVorschau)));
    zeichneAlles();
  }

  const beimVerstecken = () => { if (document.hidden && schmutzig) speichern().catch(() => {}); };
  document.addEventListener("visibilitychange", beimVerstecken);

  (async () => {
    let woerter = [];
    let vorgaengerId = null;
    try {
      woerter = (await api.einstellungen()).richtungswoerter;
      if (id) {
        const order = await api.lesen(id);
        if (order.status !== "entwurf") { location.hash = `#/auftrag/${id}`; return; }
        w = order.wunsch;
        revision = order.revision;
        vorgaengerId = order.vorgaenger_id;
      }
    } catch (fehler) {
      el.append(h("p", { class: "fehler", role: "alert" }, fehler.meldung), h("p", {}, h("a", { href: "#/" }, "Zu den Aufträgen")));
      return;
    }
    if (!beendet) bauen(woerter, vorgaengerId);
  })();

  return async () => {
    document.removeEventListener("visibilitychange", beimVerstecken);
    auswahl?.beenden();
    const offen = schmutzig && !beendet;
    beendet = true;
    if (offen) await speichern().catch(() => {});
  };
}
