// Kleine DOM-Helfer, ohne Framework.

export function h(tag, attrs, ...kinder) {
  const el = document.createElement(tag);
  for (const [name, wert] of Object.entries(attrs || {})) {
    if (wert == null || wert === false) continue;
    if (name.startsWith("on")) el.addEventListener(name.slice(2), wert);
    else if (name === "class") el.className = wert;
    else if (name === "value") el.value = wert;
    else if (name === "checked" || name === "disabled" || name === "hidden" || name === "open") el[name] = Boolean(wert);
    else el.setAttribute(name, wert === true ? "" : wert);
  }
  for (const kind of kinder.flat(Infinity)) {
    if (kind == null || kind === false) continue;
    el.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
  return el;
}

export function leeren(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

let zaehler = 0;
export function neueId(vorsilbe = "f") {
  zaehler += 1;
  return `${vorsilbe}${zaehler}`;
}

// Beschriftetes Feld mit Platz für Hinweis und Fehlermeldung. `feld` ist der Name für Fehlermeldungen des Dienstes.
export function feld(beschriftung, eingabe, { hinweis, name } = {}) {
  const id = eingabe.id || neueId();
  eingabe.id = id;
  const fehler = h("p", { class: "fehler", role: "alert", hidden: true, "data-fehler": name || "" });
  return h("div", { class: "feld" }, h("label", { for: id }, beschriftung), eingabe,
    hinweis ? h("p", { class: "hinweis" }, hinweis) : null, fehler);
}

export function fehlerZeigen(wurzel, name, meldung) {
  let gezeigt = false;
  for (const el of wurzel.querySelectorAll("[data-fehler]")) {
    const passt = meldung && el.dataset.fehler === name;
    el.hidden = !passt;
    el.textContent = passt ? meldung : "";
    if (passt && !gezeigt) {
      gezeigt = true;
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }
  return gezeigt;
}

let meldungTimer = null;
export function meldung(text, art = "info") {
  const el = document.getElementById("meldung");
  el.textContent = text;
  el.className = `meldung ${art}`;
  el.hidden = !text;
  clearTimeout(meldungTimer);
  if (text) meldungTimer = setTimeout(() => { el.hidden = true; }, art === "fehler" ? 9000 : 3500);
}

// Auswahl aus wenigen Werten als Knopfreihe (per Tastatur bedienbar, aria-pressed).
export function knopfReihe(beschriftung, wahl, aktuell, beiWahl, klasse = "") {
  const gruppe = h("div", { class: `reihe ${klasse}`, role: "group", "aria-label": beschriftung });
  const setzen = (wert) => {
    for (const k of gruppe.children) k.setAttribute("aria-pressed", String(k.dataset.wert === String(wert)));
  };
  for (const [wert, text, titel] of wahl) {
    gruppe.append(h("button", { type: "button", "data-wert": wert, title: titel, onclick: () => { setzen(wert); beiWahl(wert); } }, text));
  }
  setzen(aktuell);
  gruppe.setzen = setzen;
  return gruppe;
}

// Eingaben mit data-key über ein Neuzeichnen hinweg erhalten (Wert und Fokus).
export function eingabenMerken(wurzel) {
  const werte = new Map();
  for (const el of wurzel.querySelectorAll("[data-key]")) werte.set(el.dataset.key, el.value);
  const aktiv = document.activeElement && wurzel.contains(document.activeElement) ? document.activeElement : null;
  return { werte, fokus: aktiv?.dataset.key, start: aktiv?.selectionStart, ende: aktiv?.selectionEnd };
}

export function eingabenWiederherstellen(wurzel, merk) {
  for (const el of wurzel.querySelectorAll("[data-key]")) {
    if (merk.werte.has(el.dataset.key) && merk.werte.get(el.dataset.key) !== "") el.value = merk.werte.get(el.dataset.key);
    if (merk.fokus && el.dataset.key === merk.fokus) {
      el.focus({ preventScroll: true });
      try { el.setSelectionRange(merk.start, merk.ende); } catch { /* kein Textfeld */ }
    }
  }
}
