// Tonwerk der Spielwiese: ein Song im Speicher, in Echtzeit verbogen – Filter, Echo, Tempo, Stottern, Rückwärts, Bremse.
import { spielFilter } from "./logic.js";

const SANFT = 0.04; // Sekunden, in denen ein Regler seinen neuen Wert erreicht (kein Knacken)

export function tonwerk() {
  let ctx = null;
  let knoten = null;
  let puffer = null;
  let rueck = null;       // derselbe Song rückwärts, erst beim ersten Gebrauch angelegt
  let quelle = null;
  let pos = 0;            // gedachte Abspielstelle in Sekunden; läuft auch beim Stottern weiter
  let richtung = 1;
  let letzte = 0;
  let tempo = 1;
  let laeuft = false;

  function bauen() {
    ctx = new AudioContext();
    const tief = ctx.createBiquadFilter();
    tief.type = "lowpass"; tief.frequency.value = 20000; tief.Q.value = 1.2;
    const hoch = ctx.createBiquadFilter();
    hoch.type = "highpass"; hoch.frequency.value = 20; hoch.Q.value = 1.2;
    const echo = ctx.createDelay(1);
    echo.delayTime.value = 0.33;
    const rueckweg = ctx.createGain();
    const nass = ctx.createGain();
    rueckweg.gain.value = 0; nass.gain.value = 0;
    const messer = ctx.createAnalyser();
    messer.fftSize = 2048; messer.smoothingTimeConstant = 0.82;
    // Quelle → Tiefpass → Hochpass → Ausgang; daneben das Echo mit Rückweg
    tief.connect(hoch); hoch.connect(messer); hoch.connect(echo);
    echo.connect(rueckweg); rueckweg.connect(echo); echo.connect(nass); nass.connect(messer);
    messer.connect(ctx.destination);
    knoten = { tief, hoch, rueckweg, nass, messer };
  }

  function umgedreht(original) {
    const neu = ctx.createBuffer(original.numberOfChannels, original.length, original.sampleRate);
    for (let k = 0; k < original.numberOfChannels; k += 1) {
      const kanal = neu.getChannelData(k);
      kanal.set(original.getChannelData(k));
      kanal.reverse();
    }
    return neu;
  }

  function stumm() {
    if (!quelle) return;
    try { quelle.stop(); } catch { /* lief noch nicht */ }
    quelle.disconnect();
    quelle = null;
  }

  // Ab der gedachten Stelle spielen; `schleife` (Sekunden) wiederholt ein Stück, `rueckwaerts` dreht die Richtung.
  function abspielen({ rueckwaerts = false, schleife = 0 } = {}) {
    stumm();
    quelle = ctx.createBufferSource();
    quelle.buffer = rueckwaerts ? (rueck ||= umgedreht(puffer)) : puffer;
    quelle.playbackRate.value = tempo;
    const start = Math.max(0, Math.min(rueckwaerts ? puffer.duration - pos : pos, puffer.duration - 0.02));
    if (schleife) {
      quelle.loop = true; quelle.loopStart = start; quelle.loopEnd = Math.min(puffer.duration, start + schleife);
    }
    quelle.connect(knoten.tief);
    quelle.start(0, start);
    richtung = rueckwaerts ? -1 : 1;
    letzte = ctx.currentTime;
    laeuft = true;
  }

  const ziel = (param, wert, dauer = SANFT) => param.setTargetAtTime(wert, ctx.currentTime, dauer);

  return {
    get bereit() { return Boolean(puffer); },
    get laeuft() { return laeuft; },
    get dauer() { return puffer ? puffer.duration : 0; },
    get messer() { return knoten ? knoten.messer : null; },
    get daten() { return puffer ? puffer.getChannelData(0) : null; },
    get rate() { return puffer ? puffer.sampleRate : 0; },

    // Song holen und entpacken. Muss aus einem Klick heraus aufgerufen werden (der Browser verlangt das für Ton).
    async laden(url) {
      if (!ctx) bauen();
      await ctx.resume();
      const antwort = await fetch(url);
      if (!antwort.ok) throw new Error("Die Datei lässt sich nicht laden.");
      const neu = await ctx.decodeAudioData(await antwort.arrayBuffer());
      stumm();
      puffer = neu; rueck = null; pos = 0; laeuft = false;
    },

    spielen() { if (puffer && !laeuft) { ctx.resume(); abspielen(); } },
    pause() { if (laeuft) { this.takt(); stumm(); laeuft = false; } },
    springen(sekunde) {
      pos = Math.max(0, Math.min(sekunde, this.dauer - 0.05));
      if (laeuft) abspielen();
    },

    // Einmal je Bild aufrufen: führt die gedachte Abspielstelle fort. Liefert true, wenn das Stück zu Ende ist.
    takt() {
      if (!laeuft || !quelle) return false;
      const jetzt = ctx.currentTime;
      pos += richtung * (jetzt - letzte) * quelle.playbackRate.value;
      letzte = jetzt;
      if (pos <= 0) { pos = 0; if (richtung < 0) abspielen(); }  // rückwärts am Anfang angekommen: wieder vorwärts
      if (pos >= puffer.duration) { stumm(); laeuft = false; pos = 0; return true; }
      return false;
    },
    get stelle() { return pos; },

    // Gedrückt gehaltene Effekte; beim Loslassen geht es an der gedachten Stelle weiter.
    stottern(an, laenge = 0.18) { if (laeuft) { this.takt(); abspielen(an ? { schleife: laenge } : {}); } },
    rueckwaerts(an) { if (laeuft) { this.takt(); abspielen({ rueckwaerts: an }); } },
    bremsen(an) { if (quelle) ziel(quelle.playbackRate, an ? 0.0001 : tempo, an ? 0.28 : 0.09); },
    tempo(wert) { tempo = wert; if (quelle) ziel(quelle.playbackRate, wert); },

    // Spielfläche: x (0…1) filtert, y (0…1, oben = 1) bringt Echo. `null` lässt los, alles geht zurück auf neutral.
    flaeche(x, y) {
      if (!knoten) return;
      const f = spielFilter(x ?? 0.5);
      const echo = y == null ? 0 : Math.max(0, Math.min(1, y));
      ziel(knoten.tief.frequency, f.tief); ziel(knoten.hoch.frequency, f.hoch);
      ziel(knoten.nass.gain, echo * 0.65); ziel(knoten.rueckweg.gain, echo * 0.72);
    },
  };
}
