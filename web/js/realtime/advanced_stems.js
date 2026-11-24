// Offline-Mix vorbereiten; kein zweiter AudioContext.
export function mixStems(original, stems, settings = {}, dry = false) {
    const length = original.length;
    if (!(original instanceof Float32Array) || !length || !Array.from(original).every(Number.isFinite))
        throw new Error("Ungültige Quelle");
    if (dry) return original.slice();
    const entries = Object.entries(stems);
    if (!entries.length) throw new Error("Keine Spuren");
    const solo = entries.some(([name]) => settings[name]?.solo);
    const result = new Float32Array(length);
    for (const [name, samples] of entries) {
        const {gain = 1, mute = false, solo: selected = false} = settings[name] || {};
        if (!(samples instanceof Float32Array) || samples.length !== length ||
            !Number.isFinite(gain) || gain < 0 || gain > 2)
            throw new Error("Ungültige Spur");
        for (let i = 0; i < length; i++) {
            if (!Number.isFinite(samples[i])) throw new Error("Ungültiges Sample");
            if (!mute && (!solo || selected)) result[i] += gain * samples[i];
        }
    }
    return result;
}

export function wavExport(samples, rate, channels = 2) {
    if (!(samples instanceof Float32Array) || !Number.isInteger(rate) || rate <= 0 ||
        ![1, 2].includes(channels) || samples.length % channels || samples.length > 0x7fffffe0)
        throw new Error("Ungültiges WAV-Format");
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const v = new DataView(buffer);
    const text = (offset, word) => [...word].forEach((c, i) => v.setUint8(offset + i, c.charCodeAt(0)));
    text(0, "RIFF"); v.setUint32(4, buffer.byteLength - 8, true);
    text(8, "WAVE"); text(12, "fmt "); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, channels, true);
    v.setUint32(24, rate, true); v.setUint32(28, rate * channels * 2, true);
    v.setUint16(32, channels * 2, true); v.setUint16(34, 16, true);
    text(36, "data"); v.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
        if (!Number.isFinite(samples[i]) || Math.abs(samples[i]) > 1)
            throw new Error("Export würde clippen");
        v.setInt16(44 + 2 * i, Math.round(samples[i] * (samples[i] < 0 ? 32768 : 32767)), true);
    }
    return buffer;
}

// Controller liefert dekodierte, gleich ausgerichtete interleavte PCM-Daten
// und einen Ausgabepfad des bestehenden Players.
export function mountAdvancedStems(host, {original, stems, rate, onMix, onExport}) {
    const doc = host.ownerDocument;
    const panel = doc.createElement("section");
    const status = doc.createElement("p");
    status.textContent = "Offline vorbereitete Spuren";
    panel.append(status);
    const settings = Object.create(null);
    let dry = false;
    const refresh = () => {
        try { onMix(mixStems(original, stems, settings, dry)); status.textContent = "Mix vorbereitet"; }
        catch (e) { status.textContent = e.message; }
    };
    const button = (label, action) => {
        const b = doc.createElement("button"); b.type = "button"; b.textContent = label;
        b.addEventListener("click", action); return b;
    };
    panel.append(button("A – Original", () => { dry = true; refresh(); }),
        button("B – Spuren", () => { dry = false; refresh(); }));
    for (const name of Object.keys(stems)) {
        const row = doc.createElement("div");
        row.append(doc.createTextNode(name + " "));
        settings[name] = {gain: 1, mute: false, solo: false};
        for (const key of ["mute", "solo"]) {
            const label = doc.createElement("label"), input = doc.createElement("input");
            input.type = "checkbox";
            label.append(input, doc.createTextNode(key === "mute" ? " Stumm " : " Solo "));
            input.addEventListener("change", () => { settings[name][key] = input.checked; refresh(); });
            row.append(label);
        }
        const gain = doc.createElement("input");
        gain.type = "range"; gain.min = "0"; gain.max = "2"; gain.step = "0.01"; gain.value = "1";
        gain.setAttribute("aria-label", name + " Pegel");
        gain.addEventListener("change", () => { settings[name].gain = Number(gain.value); refresh(); });
        row.append(gain); panel.append(row);
    }
    panel.append(button("WAV exportieren", () => {
        try { onExport(wavExport(mixStems(original, stems, settings, dry), rate)); }
        catch (e) { status.textContent = e.message; }
    }));
    host.append(panel);
    return () => panel.remove();
}
