/** WP11: deterministischer Random-Walk an exakten BeatGrid-Taktgrenzen.
 * Übergabe der createBeatGrid()-Instanz aus WP10; kein eigener Tempo-Schätzer.
 */
export function createWalk(grid, {seed=0, step=0.125, initial=0, startFrame=0}={}) {
  if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647 ||
      !Number.isFinite(step) || step < 0 || step > 2 ||
      !Number.isFinite(initial) || Math.abs(initial)>2 ||
      !Number.isSafeInteger(startFrame) || startFrame<0)
    throw new RangeError("Random-Walk-Preset");
  let state = (seed ^ 0x9e3779b9) >>> 0;
  let value = initial, last = startFrame, boundary = grid.nextBar(startFrame);
  function random() {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    return (state >>> 0)/4294967296;
  }
  return Object.freeze({
    // Liefert die Ereignisse mit ihren tatsächlichen Frames, nicht den Abfrageframe.
    advance(frame) {
      if (!Number.isSafeInteger(frame) || frame<last) throw new RangeError("Seek: Walk neu erstellen");
      const events = [];
      while (boundary<=frame) {
        if(events.length>=4096) throw new RangeError("Zu viele Taktgrenzen; Walk neu erstellen");
        value = Math.max(-2,Math.min(2,value+(2*random()-1)*step));
        events.push({frame:boundary,latent_0:value});
        boundary=grid.nextBar(boundary);
      }
      last=frame;
      return events;
    },
    get value() { return value; }
  });
}
