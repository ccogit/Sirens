// Eine Master-Uhr; Quell- und Ausgabeframes sind getrennt.
export class Clock {
    constructor(rate) {
        if (!Number.isInteger(rate) || rate <= 0) throw new RangeError("Abtastrate");
        this.rate = rate;
        this.epoch = 0;
        this.output = 0;
        this.source = 0;
        this.playing = false;
        this.loopStart = 0;
        this.loopEnd = 0;
    }
    static frame(time, rate) { return Math.round(time * rate); }
    seek(source) {
        if (!Number.isSafeInteger(source) || source < 0 || this.epoch >= 0xffffffff)
            throw new RangeError("Epoch/Quellframe");
        this.source = source;
        return ++this.epoch;
    }
    stop() { this.playing = false; return this.seek(0); }
    loop(start, end) {
        if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end <= start)
            throw new RangeError("Loop");
        this.loopStart = start; this.loopEnd = end;
    }
    // Pro Sample; keine Allokation. Loopwechsel erzeugt eine neue Epoch.
    tick() {
        this.output++;
        if (this.playing && ++this.source === this.loopEnd) this.seek(this.loopStart);
    }
}
