// Prüft die reinen Funktionen der Seite. Aufruf: node --test tests/logic.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import * as L from "../web/js/logic.js";
import { katalogEintraege } from "../web/js/live_lab.js";
import * as DJ from "../web/js/auto_logic.js";

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

test("Spielwiese: Filter aus der Position, Hüllkurve, Lieblingssongs", () => {
  assert.deepEqual(L.spielFilter(0.5), { tief: 20000, hoch: 20 });
  assert.deepEqual([L.spielFilter(0), L.spielFilter(1), L.spielFilter(-3)], [{ tief: 200, hoch: 20 }, { tief: 20000, hoch: 4000 }, { tief: 200, hoch: 20 }]);
  assert.ok(L.spielFilter(0.2).tief < L.spielFilter(0.4).tief && L.spielFilter(0.6).hoch < L.spielFilter(0.9).hoch);
  const daten = new Float32Array(64); daten[0] = -0.5; daten[48] = 0.9;
  assert.deepEqual(L.spitzen(daten, 2).map((v) => Math.round(v * 10) / 10), [0.5, 0.9]);
  const katalog = { artists: [{ slug: "cco", releases: [{ songs: [
    { titel: "A", dateien: [{ pfad: "a1.mp3", bewertung: { score: 1 } }, { pfad: "a2.mp3", bewertung: { score: 2 } }, { pfad: "a3.wav", bewertung: { score: 2 } }] },
    { titel: "B", dateien: [{ pfad: "b1.mp3" }, { pfad: "b2.wav", bewertung: { score: 2 } }] }] }] }] };
  assert.deepEqual(L.lieblingsDateien(katalog), [{ pfad: "a2.mp3", titel: "A", artist: "cco", achsen: null }]);
  assert.deepEqual(L.lieblingsDateien({}), []);
});

test("Live Lab liest nur vorhandene Audio-Dateien aus dem Katalogbaum", () => {
  const daten = { artists: [{ slug: "Nova", releases: [{ slug: "Echo", songs: [
    { titel: "Pulse", dateien: [
      { pfad: "Nova/Echo/Pulse 1.mp3", fassung: "Original" },
      { pfad: "Nova/Echo/Pulse 2.wav", fassung: "Master" }
    ] }
  ] }] }] };
  assert.deepEqual(katalogEintraege(daten), [
    { pfad: "Nova/Echo/Pulse 1.mp3", text: "Nova · Pulse (Original)" },
    { pfad: "Nova/Echo/Pulse 2.wav", text: "Nova · Pulse (Master)" }
  ]);
  assert.deepEqual(katalogEintraege({ artists: [] }), []);
  assert.deepEqual(katalogEintraege({}), []);
});

test("Emblem: Achsen aus Profil und Schätzung, Tempo aus dem Klang, Farben aus Wärme und Dunkelheit", () => {
  assert.equal(L.ACHSEN.length, 12);
  const werte = L.achsenWerte({ energy: 8, warmth: 12 }, { energy: 2, darkness: 3 });
  assert.deepEqual([werte[0], werte[3], werte[4], werte[5]], [8, 10, 3, 5]);  // Profil vor Schätzung vor Mitte, begrenzt auf 0–10
  const rate = 8000; const klick = new Float32Array(rate * 20);
  for (let s = 0; s < 40; s += 1) for (let i = 0; i < 400; i += 1) klick[s * rate / 2 + i] = Math.sin(i / 3) * (1 - i / 400);  // Schlag alle 0,5 s
  const profil = L.klangProfil(klick, rate);
  assert.ok(Math.abs(profil.bpm - 120) <= 2, `bpm ${profil.bpm}`);
  assert.ok(profil.danceability > 5 && profil.energy >= 0 && profil.energy <= 10);
  const leise = L.klangProfil(new Float32Array(rate * 5), rate);
  assert.deepEqual([leise.energy, leise.danceability], [0, 0]);
  const kalt = L.emblemFarben(L.achsenWerte({ warmth: 0, darkness: 0 }));
  const warm = L.emblemFarben(L.achsenWerte({ warmth: 10, darkness: 0 }));
  assert.ok(kalt.haupt[2] > kalt.haupt[0] && warm.haupt[0] > warm.haupt[2]);      // kalt = blau, warm = orangerot
  const mitte = L.emblemFarben(L.achsenWerte({ warmth: 5 }));
  assert.ok(mitte.haupt[1] < mitte.haupt[0] && mitte.haupt[1] < mitte.haupt[2]);  // Mitte = Violett, nie Grün
  const hell = (f) => f.haupt.reduce((a, b) => a + b);
  assert.ok(hell(L.emblemFarben(L.achsenWerte({ darkness: 10 }))) < hell(L.emblemFarben(L.achsenWerte({ darkness: 0 }))));
});


test("Auto-DJ wählt aus Favoriten und entfernt doppelte Versionen", () => {
  const data={artists:[{slug:"Artist",releases:[{slug:"Set",songs:[
    {titel:"A",dateien:[
      {pfad:"Artist/Set/A-1.mp3",bewertung:{score:1},fassung:"Original"},
      {pfad:"Artist/Set/A-2.wav",bewertung:{score:2},fassung:"Master"}]},
    {titel:"B",dateien:[{pfad:"Artist/Set/B.mp3",bewertung:{score:0}}]}
  ]}]}]};
  const songs=DJ.katalogSongs(data);
  assert.equal(songs.length,2);
  assert.equal(songs[0].rating,2);
  assert.equal(songs[0].pfad,"Artist/Set/A-2.wav");
  assert.deepEqual(DJ.katalogSongs({}),[]);
});

test("Auto-DJ synchronisiert Taktraster und beurteilt Phrasenpaare", () => {
  assert.equal(DJ.naechsterTakt(19.8,{beat0:0,bpm:120}),20);
  assert.ok(DJ.tempoAngleichung(125,120).kompatibel);
  const a={bpm:120,duration:180,confidence:.8,phrase_confidence:.6,
    cues_out:[{zeit:100,score:.82,energie:.3,grund:"Break"}]};
  const b={bpm:125,duration:180,confidence:.8,phrase_confidence:.7,
    cues_in:[{zeit:8,score:.9,energie:.4,grund:"Aufbau"}]};
  const cue=DJ.findeUebergang(a,b,30,8);
  assert.ok(cue);
  assert.equal(cue.startA,100);
  assert.equal(cue.startB,8);
  assert.ok(Math.abs(cue.rateB-.96)<.01);
  assert.ok(cue.dauer>15);
  assert.equal(DJ.findeUebergang(a,{...b,bpm:45},30,8),null);
});

test("Auto-DJ klassifiziert geschätzte Dynamik und vermeidet direkte Wiederholungen", () => {
  const tags=DJ.klassifizierung({bpm:124,timeline:[
    {phase:"Aufbau / Energieanstieg",energie:.9},
    {phase:"Break / Energieabfall",energie:.2}]});
  assert.ok(tags.includes("Breaks"));
  assert.ok(tags.includes("Build-ups"));
  const songs=[{pfad:"a",rating:1},{pfad:"b",rating:2},{pfad:"c",rating:0}];
  assert.notEqual(DJ.waehleNaechsten(songs,["a"],120,()=>0).pfad,"a");
});


test("Auto-DJ komponiert Energieverläufe über mehrere Songs",()=>{
  const initial=DJ.setEnergieZiel("aufbau",0);
  const spaeter=DJ.setEnergieZiel("aufbau",5);
  assert.ok(spaeter>initial);
  assert.ok(DJ.setEnergieZiel("chill",4)<DJ.setEnergieZiel("peak",4));
  const welle=Array.from({length:8},(_,i)=>DJ.setEnergieZiel("welle",i));
  assert.ok(Math.max(...welle)-Math.min(...welle)>.35);
});
