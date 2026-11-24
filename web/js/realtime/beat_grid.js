/** BeatGrid v1: Quellframes bei expliziter Samplerate, 4/4-Takt.
 * Tempo-Wechsel sind ab source_frame wirksam, die Schlagphase bleibt stetig.
 * Keine automatische Quantisierung bei unsicherem Raster (confidence < 0.5).
 */
export const MIN_CONFIDENCE = 0.5;
function number(v, name) {
  if (typeof v !== "number" || !Number.isFinite(v)) throw new RangeError(name);
  return v;
}
function frame(v) {
  if (!Number.isSafeInteger(v) || v < 0) throw new RangeError("Quellframe");
  return v;
}
function bpm(v) {
  if (number(v, "BPM") < 1 || v > 1000) throw new RangeError("BPM");
  return v;
}
export function createBeatGrid(grid, sampleRate) {
  if (!Number.isSafeInteger(sampleRate) || sampleRate <= 0) throw new RangeError("Samplerate");
  if (!grid || number(grid.confidence, "Konfidenz") < MIN_CONFIDENCE || grid.confidence > 1)
    throw new RangeError("BeatGrid unsicher");
  const beat0 = frame(grid.beat0), bar0 = frame(grid.bar0);
  const segments = [{frame: 0, bpm: bpm(grid.bpm), beat: 0}];
  let prev = -1;
  const map = grid.tempo_map ?? [];
  if (!Array.isArray(map) || map.length > 4096) throw new RangeError("Tempo-Karte");
  for (const point of map) {
    const f = frame(point.source_frame), t = bpm(point.bpm);
    if (f <= prev) throw new RangeError("Tempo-Karte nicht streng aufsteigend");
    prev = f;
    const last = segments.at(-1);
    if (f === 0) last.bpm = t;
    else segments.push({frame: f, bpm: t, beat: last.beat + (f-last.frame)*last.bpm/(60*sampleRate)});
  }
  function segment(key, value) {
    let lo = 0, hi = segments.length;
    while (lo+1 < hi) {
      const mid = (lo+hi) >> 1;
      if (segments[mid][key] <= value) lo = mid;
      else hi = mid;
    }
    return segments[lo];
  }
  function absoluteBeat(f) {
    const s = segment("frame", f);
    return s.beat + (f-s.frame)*s.bpm/(60*sampleRate);
  }
  const origin = absoluteBeat(beat0), barOrigin = absoluteBeat(bar0)-origin;
  function frameToBeat(f) { return absoluteBeat(frame(f))-origin; }
  function beatToFrame(b) {
    const absolute = number(b, "Schlag")+origin;
    const s = segment("beat", absolute);
    return frame(Math.round(s.frame+(absolute-s.beat)*60*sampleRate/s.bpm));
  }
  function beatToBar(b) { return (number(b, "Schlag")-barOrigin)/4; }
  function barToBeat(b) { return number(b, "Takt")*4+barOrigin; }
  function frameToBar(f) { return beatToBar(frameToBeat(f)); }
  function barToFrame(b) { return beatToFrame(barToBeat(b)); }
  function nextBar(f) {
    frame(f);
    let b = Math.floor(frameToBar(f));
    // Vor dem ersten Quellframe darf kein negativer Frame zurückgegeben werden.
    while (true) {
      const absolute = barToBeat(b)+origin;
      const s = segment("beat", absolute);
      const candidate = Math.round(s.frame+(absolute-s.beat)*60*sampleRate/s.bpm);
      if (candidate > f) return frame(candidate);
      b++;
    }
  }
  function quantize(f, step=1) {
    if (number(step, "Raster") <= 0) throw new RangeError("Raster");
    const b = Math.round(frameToBeat(f)/step)*step;
    try { return beatToFrame(b); }
    catch (e) {
      if (!(e instanceof RangeError)) throw e;
      return beatToFrame(Math.ceil(-origin/step)*step);
    }
  }
  return Object.freeze({frameToBeat, beatToFrame, beatToBar, barToBeat,
    frameToBar, barToFrame, nextBar, quantize});
}
