// Mastering-Studio: Regler wie am Pult, Vorhören im Browser (Web Audio), fertiger Master per Render im Dienst.
import { api } from "./api.js";
import { h, leeren } from "./dom.js";
import { takeName } from "./logic.js";

const EQ = [["eq_sub", "Sub 40", "lowshelf", 40], ["eq_bass", "Bass 120", "peaking", 120], ["eq_tiefmitten", "Tiefmitten 350", "peaking", 350],
  ["eq_praesenz", "Präsenz 3,5k", "peaking", 3500], ["eq_luft", "Luft", "highshelf", 5000]];
const KOMP = [["komp_schwelle", "Schwelle", "dB", 1], ["komp_tief", "Tiefen", ":1", 0.1], ["komp_mitte", "Mitten", ":1", 0.1],
  ["komp_hoch", "Höhen", ":1", 0.1], ["saettigung", "Sättigung", "dB", 0.5]];
const MASTER = [["breite", "Stereo-Breite", "%", 5], ["lautheit", "Lautheit", "LUFS", 0.5], ["decke", "Pegeldecke", "dBTP", 0.1]];
const zahl = (wert) => String(wert).replace(".", ",").replace("-", "−");

// Analyse des Favoriten: Messwerte, Abstand je Band zum Zielbild und Empfehlungen in Sätzen.
function analyseTafel(a) {
  const m = a.messwerte;
  const wert = (name, text) => h("div", { class: "messwert" }, h("span", {}, name), h("strong", {}, text));
  return h("div", { class: "modul analyse" }, h("h4", {}, `Analyse · Vergleich mit ${a.vergleich}`),
    h("div", { class: "messwerte" },
      wert("Lautheit", `${zahl(m.lufs)} LUFS`), wert("Spitze", `${zahl(m.spitze)} dBTP`), wert("Dynamik", `${zahl(m.spanne)} LU`),
      wert("Spitze zu Mittel", `${zahl(m.crest)} dB`), wert("Stereo-Korrelation", zahl(m.korrelation)), wert("Seite zu Mitte", zahl(m.breite))),
    h("div", { class: "baender", role: "img", "aria-label": "Abstand je Frequenzband zu den eMastered-Fassungen" }, a.baender.map((b) => {
      const balken = h("span", { class: `balken ${b.abstand < 0 ? "unter" : "ueber"}` });
      balken.style.width = `${Math.min(50, Math.abs(b.abstand) * 8)}%`;
      return h("div", { class: "band" }, h("span", {}, b.titel), h("span", { class: "spur-band" }, balken), h("span", {}, `${b.abstand > 0 ? "+" : ""}${zahl(b.abstand)} dB`));
    })),
    h("ul", { class: "empfehlungen" }, a.empfehlungen.map((satz) => h("li", {}, satz))));
}
const db = (wert) => 10 ** (wert / 20);

// Tonkette: Quelle → EQ → Kompressor → Aufholen → Breite → Ausgang; daneben der unbearbeitete Weg zum Vergleich.
function tonkette(audio) {
  const ctx = new AudioContext();
  const quelle = ctx.createMediaElementSource(audio);
  const eq = EQ.map(([, , typ, frequenz]) => {
    const f = ctx.createBiquadFilter();
    f.type = typ; f.frequency.value = frequenz; f.Q.value = typ === "peaking" ? 1 : 0.7;
    return f;
  });
  const komp = ctx.createDynamicsCompressor();
  const [kompEin, kompAus, aufholen, nass, trocken, ausgang, pegel] = [1, 2, 3, 4, 5, 6, 7].map(() => ctx.createGain());
  const decke = ctx.createDynamicsCompressor(); // Begrenzer der Ausgangsstufe
  const teiler = ctx.createChannelSplitter(2);
  const mischer = ctx.createChannelMerger(2);
  const kreuz = [0, 1, 2, 3].map(() => ctx.createGain()); // LL, RL, LR, RR
  const messer = ctx.createAnalyser();
  messer.fftSize = 2048;
  quelle.connect(eq[0]);
  eq.forEach((f, i) => { if (eq[i + 1]) f.connect(eq[i + 1]); });
  const nachEq = eq[eq.length - 1];
  nachEq.connect(komp); komp.connect(kompEin); kompEin.connect(aufholen);
  nachEq.connect(kompAus); kompAus.connect(aufholen);
  aufholen.connect(teiler);
  teiler.connect(kreuz[0], 0); teiler.connect(kreuz[1], 1); teiler.connect(kreuz[2], 0); teiler.connect(kreuz[3], 1);
  kreuz[0].connect(mischer, 0, 0); kreuz[1].connect(mischer, 0, 0); kreuz[2].connect(mischer, 0, 1); kreuz[3].connect(mischer, 0, 1);
  mischer.connect(pegel); pegel.connect(decke); decke.connect(nass); quelle.connect(trocken);
  nass.connect(ausgang); trocken.connect(ausgang);
  ausgang.connect(messer); messer.connect(ctx.destination);
  return { ctx, eq, komp, kompEin, kompAus, aufholen, kreuz, pegel, decke, nass, trocken, messer };
}

// Der Browser-Kompressor hebt von selbst an; diese Anhebung wird herausgerechnet, damit man die Kompression hört und nicht „lauter“.
const aufholung = (schwelle, ratio) => -0.6 * (schwelle - schwelle / ratio);

// lufs: gemessene Lautheit des Songs (aus der Analyse), damit „Lautheit“ beim Vorhören wirkt.
function anwenden(k, w, vergleich, lufs) {
  EQ.forEach(([name], i) => { k.eq[i].gain.value = w[name]; });
  // Vorhören mit einem Kompressor (Mittelwert der drei Bänder); das Rendern komprimiert die Bänder getrennt.
  const ratio = (w.komp_tief + w.komp_mitte + w.komp_hoch) / 3;
  k.komp.threshold.value = w.komp_schwelle; k.komp.ratio.value = ratio; k.komp.knee.value = 6;
  k.komp.attack.value = 0.02; k.komp.release.value = 0.25;
  // Bei abgeschaltetem Kompressor läuft der Ton an ihm vorbei.
  k.kompEin.gain.value = w.komp_an ? 1 : 0;
  k.kompAus.gain.value = w.komp_an ? 0 : 1;
  k.aufholen.gain.value = w.komp_an ? db(-aufholung(w.komp_schwelle, ratio)) : 1;
  // Ausgangsstufe: auf die Ziel-Lautheit anheben, dann Begrenzer an der Pegeldecke.
  const grenze = w.decke - 0.5;
  k.pegel.gain.value = db(lufs == null ? 0 : Math.max(-12, Math.min(12, w.lautheit - lufs)));
  k.decke.threshold.value = grenze; k.decke.ratio.value = 20; k.decke.knee.value = 0;
  k.decke.attack.value = 0.002; k.decke.release.value = 0.08;
  k.nachDecke = db(-aufholung(grenze, 20));
  const breite = w.breite / 100;
  const [gleich, kreuz] = [(1 + breite) / 2, (1 - breite) / 2];
  k.kreuz[0].gain.value = gleich; k.kreuz[1].gain.value = kreuz; k.kreuz[2].gain.value = kreuz; k.kreuz[3].gain.value = gleich;
  k.nass.gain.value = vergleich ? 0 : k.nachDecke;
  k.trocken.gain.value = vergleich ? 1 : 0;
}

// Drehregler: sichtbarer Knopf zum Ziehen, darunter ein echter Schieber für Tastatur und Vorleseprogramme.
function drehregler(name, titel, einheit, schritt, grenzen, werte, geaendert) {
  const [unten, oben, standard] = grenzen[name];
  const zeiger = h("span", { class: "zeiger" });
  const knopf = h("div", { class: "drehknopf", title: "Ziehen zum Drehen, Doppelklick setzt zurück" }, zeiger);
  const zahl = h("output", {});
  const eingabe = h("input", { type: "range", min: unten, max: oben, step: schritt, value: werte[name], "aria-label": `${titel} in ${einheit}` });
  const zeigen = () => {
    const anteil = (werte[name] - unten) / (oben - unten);
    zeiger.style.transform = `rotate(${-135 + anteil * 270}deg)`;
    zahl.textContent = `${Number(werte[name].toFixed(1))} ${einheit}`;
    eingabe.value = werte[name];
  };
  const setzen = (wert) => {
    werte[name] = Math.min(oben, Math.max(unten, Math.round(wert / schritt) * schritt));
    zeigen(); geaendert();
  };
  eingabe.addEventListener("input", () => setzen(Number(eingabe.value)));
  knopf.addEventListener("dblclick", () => setzen(standard));
  knopf.addEventListener("pointerdown", (start) => {
    try { knopf.setPointerCapture(start.pointerId); } catch { /* ohne Zeigerbindung weiter */ }
    const [y0, wert0] = [start.clientY, werte[name]];
    const ziehen = (e) => setzen(wert0 + ((y0 - e.clientY) / 150) * (oben - unten));
    knopf.addEventListener("pointermove", ziehen);
    knopf.addEventListener("pointerup", () => knopf.removeEventListener("pointermove", ziehen), { once: true });
  });
  zeigen();
  return { el: h("label", { class: "regler" }, h("span", { class: "regler-name" }, titel), knopf, zahl, eingabe), zeigen };
}

function schieber(name, titel, grenzen, werte, geaendert) {
  const [unten, oben, standard] = grenzen[name];
  const zahl = h("output", {});
  const eingabe = h("input", { type: "range", class: "fader", min: unten, max: oben, step: 0.5, value: werte[name], "aria-label": `${titel} Hz in dB`,
    title: "Doppelklick setzt zurück" });
  const zeigen = () => { eingabe.value = werte[name]; zahl.textContent = `${werte[name] > 0 ? "+" : ""}${werte[name]} dB`; };
  eingabe.addEventListener("input", () => { werte[name] = Number(eingabe.value); zeigen(); geaendert(); });
  eingabe.addEventListener("dblclick", () => { werte[name] = standard; zeigen(); geaendert(); });
  zeigen();
  return { el: h("label", { class: "kanal" }, zahl, eingabe, h("span", { class: "regler-name" }, titel)), zeigen };
}

function pegel(leinwand, kette, audio, reduktion) {
  const daten = new Float32Array(kette.messer.fftSize);
  const stift = leinwand.getContext("2d");
  let spitze = 0;
  const malen = () => {
    if (!leinwand.isConnected) return;
    kette.messer.getFloatTimeDomainData(daten);
    let summe = 0;
    for (const x of daten) summe += x * x;
    const wert = audio.paused ? 0 : Math.min(1, Math.max(0, (20 * Math.log10(Math.sqrt(summe / daten.length) + 1e-9) + 48) / 48));
    spitze = Math.max(wert, spitze - 0.006);
    stift.clearRect(0, 0, leinwand.width, leinwand.height);
    stift.fillStyle = wert > 0.9 ? "#e0533d" : wert > 0.75 ? "#e6b94a" : "#58c27d";
    stift.fillRect(0, 0, leinwand.width * wert, leinwand.height);
    stift.fillStyle = "#f4efe6";
    stift.fillRect(leinwand.width * spitze - 2, 0, 2, leinwand.height);
    reduktion.textContent = audio.paused ? "" : `Kompressor ${kette.komp.reduction.toFixed(1)} dB · Begrenzer ${kette.decke.reduction.toFixed(1)} dB`;
    requestAnimationFrame(malen);
  };
  requestAnimationFrame(malen);
}

let pult = null; // bleibt über das Neuzeichnen der Seite erhalten, damit Regler und Wiedergabe nicht abreißen

// order: Auftrag im Nachlauf; rendern(einstellungen) schickt die Werte an den Dienst.
export function studioPult(order, rendern) {
  const favorit = order.nachlauf.favorit;
  const schluessel = `${order.id}|${favorit}`;
  if (pult?.schluessel === schluessel) { pult.analyseZeigen(order.nachlauf.mastering.analyse || null); return pult.el; }
  const info = order.nachlauf_info;
  const werte = { ...info.standard };
  const audio = h("audio", { controls: true, preload: "none", src: api.audioUrl(favorit) });
  const leinwand = h("canvas", { class: "pegel", width: 600, height: 14, "aria-hidden": "true" });
  const reduktion = h("output", { class: "reduktion", title: "So stark regeln Kompressor und Begrenzer gerade herunter" });
  let kette = null;
  let vergleich = false;
  let beruehrt = false; // hat der Nutzer schon selbst gedreht? Dann überschreibt die Empfehlung nichts mehr.
  let lufs = null;
  const geaendert = (vonHand = true) => { if (vonHand) beruehrt = true; if (kette) anwenden(kette, werte, vergleich, lufs); };
  audio.addEventListener("play", () => {
    document.getElementById("player-audio")?.pause();
    if (!kette) { kette = tonkette(audio); pegel(leinwand, kette, audio, reduktion); }
    kette.ctx.resume();
    geaendert(false);
  });
  const teile = [
    ...EQ.map(([name, titel]) => schieber(name, titel, info.grenzen, werte, geaendert)),
    ...KOMP.map(([name, titel, einheit, schritt]) => drehregler(name, titel, einheit, schritt, info.grenzen, werte, geaendert)),
    ...MASTER.map(([name, titel, einheit, schritt]) => drehregler(name, titel, einheit, schritt, info.grenzen, werte, geaendert)),
  ];
  const kompAn = h("button", { type: "button", class: "schalter-led", "aria-pressed": "false", onclick: () => {
    werte.komp_an = !werte.komp_an; kompAn.setAttribute("aria-pressed", String(werte.komp_an)); geaendert();
  } }, "Kompressor in drei Bändern");
  const ab = h("button", { type: "button", class: "schalter-led", "aria-pressed": "false", title: "Original ohne Bearbeitung hören", onclick: () => {
    vergleich = !vergleich; ab.setAttribute("aria-pressed", String(vergleich)); geaendert();
  } }, "Original");
  const laden = (neu) => {
    Object.assign(werte, info.standard, neu);
    kompAn.setAttribute("aria-pressed", String(werte.komp_an));
    teile.forEach((t) => t.zeigen());
    geaendert(false);
  };
  const presets = h("div", { class: "presets", role: "group", "aria-label": "Voreinstellungen" });
  const tafel = h("div", {});
  let gezeigt = null;
  const analyseZeigen = (a) => {
    if (a === gezeigt) return;
    const erste = !gezeigt && a;
    gezeigt = a;
    lufs = a ? a.messwerte.lufs : null;
    leeren(presets).append(h("button", { type: "button", onclick: () => laden({}) }, "Neutral"),
      ...(a ? a.presets.map((p) => h("button", { type: "button", class: p.name === "vorlage" ? "empfohlen" : "", title: p.beschreibung,
        onclick: () => laden(p.einstellungen) }, p.titel)) : []));
    leeren(tafel).append(a ? analyseTafel(a) : h("p", { class: "studio-hinweis" }, info.werkzeuge.analyse
      ? "Der Song wird vermessen. Messwerte, Empfehlungen und passende Voreinstellungen erscheinen gleich."
      : "Die Analyse ist auf diesem Rechner nicht eingerichtet; die Regler starten neutral."));
    if (erste && !beruehrt) laden(a.presets[0].einstellungen); // Empfehlung als Startpunkt
  };
  const knopf = h("button", { type: "button", class: "knopf", disabled: !info.werkzeuge.ffmpeg, onclick: async () => {
    knopf.disabled = true; knopf.textContent = "Rendert …";
    await rendern({ ...werte });
    knopf.disabled = false; knopf.textContent = "Master rendern";
  } }, "Master rendern");
  const el = h("section", { class: "studio", "aria-label": "Mastering-Studio" },
    h("div", { class: "studio-kopf" }, h("strong", {}, "Studio"), h("span", {}, takeName(favorit)), presets),
    tafel,
    h("div", { class: "studio-zeile" }, audio, ab),
    leinwand, reduktion,
    h("div", { class: "module" },
      h("div", { class: "modul" }, h("h4", {}, "Equalizer"), h("div", { class: "kanaele" }, teile.slice(0, 5).map((t) => t.el))),
      h("div", { class: "modul" }, h("h4", {}, kompAn), h("div", { class: "reglerzeile" }, teile.slice(5, 10).map((t) => t.el))),
      h("div", { class: "modul" }, h("h4", {}, "Ausgang"), h("div", { class: "reglerzeile" }, teile.slice(10).map((t) => t.el)))),
    h("p", { class: "studio-hinweis" }, !info.werkzeuge.ffmpeg ? "ffmpeg fehlt auf diesem Rechner; Rendern ist nicht möglich."
      : info.werkzeuge.engine
        ? "Gerendert wird mit der Mastering-Engine des Projekts: Equalizer, Kompression in drei Bändern, Sättigung, Limiter mit Oversampling, 24 Bit. Vorhören ist eine Näherung (ein Kompressor statt drei, ohne Sättigung); Lautheit und Pegeldecke wirken beim Vorhören, sobald der Song vermessen ist. Unter der Pegelanzeige steht, wie stark Kompressor und Begrenzer gerade arbeiten. Das Original bleibt unverändert."
        : "Die Mastering-Engine ist nicht eingerichtet; gerendert wird vereinfacht mit ffmpeg (ein Kompressor, keine Sättigung)."),
    h("div", { class: "knopfzeile" }, knopf));
  pult = { schluessel, el, analyseZeigen };
  analyseZeigen(order.nachlauf.mastering.analyse || null);
  return el;
}
