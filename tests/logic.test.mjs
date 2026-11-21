// Prüft die reinen Funktionen der Seite. Aufruf: node --test tests/logic.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import * as L from "../web/js/logic.js";

const lage = (dran, extra = {}) => ({ dran, claude_auch_dran: dran === "claude", station: 1, offene_bewertungen: 0, ...extra });

test("Zusammenfassungssatz ändert sich mit den Angaben", () => {
  const w = L.leererWunsch("cco");
  assert.equal(L.zusammenfassung(w), "Song für cco, noch ohne Referenz");
  w.umfang = "album"; w.track_count = 8; w.wunsch = "treibender, dreckiger";
  w.referenzen = [{ pfad: "a/b/X - Version 1.mp3" }, { pfad: "a/b/Y - Version 1.mp3" }, { pfad: "a/b/Z - Version 1.mp3" }];
  assert.equal(L.zusammenfassung(w), "Album mit 8 Songs für cco, im Stil von 3 Referenzen, treibender, dreckiger");
  w.bezug = "fortsetzung"; w.referenzen.length = 1; w.track_count = null; w.wunsch = "";
  assert.equal(L.zusammenfassung(w), "Album für cco, als Fortsetzung von 1 Referenz");
  const b = { ...L.leererWunsch(), weg: "beschreibung" };
  assert.equal(L.zusammenfassung(b), "Song, Beschreibung fehlt noch");
  b.wunsch = "Funk"; b.ziel_release_slug = "lab-notes"; b.optionen.planfreigabe = "an"; b.optionen.gesang = "instrumental";
  assert.equal(L.zusammenfassung(b), "Song im Album lab-notes, nach deiner Beschreibung: Funk, instrumental, Plan vorher zeigen");
  assert.ok(L.zusammenfassung({ ...b, wunsch: "x".repeat(200) }).includes("x…"));
  b.optionen.tempo = "schnell";
  assert.equal(L.zusammenfassung(b), "Song im Album lab-notes, nach deiner Beschreibung: Funk, instrumental, Fast Mode");
});

test("fehlende Pflichtangaben", () => {
  assert.deepEqual(L.fehlend(L.leererWunsch()).map((f) => f.feld), ["artist_slug", "referenzen"]);
  assert.deepEqual(L.fehlend({ ...L.leererWunsch("cco"), weg: "beschreibung" }).map((f) => f.feld), ["wunsch"]);
  assert.deepEqual(L.fehlend({ ...L.leererWunsch("cco"), weg: "beschreibung", wunsch: "Funk" }), []);
});

test("Richtungswörter ergänzen und entfernen", () => {
  assert.equal(L.richtungswortUmschalten("", "treibender"), "treibender");
  assert.equal(L.richtungswortUmschalten("mehr Hall", "treibender"), "mehr Hall, treibender");
  assert.equal(L.richtungswortUmschalten("mehr Hall, Treibender , dreckiger", "treibender"), "mehr Hall, dreckiger");
  assert.equal(L.hatRichtungswort("mehr Funk, lustiger", "Lustiger"), true);
  assert.equal(L.hatRichtungswort("viel lustiger", "lustiger"), false);
});

test("Status → Anzeige und Gruppen der Startansicht", () => {
  assert.deepEqual(["nutzer", "claude", "laeuft", "niemand"].map((d) => L.anzeige(lage(d)).text),
    ["Du bist dran", "Claude ist dran", "Läuft", "Erledigt"]);
  const a = (id, status, dran, extra) => ({ id, status, lage: lage(dran, extra) });
  const g = L.gruppen([a(1, "entwurf", "nutzer"), a(2, "fertig", "nutzer", { claude_auch_dran: true }), a(3, "offen", "claude"),
    a(4, "rueckfrage", "nutzer"), a(5, "gesendet", "laeuft"), a(6, "abgeschlossen", "niemand"), a(7, "plan_wartet", "nutzer")]);
  assert.deepEqual(g.nutzer.map((x) => x.id), [4, 7, 2, 1]);
  assert.deepEqual(g.claude.map((x) => x.id), [2, 3]);
  assert.deepEqual([g.laeuft.map((x) => x.id), g.erledigt.map((x) => x.id)], [[5], [6]]);
});

test("Dateinamen lesen, ohne zu raten", () => {
  assert.deepEqual(L.dateiInfo("cco/lab/mastered/Too Tidy - Version 1 PreMix (eMastered).wav"),
    { artist: "cco", release: "lab", unterordner: "mastered", titel: "Too Tidy", version: 1, fassung: "PreMix (eMastered)" });
  assert.deepEqual(L.dateiInfo("cco/lab/Loser Name.mp3"),
    { artist: "cco", release: "lab", unterordner: "", titel: "Loser Name", version: null, fassung: "" });
  assert.equal(L.takeName("cco/lab/mastered/Too Tidy - Version 2 Master.wav"), "Version 2 · Master · mastered");
  assert.equal(L.takeName("cco/lab/Loser Name.mp3"), "Loser Name");
});

test("Ein Ablauf: Stationen mit Schritten und Einträgen, Schrittleiste je Song", () => {
  const zustand = (s) => L.schrittLeiste(s).map((x) => x.zustand[0]).join("");
  assert.deepEqual(["geplant", "paket", "fertig", "fehler"].map(zustand), ["ooooo", "eaooo", "eeeee", "ooooo"]);
  const order = { status: "in_arbeit", verlauf: [{ text: "a" }, { text: "b" }, { text: "c" }],
    lage: { station: 2, stationen: ["Auftrag", "Klären", "Plan"], ausgelassen: [3], verlauf_station: [1, 2, 2],
      detail: [{ name: "lesen", station: 2 }, { name: "konzept", station: 3 }] } };
  const s = L.ablaufStationen(order);
  assert.deepEqual(s.map((x) => x.zustand), ["erledigt", "aktiv", "ausgelassen"]);
  assert.deepEqual(s.map((x) => x.eintraege.map((e) => e.text).join("")), ["a", "bc", ""]);
  assert.deepEqual(s.map((x) => x.schritte.map((e) => e.name).join("")), ["", "lesen", "konzept"]);
  assert.deepEqual(L.ablaufStationen({ ...order, status: "abgeschlossen" }).map((x) => x.zustand[0]).join(""), "eea");
  const stand = (s) => ({ stand: s });  // Cover nach dem Upload wieder offen: Text und SoundCloud bleiben abgehakt
  const nach = { status: "nachlauf", verlauf: [], nachlauf: { mastering: stand("fertig"), cover: stand("offen"), text: stand("fertig"), soundcloud: stand("fertig") },
    lage: { station: 7, stationen: "abcdefghij".split(""), ausgelassen: [] } };
  assert.equal(L.ablaufStationen(nach).map((x) => x.zustand[0]).join(""), "eeeeeeaeeo");
});

test("Referenzen wählen: bestes Take je Song, keine Doppelten, höchstens 12", () => {
  const release = { songs: [
    { titel: "A", dateien: [{ pfad: "a1" }, { pfad: "a2", bewertung: { score: 1 } }, { pfad: "a3", bewertung: { score: 2 } }] },
    { titel: "B", dateien: [{ pfad: "b1" }, { pfad: "b2" }] },
    { titel: "C", dateien: [{ pfad: "c1", bewertung: { score: -1 } }, { pfad: "c2" }] }] };
  assert.deepEqual(L.releaseReferenzen(release), ["a3", "b1", "c1"]);
  const erst = L.referenzenErgaenzen([{ pfad: "a3", gewicht: "stark", uebernehmen: "Bass" }], ["a3", "b1"]);
  assert.deepEqual(erst, { referenzen: [{ pfad: "a3", gewicht: "stark", uebernehmen: "Bass" }, { pfad: "b1", gewicht: "normal", uebernehmen: "" }], uebrig: 0 });
  const viele = L.referenzenErgaenzen([], Array.from({ length: 15 }, (_, i) => `p${i}`));
  assert.deepEqual([viele.referenzen.length, viele.uebrig], [12, 3]);
});

test("Songs zum Fertigmachen stehen in Albumreihenfolge, egal welcher gerade gezeigt wird", () => {
  const order = { tracks_stand: [{ dateien: ["a1", "a2"] }, { dateien: ["b1"] }, { dateien: ["c1"] }, {}],
    bewertungen: [{ pfad: "c1", favorit: true }, { pfad: "a2", favorit: true }, { pfad: "b1", favorit: false }],
    nachlauf: { favorit: "c1" }, nachlauf_weitere: [{ favorit: "a1" }] };
  const kurz = (o) => L.fertigmachListe(o).map((s) => `${s.pfad}${s.aktiv ? "*" : ""}${s.nachlauf ? "" : "?"}`).join(" ");
  assert.equal(kurz(order), "a1 a2? c1*");
  assert.equal(kurz({ ...order, nachlauf: { favorit: "a1" }, nachlauf_weitere: [{ favorit: "c1" }] }), "a1* a2? c1");
});

test("Vorausfüllen von Folgeaufträgen: Favorit, sonst bestbewertet, sonst erster Take", () => {
  const order = { tracks_stand: [{ nr: 1, dateien: ["a1", "a2"] }, { nr: 2, dateien: ["b1"] }, { nr: 3, dateien: [] }], bewertungen: [] };
  assert.deepEqual(L.folgeReferenzen(order), ["a1", "b1"]);
  assert.match(L.folgeHinweis(order), /erste Take/);
  order.bewertungen = [{ pfad: "a1", score: 0 }, { pfad: "a2", score: 2 }, { pfad: "b1", score: 2 }, { pfad: "fremd", score: 2 }];
  assert.deepEqual(L.folgeReferenzen(order), ["a2", "b1"]);
  assert.match(L.folgeHinweis(order), /2 bestbewerteten/);
  order.bewertungen[0].favorit = true;
  assert.deepEqual(L.folgeReferenzen(order), ["a1"]);
  assert.equal(L.folgeHinweis(order), "Dein Favorit wird die Referenz.");
});

test("Titel, Fehlerfelder, Bewertungstext", () => {
  const w = { ...L.leererWunsch("cco"), referenzen: [{ titel: "Too Tidy" }, { titel: "Omen" }] };
  assert.equal(L.auftragTitel({ titel: "", wunsch: w }), "Song wie „Too Tidy“ und 1 weitere");
  assert.equal(L.auftragTitel({ titel: "Neue Notizen", wunsch: w }), "Neue Notizen");
  assert.equal(L.auftragTitel({ titel: "", wunsch: { ...L.leererWunsch(), weg: "beschreibung", umfang: "album" } }), "Neues Album");
  assert.equal(L.fehlerFeld("referenzen[0].gewicht"), "referenzen");
  assert.equal(L.fehlerFeld("optionen.provider"), "provider");
  assert.equal(L.fehlerFeld(null), "");
  assert.deepEqual([-2, 0, 2].map(L.scoreText), ["−2", "0", "+2"]);
});
