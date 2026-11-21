// Achsenrad der Spielwiese: zwölf Achsen als Strahlen; an jedem lässt sich die Stärke mit der Maus verziehen.
import { h } from "./dom.js";
import { ACHSEN } from "./logic.js";

const RAND = 0.7; // Anteil des halben Feldes, den der volle Ausschlag einnimmt (außen bleibt Platz für die Namen)
// Länge eines Strahls: so, dass links und rechts noch die Namen der Achsen hinpassen (`platz` in derselben Einheit wie w und h).
const strahl = (w, h, platz) => Math.max(20, Math.min((Math.min(w, h) / 2) * RAND, w / 2 - platz));

// `beiAenderung(nr, wert)` meldet jedes Verziehen. Liefert { el, malen(werte, eigen, farben) }.
export function achsenRad(beiAenderung) {
  const leinwand = h("canvas", { class: "spiel-rad", role: "img", "aria-label": "Achsen des Songs; an einem Strahl ziehen verändert die Stärke" });
  let gegriffen = -1;
  const winkel = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / ACHSEN.length;

  function ziehen(e) {
    const r = leinwand.getBoundingClientRect();
    const [x, y] = [e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2];
    const voll = strahl(r.width, r.height, 84);
    if (gegriffen < 0) { // den Strahl nehmen, der der Maus am nächsten liegt
      const w = Math.atan2(y, x);
      gegriffen = ACHSEN.map((_, i) => Math.abs(Math.atan2(Math.sin(w - winkel(i)), Math.cos(w - winkel(i))))).reduce((b, v, i, a) => (v < a[b] ? i : b), 0);
    }
    const entlang = (x * Math.cos(winkel(gegriffen)) + y * Math.sin(winkel(gegriffen))) / voll; // Anteil entlang des Strahls
    beiAenderung(gegriffen, Math.round(Math.min(1, Math.max(0, entlang)) * 100) / 10);
  }
  leinwand.addEventListener("pointerdown", (e) => { try { leinwand.setPointerCapture(e.pointerId); } catch { /* ohne Zeigerbindung */ } gegriffen = -1; ziehen(e); });
  leinwand.addEventListener("pointermove", (e) => { if (gegriffen >= 0) ziehen(e); });
  for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) leinwand.addEventListener(name, () => { gegriffen = -1; });

  // werte: aktueller Stand (12 × 0–10); eigen: das Profil des Songs als feine Linie; farben: { haupt, akzent } je [r, g, b] 0…1
  function malen(werte, eigen, farben) {
    const [w, hoehe] = [Math.round(leinwand.clientWidth * devicePixelRatio), Math.round(leinwand.clientHeight * devicePixelRatio)];
    if (!w || !hoehe) return;
    if (leinwand.width !== w || leinwand.height !== hoehe) { leinwand.width = w; leinwand.height = hoehe; }
    const stift = leinwand.getContext("2d");
    const [mx, my, voll] = [w / 2, hoehe / 2, strahl(w, hoehe, 84 * devicePixelRatio)];
    const rgb = (f, a = 1) => `rgba(${f.map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255)).join(",")},${a})`;
    const punkt = (i, wert) => [mx + Math.cos(winkel(i)) * voll * (wert / 10), my + Math.sin(winkel(i)) * voll * (wert / 10)];
    const zug = (liste) => { stift.beginPath(); liste.forEach((wert, i) => { const [x, y] = punkt(i, wert); if (i) stift.lineTo(x, y); else stift.moveTo(x, y); }); stift.closePath(); };
    stift.clearRect(0, 0, w, hoehe);
    stift.lineWidth = devicePixelRatio;
    stift.strokeStyle = "rgba(180, 190, 230, 0.16)";
    for (const stufe of [2.5, 5, 7.5, 10]) { zug(ACHSEN.map(() => stufe)); stift.stroke(); }
    stift.font = `${Math.round(10.5 * devicePixelRatio)}px "Segoe UI", system-ui, sans-serif`;
    stift.textBaseline = "middle";
    ACHSEN.forEach(([, name], i) => {
      const [x, y] = punkt(i, 10);
      stift.beginPath(); stift.moveTo(mx, my); stift.lineTo(x, y); stift.stroke();
      const [tx, ty] = punkt(i, 11.6);
      stift.fillStyle = i === gegriffen ? "#fff" : "rgba(210, 218, 245, 0.8)";
      stift.textAlign = Math.abs(tx - mx) < voll * 0.2 ? "center" : tx > mx ? "left" : "right";
      stift.fillText(i === gegriffen ? `${name} ${werte[i]}` : name, tx, ty);
    });
    if (eigen) { zug(eigen); stift.setLineDash([4 * devicePixelRatio, 4 * devicePixelRatio]); stift.strokeStyle = "rgba(230, 235, 255, 0.45)"; stift.stroke(); stift.setLineDash([]); }
    zug(werte);
    stift.fillStyle = rgb(farben.haupt, 0.3); stift.fill();
    stift.lineWidth = 2 * devicePixelRatio; stift.strokeStyle = rgb(farben.haupt); stift.stroke();
    werte.forEach((wert, i) => {
      const [x, y] = punkt(i, wert);
      stift.beginPath(); stift.arc(x, y, (i === gegriffen ? 6 : 4) * devicePixelRatio, 0, Math.PI * 2);
      stift.fillStyle = i === gegriffen ? "#fff" : rgb(farben.akzent); stift.fill();
    });
  }
  return { el: leinwand, malen };
}
