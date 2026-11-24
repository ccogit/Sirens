import {createBeatGrid} from "./beat_grid.js";

export const PAD_TYPES = Object.freeze(["Rise", "Fill", "Drop", "Break", "Bassline", "Extend"]);
const frame = n => {
  if (!Number.isSafeInteger(n) || n < 0) throw new RangeError("Frame");
  return n;
};

// Alle Frames liegen auf derselben Quellzeitachse. Der Aufrufer plant die
// zurückgegebenen Einsätze im Audio-Thread, nicht per JavaScript-Timer.
export class PadScheduler {
  constructor({grid, sampleRate, p95Ms, safetyMs=80, maxPending=4,
    maxShifts=1, maxStretch=0.05, crossfadeMs=20, phraseBars=1}) {
    for (const v of [p95Ms, safetyMs, crossfadeMs, maxStretch])
      if (!Number.isFinite(v) || v < 0) throw new RangeError("Scheduler-Profil");
    for (const v of [maxPending, maxShifts, phraseBars]) frame(v);
    if (!maxPending || !phraseBars || maxStretch > 0.1) throw new RangeError("Scheduler-Grenzen");
    this.rate = sampleRate;
    this.safety = Math.ceil(safetyMs*sampleRate/1000);
    this.lead = Math.ceil((p95Ms+safetyMs)*sampleRate/1000);
    this.fade = Math.round(crossfadeMs*sampleRate/1000);
    this.maxPending = maxPending;
    this.maxShifts = maxShifts;
    this.maxStretch = maxStretch;
    this.phraseBars = phraseBars;
    this.jobs = new Map();
    this.sequence = 0;
    this.clock = 0;
    try { this.grid = createBeatGrid(grid, sampleRate); }
    catch (e) { if (!(e instanceof RangeError)) throw e; this.grid = null; }
  }
  advance(now) {
    frame(now);
    if (now < this.clock) throw new RangeError("Zeitsprung: Scheduler zurücksetzen");
    this.clock = now;
  }
  boundary(after) {
    let target = this.grid.nextBar(after);
    while (Math.round(this.grid.frameToBar(target)) % this.phraseBars !== 0)
      target = this.grid.nextBar(target);
    return target;
  }
  request({type, bars, prompt, seed, strength=1}, now) {
    this.advance(now);
    if (!PAD_TYPES.includes(type) || ![1,2,4,8].includes(bars) ||
      typeof prompt !== "string" || !prompt.trim() || prompt.length > 1000 ||
      !Number.isSafeInteger(seed) || seed < 0 ||
      !Number.isFinite(strength) || strength < 0 || strength > 1) throw new RangeError("Pad-Parameter");
    if (!this.grid) return {status:"dry", reason:"BeatGrid unsicher"};
    if (this.jobs.size >= this.maxPending) return {status:"dry", reason:"Warteschlange voll"};
    const startFrame = this.boundary(now+this.lead);
    const job = {id:++this.sequence, type, bars, prompt, seed, strength,
      startFrame, deadlineFrame:startFrame-this.safety, shifts:0, status:"rendering"};
    this.jobs.set(job.id, job);
    return {...job, durationFrames:this.duration(job)};
  }
  duration(job) {
    return this.grid.barToFrame(Math.round(this.grid.frameToBar(job.startFrame))+job.bars)-job.startFrame;
  }
  ready(id, clip, now) {
    this.advance(now);
    const job = this.jobs.get(id);
    if (!job || job.status !== "rendering") return {status:"dry", reason:"Job nicht aktiv"};
    if (!clip || !Number.isSafeInteger(clip.frames) || clip.frames <= 0 || clip.sampleRate !== this.rate) {
      this.jobs.delete(id);
      return {status:"dry", reason:"Ungültiges Clipformat"};
    }
    while (now > job.deadlineFrame && job.shifts < this.maxShifts) {
      job.startFrame = this.boundary(job.startFrame);
      job.deadlineFrame = job.startFrame-this.safety;
      job.shifts++;
    }
    if (now > job.deadlineFrame) {
      this.jobs.delete(id);
      return {status:"dry", reason:"Frist verpasst"};
    }
    const durationFrames = this.duration(job);
    const playbackRate = clip.frames/durationFrames;
    if (Math.abs(playbackRate-1) > this.maxStretch) {
      this.jobs.delete(id);
      return {status:"dry", reason:"Stretch-Grenze überschritten"};
    }
    Object.assign(job, {status:"ready", clip, durationFrames, playbackRate,
      warning:playbackRate === 1 ? null : "Begrenztes Stretching erforderlich"});
    return {...job};
  }
  preview(id) {
    const job = this.jobs.get(id);
    return job?.status === "ready" ? job.clip : null;
  }
  // Erst nach expliziter Freigabe wird ein Einsatzplan herausgegeben.
  take(id, now) {
    this.advance(now);
    const job = this.jobs.get(id);
    if (!job || job.status !== "ready") return {status:"dry", reason:"Clip nicht bereit"};
    this.jobs.delete(id);
    if (now > job.deadlineFrame) return {status:"dry", reason:"Freigabe zu spät"};
    return {...job, status:"scheduled", crossfadeFrames:Math.min(this.fade, Math.floor(job.durationFrames/2))};
  }
  cancel(id) { return this.jobs.delete(id); }
  reset() { this.jobs.clear(); this.clock = 0; }
}
