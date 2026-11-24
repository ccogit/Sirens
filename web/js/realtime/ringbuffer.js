// Zeitadressierter Stereo-Ring: nur der Besitzer schreibt und liest.
export class RingBuffer {
    constructor(capacity = 8 * 2048) {
        if (!Number.isSafeInteger(capacity) || capacity < 1) throw new RangeError("Kapazität");
        this.capacity = capacity;
        this.samples = new Float32Array(capacity * 2);
        this.frames = new Float64Array(capacity);
        this.epoch = 0;
        this.underruns = 0;
        this.reset(0, 0);
    }
    reset(epoch, frame) {
        this.epoch = epoch;
        this.cursor = frame;
        this.frames.fill(-1);
        this.count = 0;
    }
    write(epoch, start, samples) {
        const n = samples.length / 2;
        if (epoch !== this.epoch || !Number.isSafeInteger(start) || !Number.isInteger(n) ||
            start < this.cursor || start + n > this.cursor + this.capacity || n < 1) return false;
        for (let i = 0; i < n; i++) {
            if (this.frames[(start + i) % this.capacity] !== -1) return false;
        }
        for (let i = 0; i < n; i++) {
            const frame = start + i, slot = frame % this.capacity;
            this.frames[slot] = frame;
            for (let c = 0; c < 2; c++) {
                const v = samples[i * 2 + c];
                this.samples[slot * 2 + c] = Number.isFinite(v) ? v : 0;
            }
        }
        this.count += n;
        return true;
    }
    // Keine Allokation; Zielpaar wird auch bei einer Lücke vollständig überschrieben.
    read(pair) {
        const frame = this.cursor++, slot = frame % this.capacity;
        if (this.frames[slot] !== frame) {
            pair[0] = pair[1] = 0;
            this.underruns++;
            return false;
        }
        pair[0] = this.samples[slot * 2];
        pair[1] = this.samples[slot * 2 + 1];
        this.frames[slot] = -1;
        this.count--;
        return true;
    }
}
