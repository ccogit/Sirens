// Einstieg: Ansichten nach Adresse (#/, #/neu, #/neu/<id>, #/mastern, #/auftrag/<id>).
import { leeren } from "./dom.js";
import { playerEinrichten } from "./player.js";
import { startAnsicht } from "./start.js";
import { neuAnsicht } from "./neu.js";
import { auftragAnsicht } from "./auftrag.js";
import { masternAnsicht } from "./mastern.js";
import { songsAnsicht } from "./songs.js";
import { liveLabAnsicht } from "./live_lab.js";

const ansicht = document.getElementById("ansicht");
let aufraeumen = null;

async function zeigen() {
  if (aufraeumen) await aufraeumen();
  aufraeumen = null;
  const teile = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [bereich, id, unterseite] = teile;
  for (const link of document.querySelectorAll("[data-nav]")) {
    const aktiv = link.dataset.nav === (bereich === "neu" || bereich === "mastern" || bereich === "songs" || bereich === "lab" ? bereich : "start");
    if (aktiv) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  }
  leeren(ansicht);
  window.scrollTo(0, 0);
  if (bereich === "neu") aufraeumen = neuAnsicht(ansicht, id);
  else if (bereich === "mastern") aufraeumen = masternAnsicht(ansicht);
  else if (bereich === "songs") aufraeumen = songsAnsicht(ansicht);
  else if (bereich === "lab") aufraeumen = liveLabAnsicht(ansicht);
  else if (bereich === "auftrag" && id) aufraeumen = auftragAnsicht(ansicht, id, unterseite);
  else aufraeumen = startAnsicht(ansicht);
}

const themeSwitch = document.getElementById("theme-switch");
const theme = (() => { try { return localStorage.getItem("sirens.theme"); } catch { return null; } })();
// Signal Room ist der Standard; eine ausdrücklich gespeicherte helle Wahl bleibt erhalten.
document.documentElement.dataset.theme = theme === "light" ? "light" : "dark";
function updateTheme() {
  const dark = document.documentElement.dataset.theme === "dark";
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0c0d10" : "#f4f3ed");
  themeSwitch.textContent = dark ? "☀" : "☾";
  themeSwitch.setAttribute("aria-pressed", String(dark));
  themeSwitch.setAttribute("aria-label", dark ? "Helles Erscheinungsbild einschalten" : "Dunkles Erscheinungsbild einschalten");
}
themeSwitch.addEventListener("click", () => {
  document.documentElement.dataset.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  try { localStorage.setItem("sirens.theme", document.documentElement.dataset.theme); } catch { /* privater Modus */ }
  updateTheme();
});
updateTheme();
playerEinrichten();
window.addEventListener("hashchange", zeigen);
zeigen();
