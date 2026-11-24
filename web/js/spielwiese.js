// Spielwiese: Zeitvertreib, solange Claude arbeitet. Ein gut bewerteter Song läuft und lässt sich in Echtzeit verbiegen.
// Zwei Ansichten zum Umschalten: „Wellen“ (drei Bänder) und „Emblem“ (Grafikkarte; die zwölf Achsen des Songs
// bestimmen Form und Farbe und lassen sich am Achsenrad verziehen).
import { api } from "./api.js";
import { h, knopfReihe } from "./dom.js";
import { achsenWerte, emblemFarben, klangProfil, lieblingsDateien, spitzen } from "./logic.js";
import { achsenRad } from "./spiel_achsen.js";
import { emblemBild } from "./spiel_gl.js";
import { tonwerk } from "./spiel_ton.js";
import { baender, bildZustand, buehneMalen, uebersichtMalen } from "./spiel_bild.js";

let spiel = null; // bleibt über das Neuzeichnen der Seite erhalten, damit Ton und Bild nicht abreißen

// Knopf, der wirkt, solange er gedrückt ist (Maus, Finger oder Leertaste).
function halteKnopf(text, schalten) {
  const knopf = h("button", { type: "button", class: "spiel-halten", "aria-pressed": "false", title: "Gedrückt halten" }, text);
  const setzen = (an) => {
    if ((knopf.getAttribute("aria-pressed") === "true") === an) return;
    knopf.setAttribute("aria-pressed", String(an));
    schalten(an);
  };
  knopf.addEventListener("pointerdown", (e) => { try { knopf.setPointerCapture(e.pointerId); } catch { /* ohne Zeigerbindung */ } setzen(true); });
  for (const name of ["pointerup", "pointercancel", "lostpointercapture", "blur"]) knopf.addEventListener(name, () => setzen(false));
  knopf.addEventListener("keydown", (e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); setzen(true); } });
  knopf.addEventListener("keyup", (e) => { if (e.key === " " || e.key === "Enter") setzen(false); });
  return knopf;
}

function bauen() {
  const ton = tonwerk();
  const zustand = bildZustand();
  let songs = null;      // gut bewertete Songs aus dem Katalog
  let aktuell = null;
  let huelle = null;
  let zeiger = null;
  let frequenzen = null;
  let welle = null;
  let laufend = false;
  let laedt = false, generation = 0;
  let bilder = 0;
  let ansicht = (() => { try { return localStorage.getItem("sirens.spielansicht") === "emblem" ? "emblem" : "wellen"; } catch { return "wellen"; } })();
  let gl = null;                       // Emblem auf der Grafikkarte; entsteht beim ersten Umschalten
  let eigen = achsenWerte(null);       // Profil des Songs (zwölf Achsen, 0–10)
  let werte = [...eigen];              // was gerade gezeigt wird; am Rad verziehbar
  let bpm = 120;

  const titel = h("span", { class: "spiel-titel" }, "Spiel mit einem deiner gut bewerteten Songs.");
  const buehne = h("canvas", { class: "spiel-buehne", role: "img", "aria-label": "Wellenbild des laufenden Songs; Ziehen verändert den Klang" });
  const emblem = h("canvas", { class: "spiel-buehne", role: "img", "aria-label": "Emblem des laufenden Songs; Ziehen verändert den Klang" });
  const rad = achsenRad((nr, wert) => { werte[nr] = wert; });
  const eigenes = h("button", { type: "button", class: "spiel-halten", title: "Alle Achsen zurück auf das Profil des Songs",
    onclick: () => { werte = [...eigen]; } }, "Profil des Songs");
  const herkunft = h("span", {});
  const flaeche = h("div", { class: "spiel-flaeche" }, buehne, emblem, rad.el);
  const uebersicht = h("canvas", { class: "spiel-uebersicht", title: "Klicken springt an diese Stelle", "aria-hidden": "true" });
  const haupt = h("button", { type: "button", class: "knopf" }, "Lieblingssong spielen");
  const anderer = h("button", { type: "button", class: "knopf zweit", hidden: true }, "Anderer Song");
  const tempoWert = h("output", {}, "100 %");
  const tempo = h("input", { type: "range", min: 50, max: 150, step: 1, value: 100, "aria-label": "Tempo in Prozent", title: "Doppelklick setzt zurück" });
  const meldung = h("p", { class: "hinweis", role: "status" }, "Auf der Fläche ziehen: nach links wird es dumpf, nach rechts dünn, nach oben kommt Echo. ", herkunft);

  function zeigen(neu) {
    if (neu === "emblem" && !gl) gl = emblemBild(emblem);
    ansicht = neu === "emblem" && gl ? "emblem" : "wellen";
    try { localStorage.setItem("sirens.spielansicht", ansicht); } catch { /* ohne Speicher */ }
    flaeche.classList.toggle("emblem", ansicht === "emblem");
    buehne.hidden = ansicht === "emblem";
    for (const teil of [emblem, rad.el, eigenes, herkunft]) teil.hidden = ansicht !== "emblem";
    if (neu === "emblem" && !gl) meldung.append(" Das Emblem braucht WebGL 2; dieser Browser bietet es nicht.");
    schalter.setzen(ansicht);
  }
  const schalter = knopfReihe("Ansicht", [["wellen", "Wellen"], ["emblem", "Emblem"]], ansicht, zeigen, "klein");

  const beschriften = () => { haupt.textContent = laedt ? "Lädt …" : !ton.bereit ? "Lieblingssong spielen" : ton.laeuft ? "Pause" : "Weiter"; haupt.disabled = laedt; };

  async function naechster() {
    if (laedt) return;
    laedt = true; beschriften();
    const token = generation;
    try {
      songs ||= lieblingsDateien(await api.katalog("", 1));
      if (token !== generation || !el.isConnected) return;
      if (!songs.length) { meldung.textContent = "Noch kein gut bewerteter Song da. Bewerte einen Take mit +1 oder +2, dann spielt er hier."; return; }
      const wahl = songs.filter((s) => s.pfad !== aktuell?.pfad);
      aktuell = (wahl.length ? wahl : songs)[Math.floor(Math.random() * (wahl.length || songs.length))];
      titel.textContent = `${aktuell.titel} – wird geladen`;
      await ton.laden(api.audioUrl(aktuell.pfad));
      huelle = spitzen(ton.daten, 240);
      // Form und Farbe des Emblems: das Profil des Songs; was fehlt, wird aus dem Klang geschätzt.
      const klang = klangProfil(ton.daten, ton.rate);
      eigen = achsenWerte(aktuell.achsen, klang);
      werte = [...eigen];
      bpm = klang.bpm;
      herkunft.textContent = aktuell.achsen
        ? `Am Rad die Achsen verziehen. Form und Farbe kommen aus deinem Profil des Songs, das Tempo (${bpm} BPM) aus dem Klang.`
        : `Am Rad die Achsen verziehen. Für diesen Song gibt es noch kein Profil: Energie, Dunkel, Wärme, Tanzbar und Tempo (${bpm} BPM) sind aus dem Klang geschätzt, der Rest steht auf Mitte.`;
      titel.textContent = `${aktuell.titel} · ${aktuell.artist}`;
      anderer.hidden = false;
      document.getElementById("player-audio")?.pause(); // es läuft immer nur eines
      if (token === generation && el.isConnected) ton.spielen();
    } catch {
      if (token !== generation || !el.isConnected) return;
      // Diesen Song überspringen; der Knopf holt den nächsten.
      meldung.textContent = `„${aktuell?.titel || "Der Song"}“ lässt sich nicht laden. Versuch es mit einem anderen.`;
      if (aktuell) songs = songs.filter((s) => s !== aktuell);
      titel.textContent = "Spiel mit einem deiner gut bewerteten Songs.";
    } finally { laedt = false; beschriften(); }
  }

  haupt.addEventListener("click", () => {
    if (!ton.bereit) { naechster(); return; }
    if (ton.laeuft) ton.pause(); else { document.getElementById("player-audio")?.pause(); ton.spielen(); }
    beschriften();
  });
  anderer.addEventListener("click", naechster);
  document.getElementById("player-audio")?.addEventListener("play", () => { ton.pause(); beschriften(); });
  tempo.addEventListener("input", () => { ton.tempo(tempo.value / 100); tempoWert.textContent = `${tempo.value} %`; });
  tempo.addEventListener("dblclick", () => { tempo.value = 100; tempo.dispatchEvent(new Event("input")); });

  // Spielfläche: ziehen filtert und bringt Echo; loslassen stellt alles zurück.
  const ort = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    return { x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, 1 - (e.clientY - r.top) / r.height)) };
  };
  for (const leinwand of [buehne, emblem]) {
    leinwand.addEventListener("pointerdown", (e) => {
      try { leinwand.setPointerCapture(e.pointerId); } catch { /* ohne Zeigerbindung */ }
      zeiger = ort(e); ton.flaeche(zeiger.x, zeiger.y);
    });
    leinwand.addEventListener("pointermove", (e) => { if (zeiger) { zeiger = ort(e); ton.flaeche(zeiger.x, zeiger.y); } });
    for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) leinwand.addEventListener(name, () => { zeiger = null; ton.flaeche(null, null); });
  }
  uebersicht.addEventListener("click", (e) => {
    const r = uebersicht.getBoundingClientRect();
    if (ton.bereit) ton.springen(((e.clientX - r.left) / r.width) * ton.dauer);
  });

  const el = h("section", { class: "spielwiese", "aria-label": "Zeitvertreib" },
    h("div", { class: "spiel-kopf" }, h("strong", {}, "Solange Claude arbeitet"), titel, schalter),
    flaeche, uebersicht,
    h("div", { class: "spiel-leiste" }, haupt, anderer, eigenes,
      halteKnopf("Stottern", (an) => ton.stottern(an)), halteKnopf("Rückwärts", (an) => ton.rueckwaerts(an)), halteKnopf("Bremse", (an) => ton.bremsen(an)),
      h("label", { class: "spiel-tempo" }, "Tempo", tempo, tempoWert)),
    meldung);
  zeigen(ansicht);

  const ruhig = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  function passend(leinwand) { // Leinwand an ihre sichtbare Größe anpassen
    const [w, hoehe] = [Math.round(leinwand.clientWidth * devicePixelRatio), Math.round(leinwand.clientHeight * devicePixelRatio)];
    if (w && hoehe && (leinwand.width !== w || leinwand.height !== hoehe)) { leinwand.width = w; leinwand.height = hoehe; }
    return leinwand.getContext("2d");
  }
  function bild(zeit) {
    if (!el.isConnected) { laufend = false; ton.pause(); beschriften(); return; } // Ansicht verlassen: Ruhe
    const zuEnde = ton.takt();
    let kraft = [0.04, 0.03, 0.02].map((v, i) => v + 0.03 * Math.sin(zeit / (900 + i * 400))); // ruhige See ohne Ton
    if (ton.laeuft && ton.messer) {
      frequenzen ||= new Uint8Array(ton.messer.frequencyBinCount);
      welle ||= new Uint8Array(ton.messer.fftSize);
      kraft = baender(ton.messer, frequenzen);
      ton.messer.getByteTimeDomainData(welle);
    }
    bilder += 1;
    // Ohne Ton genügt jedes zweite Bild; wer wenig Bewegung wünscht, bekommt ohne Ton ein stehendes Bild.
    if (ton.laeuft || zeiger || bilder === 1 || (!ruhig && bilder % 2 === 0)) {
      if (ansicht === "emblem") {
        gl.malen({ zeit: zeit / 1000, achsen: werte, bpm, dur: false, kraft, spektrum: ton.laeuft ? frequenzen : null, zeiger });
        rad.malen(werte, eigen, emblemFarben(werte));
      } else buehneMalen(passend(buehne), buehne.width, buehne.height, zeit / 1000, zustand, kraft, ton.laeuft ? welle : null, zeiger);
    }
    uebersichtMalen(passend(uebersicht), uebersicht.width, uebersicht.height, huelle, ton.dauer ? ton.stelle / ton.dauer : 0);
    if (zuEnde) naechster(); // nach dem Stück gleich das nächste
    requestAnimationFrame(bild);
  }
  return { el, pause: () => { generation++; ton.pause(); ton.flaeche(null, null); beschriften(); }, wecken: () => { if (!laufend) { laufend = true; requestAnimationFrame(bild); } } };
}

// Das eine Spielfeld der Seite; nach dem Einhängen läuft das Bild von selbst.
export function spielwiese() {
  spiel ||= bauen();
  queueMicrotask(() => spiel.wecken());
  return spiel.el;
}

export function spielAnhalten() {
  spiel?.pause();
}
