// Instrument-Labor: aus einem isolierten Stem mit Basic Pitch Noten extrahieren
// und stattdessen live einen gewählten Web-Audio-Synthesizer spielen.
import { api } from "./api.js";
import { h } from "./dom.js";
import { StemSynth, SYNTH_KLAENGE } from "./stem_synth.js";

const STEM_NAMEN={vocals:"Gesang",bass:"Bass",guitar:"Gitarre",piano:"Klavier",other:"Weitere Instrumente"};
const VERFUEGBAR=["vocals","bass","guitar","piano","other"];

export function instrumentLabor(player, pfad, modell, stems, onMix) {
  const synth=new StemSynth(player);
  let beendet=false, marke=0, timer=null;
  const spuren=stems.filter(name=>VERFUEGBAR.includes(name));
  const quelle=h("select", {"aria-label":"Zu ersetzendes Instrument"},
    ...spuren.map(name=>h("option",{value:name},STEM_NAMEN[name])));
  const sound=h("select", {"aria-label":"Neuer Instrumentenklang"},
    ...Object.entries(SYNTH_KLAENGE).map(([id,name])=>h("option",{value:id},name)));
  const erkennen=h("button", {type:"button",class:"stems-primary"}, "KI-Noten erkennen");
  const umschalten=h("button", {type:"button",class:"stems-action",disabled:true,
    "aria-pressed":"false"}, "Instrument ersetzen: AUS");
  const anzeige=h("p",{class:"stems-status",role:"status","aria-live":"polite"},
    "Zunächst eine Instrumentenspur wählen und die Noten erkennen.");
  const info=h("p",{class:"stems-hint"},
    "Basic Pitch erkennt Tonhöhen und Noten in einem Stem; die synthetischen Ersatzklänge sind Näherungen, keine exakten Instrumentenmodelle. Melodische Einzelstimmen liefern meist die besten Ergebnisse.");

  function wechseln(an) {
    synth.aktiv=Boolean(an && synth.events.length);
    umschalten.textContent="Instrument ersetzen: "+(synth.aktiv?"AN":"AUS");
    umschalten.setAttribute("aria-pressed",String(synth.aktiv));
    if(synth.aktiv && player.laeuft)synth.start();else synth.stop();
    onMix();
  }
  function neu() {
    marke++;
    clearTimeout(timer);
    timer=null;
    wechseln(false);
    synth.setNoten([]);
    erkennen.disabled=false;
    erkennen.hidden=false;
    umschalten.disabled=true;
    umschalten.textContent="Instrument ersetzen: AUS";
    anzeige.textContent="Prüfe bereits erkannte Noten …";
    if(quelle.value)pruefen(marke);
  }
  function darstellen(daten,nr) {
    if(beendet||nr!==marke)return;
    anzeige.textContent=daten.meldung||"Notenstatus unbekannt.";
    if(daten.zustand==="bereit") {
      synth.setNoten(daten.noten||[]);
      erkennen.hidden=true;
      umschalten.disabled=!synth.events.length;
      if(!synth.events.length)anzeige.textContent="Keine verwertbaren Noten gefunden. Andere Spur probieren.";
    } else if(daten.zustand==="laeuft") {
      erkennen.disabled=true;
      erkennen.textContent="Noten werden erkannt …";
      timer=setTimeout(()=>pruefen(nr),2000);
    } else {
      erkennen.disabled=false;
      erkennen.hidden=false;
      erkennen.textContent=daten.zustand==="fehler"?"Notenerkennung erneut versuchen":"KI-Noten erkennen";
    }
  }
  async function pruefen(nr) {
    if(beendet||!quelle.value)return;
    try {
      const daten=await api.stemNoten(pfad,modell,quelle.value);
      darstellen(daten,nr);
    } catch(err) {
      if(!beendet&&nr===marke) {
        anzeige.textContent=err.meldung||"Notenerkennung nicht verfügbar.";
        erkennen.disabled=false;
      }
    }
  }
  quelle.addEventListener("change",neu);
  sound.addEventListener("change",()=>synth.setInstrument(sound.value));
  erkennen.addEventListener("click",async()=>{
    if(!quelle.value||erkennen.disabled)return;
    const nr=marke;
    erkennen.disabled=true;
    anzeige.textContent="Notenerkennung auf lokaler CPU gestartet …";
    try {
      const daten=await api.stemNotenStart(pfad,modell,quelle.value);
      darstellen(daten,nr);
    } catch(err) {
      if(!beendet&&nr===marke) {
        anzeige.textContent=err.meldung||"Notenerkennung konnte nicht gestartet werden.";
        erkennen.disabled=false;
      }
    }
  });
  umschalten.addEventListener("click",()=>wechseln(!synth.aktiv));
  if(spuren.length)neu();
  return {
    el:h("section",{class:"stems-labor"},
      h("div",{},h("span",{class:"stems-kicker"},"MORPH ENGINE · BASIC PITCH"),
        h("h2",{},"Tausch die Instrumente mitten im Song.")),
      h("div",{class:"stems-labor-grid"},
        h("label",{},"Stem auswählen",quelle),
        h("label",{},"Neuer Klang",sound),
        erkennen,umschalten),
      anzeige,info),
    aktuelleSpur:()=>synth.aktiv?quelle.value:null,
    pegel:(v)=>synth.setLautstaerke(v),
    play:()=>{if(synth.aktiv)synth.start();},
    pause:()=>synth.stop(),
    seek:()=>{if(synth.aktiv){synth.suchen(player.position());synth.tick();}},
    tick:()=>synth.tick(),
    beenden() {
      beendet=true;
      marke++;
      clearTimeout(timer);
      wechseln(false);
      synth.beenden();
    },
  };
}
