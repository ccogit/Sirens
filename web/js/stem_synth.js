// Instrument-Labor: Basic-Pitch-Noten statt eines Stems live mit Web-Audio-Klängen spielen.
// Kein Sample-Download, kein externer Synthesizer. Klangfarben sind synthetische Annäherungen.
export const SYNTH_KLAENGE = Object.freeze({
  synth: "Neon Lead", bell: "Crystal Bells", keys: "Electric Keys",
  strings: "Cyber Strings", bass: "Sub Bass",
});

export function noteGueltig(n) {
  return Array.isArray(n) && n.length >= 4 &&
    n.every((x) => typeof x === "number" && Number.isFinite(x)) &&
    n[0] >= 0 && n[1] > n[0] && n[1] <= 7200 &&
    Number.isInteger(n[2]) && n[2] >= 0 && n[2] <= 127 && n[3] >= 0 && n[3] <= 1;
}

export class StemSynth {
  constructor(player) {
    this.player = player;
    this.events = [];
    this.naechste = 0;
    this.programm = "synth";
    this.aktiv = false;
    this.stimmen = new Set();
    this.gain = player.ctx.createGain();
    this.gain.gain.value = .65;
    this.gain.connect(player.analyser);
  }

  setNoten(noten) {
    this.stop();
    this.events = (Array.isArray(noten) ? noten : []).filter(noteGueltig).slice(0, 12000)
      .sort((a,b) => a[0] - b[0]);
  }

  setInstrument(programm) {
    if (!Object.hasOwn(SYNTH_KLAENGE, programm)) return;
    this.stop();
    this.programm = programm;
    if (this.aktiv && this.player.laeuft) this.suchen(this.player.position());
  }

  setLautstaerke(wert) {
    if (!this.player.ctx) return;
    this.gain.gain.setTargetAtTime(Math.max(0,Math.min(1,wert*.75)),this.player.ctx.currentTime,.02);
  }

  suchen(sekunden) {
    this.stop();
    // Bereits klingende Noten bleiben beim Springen erhalten, sofern ihre Endzeit noch nicht vorbei ist.
    this.naechste = this.events.findIndex((event) => event[1] > sekunden);
    if (this.naechste < 0) this.naechste = this.events.length;
  }

  start() {
    if (!this.aktiv) return;
    this.suchen(this.player.position());
    this.tick();
  }

  stop() {
    for (const {oscillator, gain} of this.stimmen) {
      oscillator.onended = null;
      try {
        gain.gain.cancelScheduledValues(0);
        gain.gain.value = 0;
        oscillator.stop();
      } catch { /* Stimme bereits beendet */ }
      oscillator.disconnect();
      gain.disconnect();
    }
    this.stimmen.clear();
  }

  tick() {
    if (!this.aktiv || !this.player.laeuft || !this.player.ctx) return;
    const position = this.player.position();
    const ende = position + .22;
    const ctx = this.player.ctx;
    while (this.naechste < this.events.length) {
      const note = this.events[this.naechste];
      if (note[0] > ende) break;
      this.naechste++;
      if (note[1] <= position || this.stimmen.size >= 24) continue;
      const von = Math.max(ctx.currentTime + .008, this.player.startAt + note[0]);
      const bis = Math.max(von + .06, this.player.startAt + note[1]);
      this.spielen(note[2],note[3],von,bis);
    }
  }

  spielen(midi, velocity, von, bis) {
    const ctx = this.player.ctx;
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    const grundton=440*Math.pow(2,(midi-69)/12);
    oscillator.frequency.value = Math.max(30,Math.min(5500,grundton));
    oscillator.type = {synth:"sawtooth",bell:"sine",keys:"triangle",strings:"sawtooth",bass:"sine"}[this.programm];
    let attack=.012, release=.1, peak=Math.min(.35,Math.max(.025,velocity*.28));
    if (this.programm === "bell") { attack=.003; release=.75; peak*=.85; }
    if (this.programm === "strings") { attack=.12; release=.3; peak*=.65; }
    if (this.programm === "bass") { attack=.01; release=.16; peak*=1.2; oscillator.frequency.value/=2; }
    if (this.programm === "keys") { attack=.004; release=.18; }
    const dauern=Math.min(5,Math.max(.05,bis-von));
    const loslassen=von+dauern;
    gain.gain.setValueAtTime(0,von);
    gain.gain.linearRampToValueAtTime(peak,von+Math.min(attack,dauern*.4));
    gain.gain.setValueAtTime(peak*.65,loslassen);
    gain.gain.exponentialRampToValueAtTime(.0001,loslassen+release);
    oscillator.connect(gain).connect(this.gain);
    const stimme={oscillator,gain};
    this.stimmen.add(stimme);
    oscillator.onended=()=>{this.stimmen.delete(stimme);oscillator.disconnect();gain.disconnect();};
    oscillator.start(von);
    oscillator.stop(loslassen+release+.02);
  }

  beenden() {
    this.aktiv=false;
    this.stop();
    this.events=[];
    this.gain.disconnect();
  }
}
