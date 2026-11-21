// Kasten „Claude ist dran“: zeigt, ob Claude gerade arbeitet, und startet ihn auf Knopfdruck.
import { api } from "./api.js";
import { h, meldung } from "./dom.js";
import { SATZ, zeitText } from "./logic.js";

function satzZeile() {
  const feld = h("input", { type: "text", readonly: true, value: SATZ, "aria-label": "Satz für Claude Code", onfocus: (e) => e.target.select() });
  return h("div", { class: "satz-zeile" }, feld,
    h("button", { type: "button", onclick: async () => {
      try { await navigator.clipboard.writeText(SATZ); meldung("Kopiert. Jetzt in Claude Code einfügen."); } catch { feld.select(); meldung("Bitte mit Strg+C kopieren."); }
    } }, "Kopieren"));
}

// zustand: Antwort von /api/claude. danach: wird nach dem Start aufgerufen (neu laden).
export function claudeKasten(zustand, text, danach) {
  if (!zustand || !zustand.aktiv) return h("div", { class: "satz" }, h("p", {}, text || "In Claude Code einfügen:"), satzZeile());
  if (zustand.laeuft) {
    return h("div", { class: "satz", role: "status" },
      h("p", {}, `Claude arbeitet gerade (gestartet ${zeitText(zustand.gestartet_am)}). Du musst nichts tun.`));
  }
  const fehler = zustand.letzter?.fehler;
  const starten = async (ereignis) => {
    ereignis.target.disabled = true;
    try { await api.claudeStarten(); meldung("Claude ist gestartet."); } catch (f) { meldung(f.meldung, "fehler"); }
    danach?.();
  };
  return h("div", { class: "satz" },
    h("p", {}, fehler ? `Der letzte Start hat nicht geklappt: ${fehler}` : (text || "Claude arbeitet gerade nicht.")),
    h("div", { class: "satz-zeile" }, h("button", { type: "button", onclick: starten }, "Claude jetzt starten")),
    h("details", { class: "klein" }, h("summary", {}, "Lieber selbst in Claude Code eingeben"), satzZeile()));
}
