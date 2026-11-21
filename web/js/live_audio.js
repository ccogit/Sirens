// Realtime-Engine: zwei Decks, GPU-unabhängige Web-Audio-Effekte und eigene Drum-Pads.
// Alle Klänge bleiben im Browser; lokale Dateien werden nicht hochgeladen.
export class LiveAudio {
  constructor() {
    this.ctx = null;
    this.analyser = null;
    this.urls = [null, null];
    this.decks = [new Audio(), new Audio()];
    for (const audio of this.decks) audio.preload = "metadata";
  }

  async aktivieren() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) throw new Error("Dieser Browser unterstützt Web Audio nicht.");
      const ctx = this.ctx = new AudioContext();
      this.mix = ctx.createGain();
      this.filter = ctx.createBiquadFilter();
      this.filter.type = "lowpass";
      this.filter.frequency.value = 18000;
      this.drive = ctx.createWaveShaper();
      this.drive.oversample = "2x";
      this.delay = ctx.createDelay(1.0);
      this.delay.delayTime.value = 0.27;
      this.feedback = ctx.createGain();
      this.feedback.gain.value = 0.32;
      this.wet = ctx.createGain();
      this.wet.gain.value = 0;
      this.dry = ctx.createGain();
      this.dry.gain.value = 0.75;
      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 2048;
      this.analyser.smoothingTimeConstant = 0.78;
      this.gains = this.decks.map((audio) => {
        const source = ctx.createMediaElementSource(audio);
        const gain = ctx.createGain();
        source.connect(gain).connect(this.mix);
        return gain;
      });
      this.mix.connect(this.filter).connect(this.drive);
      this.drive.connect(this.dry).connect(this.analyser);
      this.drive.connect(this.delay).connect(this.wet).connect(this.analyser);
      this.delay.connect(this.feedback).connect(this.delay);
      this.analyser.connect(ctx.destination);
      this.setCrossfade(50);
      this.setDrive(0);
    }
    if (this.ctx.state === "suspended") await this.ctx.resume();
  }

  laden(index, src, istDatei = false) {
    const audio = this.decks[index];
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    if (this.urls[index]) URL.revokeObjectURL(this.urls[index]);
    this.urls[index] = istDatei ? URL.createObjectURL(src) : null;
    audio.src = this.urls[index] || src;
    audio.load();
  }

  async schalten(index) {
    await this.aktivieren();
    const audio = this.decks[index];
    if (!audio.src) return;
    if (audio.paused) await audio.play(); else audio.pause();
  }

  setCrossfade(position) {
    if (!this.gains) return;
    const x = Math.min(1, Math.max(0, Number(position) / 100));
    for (const g of this.gains) g.gain.cancelScheduledValues(this.ctx.currentTime);
    this.gains[0].gain.setTargetAtTime(Math.cos(x * Math.PI / 2), this.ctx.currentTime, 0.02);
    this.gains[1].gain.setTargetAtTime(Math.sin(x * Math.PI / 2), this.ctx.currentTime, 0.02);
  }

  autoCrossfade(von, sekunden) {
    if (!this.ctx || !this.gains) return;
    const start = this.ctx.currentTime + 0.03;
    const n = 128;
    const weg = new Float32Array(n);
    const hin = new Float32Array(n);
    for (let i=0; i<n; i++) {
      const phase = (i/(n-1))*Math.PI/2;
      weg[i] = Math.max(0.00001,Math.cos(phase));
      hin[i] = Math.max(0.00001,Math.sin(phase));
    }
    for (const gain of this.gains) gain.gain.cancelScheduledValues(this.ctx.currentTime);
    const aus=this.gains[von].gain, ein=this.gains[1-von].gain;
    aus.setValueAtTime(1,start);
    ein.setValueAtTime(0,start);
    aus.setValueCurveAtTime(weg,start,Math.max(.1,sekunden));
    ein.setValueCurveAtTime(hin,start,Math.max(.1,sekunden));
  }

  setFilter(position) {
    if (!this.filter) return;
    const frequency = 220 * Math.pow(18000 / 220, Number(position) / 100);
    this.filter.frequency.setTargetAtTime(frequency, this.ctx.currentTime, 0.025);
  }

  setDrive(position) {
    if (!this.drive) return;
    const k = Number(position) * 0.5;
    const curve = new Float32Array(2048);
    for (let i = 0; i < curve.length; i++) {
      const x = i / (curve.length - 1) * 2 - 1;
      curve[i] = (1 + k) * x / (1 + k * Math.abs(x));
    }
    this.drive.curve = curve;
  }

  setEcho(position) {
    if (!this.wet) return;
    this.wet.gain.setTargetAtTime(Number(position) / 100 * 0.48, this.ctx.currentTime, 0.02);
  }

  setTempo(index, position) {
    const audio = this.decks[index];
    audio.playbackRate = Number(position) / 100;
    audio.preservesPitch = false;
  }

  async pad(art) {
    await this.aktivieren();
    const ctx = this.ctx, now = ctx.currentTime;
    const envelope = (source, duration, volume) => {
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(Math.max(volume, 0.001), now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
      source.connect(gain).connect(this.mix);
      source.start(now);
      source.stop(now + duration + 0.02);
    };
    if (art === "kick") {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(160, now);
      osc.frequency.exponentialRampToValueAtTime(43, now + 0.20);
      envelope(osc, 0.30, 0.72);
    } else if (art === "bass" || art === "chord") {
      const notes = art === "bass" ? [55] : [220, 261.63, 329.63];
      notes.forEach((hz) => {
        const osc = ctx.createOscillator();
        osc.type = art === "bass" ? "sawtooth" : "sine";
        osc.frequency.value = hz;
        envelope(osc, art === "bass" ? 0.30 : 0.85, art === "bass" ? 0.28 : 0.14);
      });
    } else {
      const duration = art === "hat" ? 0.09 : 0.22;
      const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * duration), ctx.sampleRate);
      const channel = buffer.getChannelData(0);
      for (let i = 0; i < channel.length; i++) channel[i] = Math.random() * 2 - 1;
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      const hp = ctx.createBiquadFilter();
      hp.type = "highpass";
      hp.frequency.value = art === "hat" ? 6500 : 900;
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(art === "hat" ? 0.18 : 0.24, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
      src.connect(hp).connect(gain).connect(this.mix);
      src.start(now);
      src.stop(now + duration + 0.02);
    }
  }

  beenden() {
    for (const audio of this.decks) {
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
    }
    for (const url of this.urls) if (url) URL.revokeObjectURL(url);
    this.urls = [null, null];
    if (this.ctx) this.ctx.close().catch(() => {});
    this.ctx = null;
    this.analyser = null;
  }
}
