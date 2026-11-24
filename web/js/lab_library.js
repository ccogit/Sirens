// Gemeinsame Tool-Bibliothek für das Live Lab; keine Audio- oder GPU-Arbeit in der Vorschau.
import { h } from "./dom.js";

export function labWerkzeugWahl(werkzeuge, gespeichert) {
  return werkzeuge.some((tool) => tool.id === gespeichert) ? gespeichert : werkzeuge[0].id;
}

// Nur ein Panel darf aktiv sein. Erneutes Öffnen lässt laufendes Audio in Ruhe.
export function labWerkzeugAktivieren(werkzeuge, id, bisher) {
  if (id === bisher) return;
  for (const tool of werkzeuge) {
    tool.panel.hidden = tool.id !== id;
    if (tool.id !== id) tool.anhalten?.();
  }
  werkzeuge.find((tool) => tool.id === id)?.aktivieren?.();
}

export function labWerkzeugNavigation(werkzeuge, waehlen) {
  const titel = h("h2", { tabindex: "-1" });
  const beschreibung = h("p", { class: "lab-workspace-description" });
  const karten = new Map();
  const summaryText = h("span", { class: "lab-library-current" });
  const grid = h("div", { class: "lab-tool-grid", role: "group", "aria-label": "Musikwerkzeuge" });
  const bibliothek = h("details", { class: "lab-library", open: true },
    h("summary", {},
      h("span", { class: "lab-library-heading" }, "Tool-Bibliothek",
        h("small", {}, werkzeuge.length + " Werkzeuge · entdecke neue Klangwelten")),
      summaryText),
    grid);

  for (const tool of werkzeuge) {
    const label = h("span", { class: "lab-tool-action" }, "Öffnen →");
    const karte = h("button", {
      type: "button", class: "lab-tool-card", "data-tone": tool.farbe, "data-toy": tool.id,
      "aria-pressed": "false", "aria-controls": "lab-panel-" + tool.id,
      onclick: () => {
        waehlen(tool.id);
        bibliothek.open = false;
        titel.focus();
      }
    },
      h("span", { class: "lab-tool-art", "aria-hidden": "true" },
        h("span", { class: "lab-tool-symbol" }, tool.symbol),
        h("span", { class: "lab-tool-wave" }, tool.motiv.map((wert) =>
          h("i", { style: "--bar:" + wert + "%" })))),
      h("span", { class: "lab-tool-body" },
        h("span", { class: "lab-tool-category" }, tool.kategorie),
        h("strong", { class: "lab-tool-title" }, tool.titel),
        h("span", { class: "lab-tool-description" }, tool.beschreibung),
        h("span", { class: "lab-tool-meta" }, tool.hinweis),
        label));
    karten.set(tool.id, { karte, label });
    grid.append(karte);
  }

  let aktuell;
  const arbeitskopf = h("header", { class: "lab-workspace-head" },
    h("div", {}, h("span", { class: "lab-workspace-kicker" }, "AKTIVES WERKZEUG"), titel, beschreibung),
    h("button", { type: "button", class: "lab-mode", onclick: () => {
      bibliothek.open = true;
      karten.get(aktuell)?.karte.focus();
    } }, "↑ Werkzeuge anzeigen"));

  function anzeigen(id) {
    aktuell = id;
    const tool = werkzeuge.find((eintrag) => eintrag.id === id);
    titel.textContent = tool.titel;
    beschreibung.textContent = tool.beschreibung;
    summaryText.textContent = "Ausgewählt: " + tool.titel;
    for (const [key, { karte, label }] of karten) {
      karte.setAttribute("aria-pressed", String(key === id));
      label.textContent = key === id ? "✓ Ausgewählt · Öffnen →" : "Öffnen →";
    }
  }

  return { bibliothek, arbeitskopf, anzeigen };
}
