// Nachlauf für den Favoriten: Mastering, Ableton, Cover, Songbeschreibung, SoundCloud.
import { api } from "./api.js";
import { feld, h, leeren } from "./dom.js";
import { dateiInfo, fertigmachListe, takeName } from "./logic.js";
import { abspielKnopf, explorerKnopf } from "./player.js";
import { studioPult } from "./studio.js";

const ERLEDIGT = ["fertig", "ausgelassen"];
const STAND = { offen: "noch nicht dran", wartet: "wartet auf dich", beauftragt: "Claude ist dran", fertig: "erledigt", ausgelassen: "ausgelassen" };
const NR = { Mastering: 6, Cover: 7, "Songbeschreibung und Songtext": 8, SoundCloud: 9 };  // Stationen im Ablauf
const hinweis = (text) => h("p", { class: "hinweis" }, text);
// Ein Weg zum Master: links, was er tut, rechts der Knopf dazu.
const weg = (titel, text, ...aktion) => h("div", { class: "weg" }, h("div", {}, h("strong", {}, titel), hinweis(text)), aktion);
const dateiName = (pfad) => pfad.split("/").pop();
let analyseLaeuft = null;

// Karte einer Phase. Die vier Schritte bis zur Veröffentlichung tragen ihre Station als Nummer; alles ohne Nummer ist freiwillig.
function phase(titel, stand, ...inhalt) {
  const nr = NR[titel];
  return h("section", { class: `phase ${stand}${nr ? "" : " freiwillig"}`, "aria-label": titel },
    h("h3", {}, h("span", {}, nr ? h("span", { class: "nr" }, String(nr)) : null, titel),
      h("span", { class: "phase-stand" }, !nr && stand === "offen" ? "freiwillig" : STAND[stand] || stand)), inhalt);
}

function messwerte(e) {
  return `${e.lufs.toFixed(1)} LUFS · Spitze ${e.spitze.toFixed(1)} dBTP · Dynamik ${e.spanne.toFixed(1)} LU`;
}

function mastering(order, { tun, neuLaden }) {
  const n = order.nachlauf;
  const info = order.nachlauf_info;
  const m = n.mastering;
  const nehmen = (datei) => h("button", { type: "button", class: "klein-knopf", disabled: m.datei === datei,
    onclick: () => tun("master", { weg: "datei", datei }) }, m.datei === datei ? "gewählt" : "Diesen Master nehmen");
  const referenz = h("select", { "data-key": "studio-referenz" },
    order.wunsch.referenzen.filter((r) => r.pfad !== n.favorit).map((r) => h("option", { value: r.pfad }, `${r.titel} – ${takeName(r.pfad)}`)));
  const liste = (eintraege) => h("ul", { class: "takes" }, eintraege);
  if (!m.analyse && info.werkzeuge.analyse && analyseLaeuft !== `${order.id}|${n.favorit}`) {
    analyseLaeuft = `${order.id}|${n.favorit}`; // einmal je Song von selbst vermessen
    tun("analyse").then((ok) => { if (!ok) analyseLaeuft = null; });
  }
  // Knopf, der während des Renderns im Dienst gesperrt bleibt.
  const lang = (text, laeuft, body) => h("button", { type: "button", class: "knopf zweit", onclick: async (e) => {
    e.target.disabled = true; e.target.textContent = laeuft;
    if (!(await tun("studio", body()))) { e.target.disabled = false; e.target.textContent = text; }
  } }, text);
  const wahl = h("div", {},
    m.entwuerfe.length ? [h("h4", {}, "Deine Master-Entwürfe"),
      liste(m.entwuerfe.map((e) => h("li", { class: "take" },
        h("div", { class: "take-kopf" }, abspielKnopf(e.datei), h("strong", {}, dateiName(e.datei)), explorerKnopf(e.datei), nehmen(e.datei)),
        h("span", { class: "klein" }, `${e.weg} · ${messwerte(e)}`),
        (e.hinweise || []).map((text) => h("span", { class: "klein" }, `Hinweis: ${text}`)))))] : null,
    studioPult(order, (einstellungen) => tun("studio", { einstellungen })),
    h("div", { class: "wege" },
      info.werkzeuge.phaselimiter
        ? weg("Automatisch mastern", "phaselimiter sucht Klang und Dynamik selbst und legt einen Entwurf zum Vergleichen an (etwa eine halbe Minute).",
          lang("Starten", "Mastert …", () => ({ automatik: -10.5 })))
        : weg("Automatisch mastern", "phaselimiter ist auf diesem Rechner nicht eingerichtet."),
      !info.werkzeuge.matchering ? weg("An einen Referenzsong angleichen", "Matchering ist auf diesem Rechner nicht installiert.")
        : !referenz.options.length ? weg("An einen Referenzsong angleichen", "Dieser Auftrag hat keinen anderen Referenzsong zum Angleichen.")
          : weg("An einen Referenzsong angleichen", "Matchering überträgt Klangbild und Lautheit der Referenz.",
            feld("Referenzsong", referenz), lang("Angleichen", "Gleicht an …", () => ({ referenz: referenz.value }))),
      h("details", { class: "weg", "data-auf": "eigene-datei" }, h("summary", {}, "Eigene Master-Datei verwenden"),
        hinweis("Eine anderswo gemasterte Datei in den Ordner des Songs (oder in „mastered“) legen. " +
          "Enthält der Dateiname den Songtitel und das Wort „Master“, erscheint sie hier."),
        h("p", { class: "pfad" }, info.favorit_absolut),
        liste(info.kandidaten.map((p) => h("li", { class: "take-kopf" }, abspielKnopf(p), h("span", {}, dateiName(p)), explorerKnopf(p), nehmen(p)))),
        h("button", { type: "button", class: "klein-knopf", onclick: neuLaden }, "Nach Master-Datei suchen")),
      weg("Ohne Mastering", "Der Favorit geht unverändert weiter.",
        h("button", { type: "button", class: "klein-knopf", onclick: () => tun("master", { weg: "ohne" }) }, "Ohne Mastering weiter"))));
  if (!ERLEDIGT.includes(m.stand)) return phase("Mastering", "wartet", wahl);
  return phase("Mastering", m.stand,
    m.datei ? h("p", { class: "take-kopf" }, abspielKnopf(m.datei), h("span", {}, `${dateiName(m.datei)} (${m.weg})`), explorerKnopf(m.datei)) : h("p", {}, "Ohne Mastering."),
    n.soundcloud.stand === "beauftragt" ? null
      : h("details", { "data-auf": "master-aendern" }, h("summary", {}, "Master ändern"), wahl));
}

function ableton(order, { tun }) {
  const a = order.nachlauf.ableton;
  return phase("Ableton", a.stand,
    hinweis("Legt die Endfassung in ein Ableton-Set. Gehört nicht zur Veröffentlichung."),
    a.notiz ? h("p", {}, a.notiz) : null,
    a.stand === "beauftragt" ? hinweis("Claude legt den Song in Ableton an.")
      : h("div", { class: "knopfzeile" },
        h("button", { type: "button", class: "knopf zweit", onclick: () => tun("ableton") },
          a.stand === "fertig" ? "Noch einmal nach Ableton exportieren" : "Nach Ableton exportieren"),
        h("span", { class: "hinweis" }, `Exportiert wird: ${dateiName(order.nachlauf_info.endfassung)}`)));
}

function cover(order, { tun, neuLaden, bereit }) {
  const n = order.nachlauf;
  const c = n.cover;
  const info = order.nachlauf_info;
  const oben = n.soundcloud.stand === "fertig";      // der Song liegt schon bei SoundCloud
  const laedt = n.soundcloud.stand === "beauftragt";
  const bild = c.datei ? h("img", { class: "cover", src: api.bildUrl(c.datei), alt: "Cover des Songs" }) : null;
  const ohne = oben ? null : h("button", { type: "button", class: "schlicht", onclick: () => tun("cover", { entscheidung: "ohne" }) }, "Ohne Cover weiter");
  const wunsch = h("input", { type: "text", "data-key": "cover-wunsch", placeholder: "z. B. dunkler, weniger Text" });
  const rest = info.max_cover - c.versuche;
  const zaehler = hinweis(rest > 0 ? `Jedes neue Cover ist eine weitere Bild-Erzeugung: ${c.versuche} von ${info.max_cover} sind verbraucht.`
    : `Alle ${info.max_cover} Bild-Erzeugungen für diesen Song sind verbraucht.`);
  // Frühere Cover und eigene Bilder aus dem Songordner: ohne neue Erzeugung wählbar.
  const andere = h("details", { "data-auf": "cover-datei" }, h("summary", {}, "Anderes Bild aus dem Songordner nehmen"),
    hinweis("Frühere Cover dieses Songs und eigene Bilder. Ein eigenes Bild in den Ordner des Songs legen; enthält der Dateiname den Songtitel, erscheint es hier."),
    h("ul", { class: "bilder" }, info.cover_kandidaten.map((pfad) => h("li", {},
      h("img", { src: api.bildUrl(pfad), alt: "", loading: "lazy" }), h("span", { class: "klein" }, dateiName(pfad)),
      h("button", { type: "button", class: "klein-knopf", onclick: () => tun("cover", { entscheidung: "datei", datei: pfad }) }, "Dieses Bild nehmen")))),
    h("div", { class: "knopfzeile" }, explorerKnopf(n.favorit), h("button", { type: "button", class: "klein-knopf", onclick: neuLaden }, "Nach Bildern suchen")));
  // Nach dem Annehmen (auch nach dem Upload): neues Cover von Claude oder ein anderes Bild.
  const aendern = (titel) => laedt ? hinweis("Der Song wird gerade hochgeladen. Danach lässt sich das Cover ändern.")
    : h("details", { "data-auf": "cover-aendern" }, h("summary", {}, titel),
      oben ? hinweis("Der Song liegt schon bei SoundCloud. Das neue Cover setzt du danach im Schritt SoundCloud mit einem Klick dort ein.") : null,
      rest > 0 ? [feld("Wunsch für ein neues Cover (freiwillig)", wunsch),
        h("div", { class: "knopfzeile" }, h("button", { type: "button", class: "knopf zweit",
          onclick: () => tun("cover", { entscheidung: "aendern", text: wunsch.value.trim() }) }, "Neues Cover von Claude"))] : null,
      zaehler, andere);
  if (c.stand === "offen") {
    return phase("Cover", bereit ? "beauftragt" : c.stand, hinweis(bereit ? "Claude erstellt das Cover." : "Kommt nach dem Mastering."),
      bereit && c.wunsch ? hinweis(`Dein Wunsch: ${c.wunsch}`) : null, h("div", { class: "knopfzeile" }, ohne));
  }
  if (c.stand === "wartet") {
    return phase("Cover", c.stand, bild, c.fehler ? h("p", { class: "fehler" }, `Nicht gelungen: ${c.fehler}`) : null,
      rest > 0 ? feld("Wunsch für ein neues Cover (freiwillig)", wunsch) : null, zaehler,
      h("div", { class: "knopfzeile" },
        c.datei ? h("button", { type: "button", class: "knopf", onclick: () => tun("cover", { entscheidung: "annehmen" }) }, "Cover annehmen") : null,
        rest > 0 ? h("button", { type: "button", class: "knopf zweit", onclick: () => tun("cover", { entscheidung: "neu", text: wunsch.value.trim() }) }, "Neues Cover") : null,
        ohne),
      andere);
  }
  if (c.stand === "ausgelassen") return phase("Cover", c.stand, h("p", {}, "Ohne Cover."), bereit ? aendern("Doch ein Cover") : null);
  return phase("Cover", c.stand, bild, aendern("Cover ändern"));
}

function text(order, { tun, bereit }) {
  const t = order.nachlauf.text;
  const wunsch = h("input", { type: "text", "data-key": "beschreibung-wunsch",
    placeholder: "z. B. prägnanter, andere Tags, kürzerer Songtext" });
  const aendern = ERLEDIGT.includes(t.stand) && bereit
    ? h("details", { class: "followup-options", "data-auf": "text-aendern" },
        h("summary", {}, "Beschreibung oder Songtext ändern"),
        feld("Was soll Claude ändern?", wunsch),
        h("button", { type: "button", class: "knopf zweit",
          onclick: () => tun("textedit", { wunsch: wunsch.value.trim() }) }, "Neue Fassung anfordern"))
    : null;
  return phase("Songbeschreibung und Songtext", t.stand === "offen" && bereit ? "beauftragt" : t.stand,
    t.stand === "fertig" ? [
      h("p", { class: "klein" }, "Aktuelle Textfassung: " + dateiName(t.datei)),
      t.tags.length ? h("p", { class: "chips" }, t.tags.map((tag) => h("span", { class: "chip" }, tag))) : null,
      h("details", { "data-auf": "beschreibung" }, h("summary", {}, "Beschreibung und Songtext lesen"),
        h("pre", { class: "songtext" }, t.beschreibung))]
      : hinweis(t.stand === "ausgelassen" ? "Noch keine Textfassung."
        : t.wunsch ? "Claude erstellt eine neue Fassung: " + t.wunsch
          : bereit ? "Claude erstellt die Beschreibung." : "Kommt nach dem Mastering."),
    aendern);
}

function soundcloud(order, { tun, neuLaden, bereit }) {
  const s = order.nachlauf.soundcloud;
  if (s.stand === "fertig") {
    const ersetzen = h("button", { type: "button", class: "knopf zweit", onclick: async () => {
      ersetzen.disabled = true; ersetzen.textContent = "Ersetzt …";
      await tun("soundcloud", { entscheidung: "cover" });
    } }, "Cover auf SoundCloud aktualisieren");
    const bestaetigen = (entscheidung, titel, warnung) => {
      const zeile = h("div", { class: "knopfzeile" });
      const knopf = h("button", { type: "button", class: "knopf zweit", onclick: () => {
        leeren(zeile).append(
          h("span", { class: "hinweis" }, warnung),
          h("button", { type: "button", class: "knopf", onclick: () => tun("soundcloud",
            { entscheidung, bestaetigt: true }) }, "Ja, bestätigen"),
          h("button", { type: "button", class: "schlicht", onclick: neuLaden }, "Abbrechen"));
      } }, titel);
      zeile.append(knopf);
      return zeile;
    };
    return phase("SoundCloud", s.cover_offen || s.audio_offen || s.text_offen ? "wartet" : s.stand,
      h("p", {}, h("a", { href: s.link, target: "_blank", rel: "noopener" }, "Veröffentlichten Song öffnen ↗")),
      s.cover_offen ? h("div", { class: "sync-notice" },
        h("strong", {}, "Cover auf SoundCloud veraltet"),
        s.cover_fehler ? h("p", { class: "fehler" }, s.cover_fehler) : null, ersetzen) : null,
      s.text_offen ? h("div", { class: "sync-notice" },
        h("strong", {}, "Beschreibung/Tags lokal geändert"),
        s.text_fehler ? h("p", { class: "fehler" }, s.text_fehler) : null,
        order.nachlauf.text.stand === "fertig"
          ? bestaetigen("metadaten", "Bestehenden SC-Track aktualisieren",
              "Beschreibung und Tags des vorhandenen Tracks ersetzen – keinen neuen Song hochladen?")
          : hinweis("Erst die neue Textfassung abwarten.")) : null,
      s.audio_offen ? h("div", { class: "sync-notice" },
        h("strong", {}, "Audio auf SoundCloud noch nicht ausgetauscht"),
        h("p", {}, "SoundCloud bietet den Audioaustausch nur über die eigene Oberfläche an. Öffne den bestehenden Song und ersetze dort die Datei, sofern dein Tarif dies erlaubt."),
        h("a", { href: s.link, target: "_blank", rel: "noopener" }, "Zum bestehenden Track"),
        bestaetigen("audio_bestaetigt", "Ich habe die Audiodatei dort ersetzt",
          "Wurde die Datei im bestehenden SoundCloud-Track wirklich erfolgreich ausgetauscht?")) : null);
  }
  if (s.stand === "beauftragt") return phase("SoundCloud", s.stand, hinweis("Claude lädt den Song hoch."));
  if (s.stand === "ausgelassen") return phase("SoundCloud", s.stand,
    h("p", {}, "Bisher bewusst nicht veröffentlicht."),
    h("button", { type: "button", class: "knopf zweit",
      onclick: () => tun("soundcloud", { entscheidung: "wieder_oeffnen" }) }, "Doch auf SoundCloud veröffentlichen"));
  if (!bereit) return phase("SoundCloud", s.stand, h("p", { class: "hinweis" }, "Kommt, sobald Master, Cover und Beschreibung stehen."));
  if (!order.nachlauf_info.werkzeuge.soundcloud) {
    return phase("SoundCloud", "wartet",
      h("p", { class: "fehler" }, "SoundCloud ist auf diesem Rechner noch nicht eingerichtet."),
      hinweis("In der Datei .env im Ordner von Sirens SOUNDCLOUD_CLIENT_ID und SOUNDCLOUD_CLIENT_SECRET eintragen, dann einmal im Projektordner „py -3.11 scripts/soundcloud_auth.py“ ausführen und diese Seite neu laden."),
      h("div", { class: "knopfzeile" },
        h("button", { type: "button", class: "schlicht", onclick: () => tun("soundcloud", { entscheidung: "ohne" }) }, "Nicht hochladen")));
  }
  const oeffentlich = h("input", { type: "checkbox", id: "sc-oeffentlich" });
  return phase("SoundCloud", "wartet",
    s.fehler ? h("p", { class: "fehler" }, `Der letzte Versuch ist gescheitert: ${s.fehler}`) : null,
    h("p", {}, `Hochgeladen wird ${dateiName(order.nachlauf_info.endfassung)} mit Cover, Beschreibung, Songtext und Tags.`),
    h("div", { class: "schalter" }, oeffentlich, h("div", {}, h("label", { for: "sc-oeffentlich" }, "Öffentlich veröffentlichen"),
      h("p", { class: "hinweis" }, "Ohne Haken bleibt der Song privat."))),
    hinweis("Promotion lässt sich nur bei SoundCloud selbst einschalten; nach dem Upload steht hier der Link dorthin."),
    h("div", { class: "knopfzeile" },
      h("button", { type: "button", class: "knopf", onclick: (e) => {
        // Zweiter Schritt: erst nach ausdrücklicher Bestätigung wird hochgeladen.
        const zeile = e.target.parentElement;
        const sicht = oeffentlich.checked ? "oeffentlich" : "privat";
        leeren(zeile).append(
          h("strong", {}, `Wirklich bei SoundCloud hochladen, ${sicht === "oeffentlich" ? "ÖFFENTLICH" : "privat"}?`),
          h("button", { type: "button", class: `knopf${sicht === "oeffentlich" ? " gefahr" : ""}`,
            onclick: () => tun("soundcloud", { entscheidung: "hochladen", sichtbarkeit: sicht, bestaetigt: true }) }, "Ja, hochladen"),
          h("button", { type: "button", class: "schlicht", onclick: neuLaden }, "Abbrechen"));
      } }, "Bei SoundCloud hochladen …"),
      h("button", { type: "button", class: "schlicht", onclick: () => tun("soundcloud", { entscheidung: "ohne" }) }, "Nicht hochladen")));
}

function versionFrage(order, { tun, neuLaden }) {
  const offen = [
    ["version_entscheidung", "Master"],
    ["cover_entscheidung", "Cover"],
    ["text_entscheidung", "Text"]
  ].filter(([key]) => Boolean(order.nachlauf[key]));
  if (!offen.length) return null;
  return h("div", { class: "version-questions breit" }, offen.map(([key, art]) => {
    const v = order.nachlauf[key];
    const frage = h("div", { class: "knopfzeile" });
    frage.append(
      h("button", { type: "button", class: "knopf zweit",
        onclick: () => tun("version", { entscheidung: "behalten", pfad: v.alt }) }, "Behalten"),
      h("button", { type: "button", class: "knopf zweit", onclick: () => {
        leeren(frage).append(h("p", { class: "hinweis" },
          "Die alte Datei wird aus dem aktiven Songordner ins Sirens-Archiv verschoben, nicht endgültig gelöscht. Fortfahren?"),
          h("button", { type: "button", class: "knopf", onclick: () => tun("version",
            { entscheidung: "archivieren", pfad: v.alt, bestaetigt: true }) }, "Ja, archivieren"),
          h("button", { type: "button", class: "schlicht", onclick: neuLaden }, "Abbrechen"));
      } }, "Alte Fassung archivieren"));
    return h("section", { class: "version-prompt" },
      h("strong", {}, "Neue " + art + "-Fassung – alte Version behalten?"),
      h("p", {}, "Bisher: " + dateiName(v.alt) + " · Aktuell: " + dateiName(v.neu)),
      frage, h("p", { class: "version-archive-note" },
        "Quellaufnahmen und noch verwendete Veröffentlichungen sind geschützt."));
  }));
}

const fertigVon = (n) => ["mastering", "cover", "text", "soundcloud"].filter((p) => ERLEDIGT.includes(n[p].stand)).length;

// Alle Songs des Auftrags, die fertig gemacht werden: wechseln, einen weiteren Favoriten dazunehmen, zurück zum Anhören.
function songLeiste(order, { tun }) {
  const n = order.nachlauf;
  if (n.vorhanden || n.nur_mastern) return null;
  const liste = fertigmachListe(order);  // feste Reihenfolge wie im Album
  const mehr = order.tracks_stand.filter((t) => (t.dateien || []).length).length > liste.filter((s) => s.nachlauf).length;
  return h("nav", { class: "songleiste breit", "aria-label": "Songs, die fertig gemacht werden" },
    h("div", { class: "songwahl" }, liste.map((s) =>
      h("button", { type: "button", class: `songknopf${s.nachlauf ? "" : " neu"}`, "aria-pressed": String(s.aktiv), disabled: s.aktiv,
        onclick: () => tun("nachlauf", { pfad: s.pfad }) },
        h("strong", {}, `${dateiInfo(s.pfad).titel} – ${takeName(s.pfad)}`),
        h("span", { class: "klein" }, !s.nachlauf ? "Favorit – jetzt auch fertig machen"
          : s.nachlauf.soundcloud.link ? "bei SoundCloud" : `${fertigVon(s.nachlauf)} von 4 erledigt`)))),
    h("div", { class: "knopfzeile" },
      h("button", { type: "button", class: "knopf zweit", onclick: () => tun("anhoeren") }, "Zurück zum Anhören"),
      hinweis(mehr ? "Dort markierst du bei weiteren Songs einen Favoriten und wählst „Fertig machen“. Der Stand hier bleibt erhalten; Claude arbeitet weiter."
        : "Der Stand hier bleibt erhalten; Claude arbeitet weiter.")));
}

// helfer: { tun(name, body), neuLaden() }
export function nachlaufAnsicht(order, helfer) {
  const n = order.nachlauf;
  const masterDa = ERLEDIGT.includes(n.mastering.stand);
  const allesDa = masterDa && ERLEDIGT.includes(n.cover.stand) && ERLEDIGT.includes(n.text.stand);
  const master = mastering(order, helfer);
  if (!masterDa) master.classList.add("breit");  // das Studio braucht die ganze Breite
  const gruppe = (titel, zusatz, ...karten) => h("section", { class: "gruppe", "aria-label": titel },
    h("p", { class: "gruppen-titel" }, titel, h("span", { class: "hinweis" }, zusatz)), karten);
  const export_ = ableton(order, helfer);
  export_.classList.add("breit");
  return h("div", { class: "nachlauf" },
    songLeiste(order, helfer),
    h("p", { class: "take-kopf" }, abspielKnopf(n.favorit), h("strong", {}, (n.vorhanden || n.nur_mastern) ? "Song:" : "Favorit:"), h("span", {}, dateiName(n.favorit)), explorerKnopf(n.favorit)),
    versionFrage(order, helfer),
    gruppe("Schritte bis zur Veröffentlichung", "der Reihe nach; jeder wird erledigt oder bewusst ausgelassen",
      master, cover(order, { ...helfer, bereit: masterDa }), text(order, { ...helfer, bereit: masterDa }), soundcloud(order, { ...helfer, bereit: allesDa })),
    gruppe("Freiwillig", "jederzeit möglich, hält nichts auf", export_),
    h("div", { class: "knopfzeile" }, h("button", { type: "button", class: `knopf${allesDa && ERLEDIGT.includes(n.soundcloud.stand) ? "" : " zweit"}`, onclick: () => helfer.tun("abschliessen") }, "Auftrag abschließen")));
}
