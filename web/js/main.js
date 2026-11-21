// Einstieg: Ansichten nach Adresse (#/, #/neu, #/neu/<id>, #/mastern, #/auftrag/<id>).
import { leeren } from "./dom.js";
import { playerEinrichten } from "./player.js";
import { startAnsicht } from "./start.js";
import { neuAnsicht } from "./neu.js";
import { auftragAnsicht } from "./auftrag.js";
import { masternAnsicht } from "./mastern.js";

const ansicht = document.getElementById("ansicht");
let aufraeumen = null;

async function zeigen() {
  if (aufraeumen) await aufraeumen();
  aufraeumen = null;
  const teile = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [bereich, id] = teile;
  for (const link of document.querySelectorAll("[data-nav]")) {
    const aktiv = link.dataset.nav === (bereich === "neu" || bereich === "mastern" ? bereich : "start");
    if (aktiv) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  }
  leeren(ansicht);
  window.scrollTo(0, 0);
  if (bereich === "neu") aufraeumen = neuAnsicht(ansicht, id);
  else if (bereich === "mastern") aufraeumen = masternAnsicht(ansicht);
  else if (bereich === "auftrag" && id) aufraeumen = auftragAnsicht(ansicht, id);
  else aufraeumen = startAnsicht(ansicht);
}

playerEinrichten();
window.addEventListener("hashchange", zeigen);
zeigen();
