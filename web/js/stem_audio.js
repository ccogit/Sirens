// Samplegenauer Mehrspur-Player: alle Demucs-WAV-Dateien werden mit demselben
// AudioContext und einem gemeinsamen Startzeitpunkt abgespielt.
// Die WAVs kommen ausschließlich vom lokalen Sirens-Dienst.
export class StemAudio {
  constructor() {
    this.ctx = null;
    this.buffers = [];
    this.gains = [];
    this.sources = [];
    this.dauer = 0;
    this.offset = 0;
    this.startAt = 0;
    this.laeuft = false;
    this.beendet = false;
    this.abort = new AbortController();
    this.onEnde = null;
  }

  async laden(urls, fortschritt = () => {}) {
    if (this.beendet) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) throw new Error("Dein Browser unterstützt Web Audio nicht.");
    const ctx = this.ctx = new AudioCtx();
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 2048;
    this.analyser.smoothingTimeConstant = .77;
    this.analyser.connect(ctx.destination);
    for (let i = 0; i < urls.length; i++) {
      if (this.beendet) return;
      fortschritt(i + 1, urls.length);
      const antwort = await fetch(urls[i], { signal: this.abort.signal });
      if (!antwort.ok) throw new Error("Stem " + (i + 1) + " konnte nicht geladen werden (HTTP " + antwort.status + ").");
      const daten = await antwort.arrayBuffer();
      if (this.beendet) return;
      const buffer = await ctx.decodeAudioData(daten);
      if (this.beendet) return;
      this.buffers.push(buffer);
      const gain = ctx.createGain();
      gain.gain.value = 1;
      gain.connect(this.analyser);
      this.gains.push(gain);
    }
    if (!this.buffers.length) throw new Error("Keine Audiospuren gefunden.");
    this.dauer = Math.min(...this.buffers.map((buffer) => buffer.duration));
    if (!Number.isFinite(this.dauer) || this.dauer <= 0) throw new Error("Die Audiospuren sind leer.");
  }

  get bereit() {
    return this.buffers.length > 0 && !this.beendet && this.dauer > 0;
  }

  position() {
    return Math.max(0, Math.min(this.dauer, this.laeuft ? this.ctx.currentTime - this.startAt : this.offset));
  }

  _stopQuellen() {
    for (const quelle of this.sources) {
      quelle.onended = null;
      try { quelle.stop(); } catch { /* war bereits beendet */ }
      quelle.disconnect();
    }
    this.sources = [];
  }

  _starten() {
    this._stopQuellen();
    if (this.offset >= this.dauer) this.offset = 0;
    const beginn = this.ctx.currentTime + .05;
    this.startAt = beginn - this.offset;
    const version = Symbol("wiedergabe");
    this.version = version;
    this.sources = this.buffers.map((buffer, i) => {
      const quelle = this.ctx.createBufferSource();
      quelle.buffer = buffer;
      quelle.connect(this.gains[i]);
      // Exakt gleicher AudioContext-Zeitstempel: keine hörbare Drift der Stems.
      quelle.start(beginn, this.offset, Math.max(.001, this.dauer - this.offset));
      if (i === 0) quelle.onended = () => {
        if (this.version !== version || !this.laeuft || this.beendet) return;
        this.laeuft = false;
        this.offset = 0;
        this._stopQuellen();
        this.onEnde?.();
      };
      return quelle;
    });
    this.laeuft = true;
  }

  async schalten() {
    if (!this.bereit) return;
    if (this.laeuft) { this.pause(); return; }
    if (this.ctx.state === "suspended") await this.ctx.resume();
    if (this.beendet) return;
    this._starten();
  }

  pause() {
    if (!this.laeuft) return;
    this.offset = this.position();
    this.laeuft = false;
    this._stopQuellen();
  }

  springen(sekunden) {
    if (!this.bereit) return;
    const warAn = this.laeuft;
    if (warAn) this.pause();
    this.offset = Math.max(0, Math.min(this.dauer, Number(sekunden) || 0));
    if (warAn) this._starten();
  }

  pegel(index, wert) {
    if (!this.gains[index]) return;
    this.gains[index].gain.setTargetAtTime(Math.max(0, Math.min(1, Number(wert) || 0)), this.ctx.currentTime, .012);
  }

  beenden() {
    this.beendet = true;
    this.abort.abort();
    this.pause();
    this._stopQuellen();
    this.buffers = [];
    this.gains = [];
    this.analyser = null;
    const ctx = this.ctx;
    this.ctx = null;
    if (ctx) ctx.close().catch(() => {});
  }
}
