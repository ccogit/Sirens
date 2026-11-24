// Offline-Mix vorbereiten; kein zweiter AudioContext.
export function mixStems(original, stems, settings = {}, dry = false) {
    const length = original.length;
    if (!(original instanceof Float32Array) || !length || !original.every(Number.isFinite))
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

// Offline-WAV ohne zusätzlichen AudioContext dekodieren. Nur PCM16/24 Stereo.
export function decodeStemWav(buffer) {
    if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < 44) throw new Error("Ungültige WAV-Datei");
    const v = new DataView(buffer), tag = p => String.fromCharCode(...new Uint8Array(buffer, p, 4));
    if (tag(0) !== "RIFF" || tag(8) !== "WAVE" || v.getUint32(4, true) + 8 > buffer.byteLength)
        throw new Error("Ungültiger WAV-Header");
    let fmt, data;
    for (let p = 12; p + 8 <= buffer.byteLength;) {
        const n = v.getUint32(p + 4, true), start = p + 8;
        if (start + n > buffer.byteLength) throw new Error("Unvollständiger WAV-Block");
        if (tag(p) === "fmt " && n >= 16) fmt = {type: v.getUint16(start, true),
            channels: v.getUint16(start + 2, true), rate: v.getUint32(start + 4, true),
            width: v.getUint16(start + 14, true), align: v.getUint16(start + 12, true)};
        if (tag(p) === "data") data = {start, n};
        p = start + n + (n % 2);
    }
    if (!fmt || !data || fmt.type !== 1 || fmt.channels !== 2 || fmt.rate !== 44100 ||
        ![16, 24].includes(fmt.width) || fmt.align !== fmt.width / 4 ||
        !data.n || data.n % fmt.align) throw new Error("Nur 44,1-kHz-Stereo-PCM16/24 unterstützt");
    const width = fmt.width / 8, samples = new Float32Array(data.n / width);
    for (let i = 0; i < samples.length; i++) {
        const p = data.start + i * width;
        samples[i] = width === 2 ? v.getInt16(p, true) / 32768 :
            ((v.getUint8(p) | v.getUint8(p + 1) << 8 | v.getUint8(p + 2) << 16) << 8 >> 8) / 8388608;
    }
    return {samples, rate: fmt.rate};
}

const validId = id => typeof id === "string" && /^[a-f0-9]{32}$/.test(id);
export function createSeparationApi(fetcher = globalThis.fetch) {
    async function json(method, path, body) {
        const response = await fetcher("/api/rt/v1/" + path, {method,
            headers: body === undefined ? {} : {"Content-Type": "application/json"},
            body: body === undefined ? undefined : JSON.stringify(body),
            signal: AbortSignal.timeout(20000)});
        const result = await response.json();
        if (!response.ok) throw new Error(result.meldung || "Dateijob abgelehnt");
        return result;
    }
    const jobPath = id => {
        if (!validId(id)) throw new Error("Ungültige Job-ID");
        return "jobs/" + id;
    };
    return {
        start: (pfad, model) => json("POST", "separation/jobs", {pfad, model}),
        job: id => json("GET", jobPath(id)),
        detail: id => json("GET", "separation/" + jobPath(id)),
        cancel: id => json("POST", jobPath(id) + "/cancel", {}),
        async exportMix(id, wav) {
            const response = await fetcher("/api/rt/v1/" + jobPath(id) + "/export", {
                method: "PUT", headers: {"Content-Type": "application/octet-stream"}, body: wav,
                signal: AbortSignal.timeout(60000)});
            const result = await response.json();
            if (!response.ok) throw new Error(result.meldung || "Export fehlgeschlagen");
            return result;
        },
        async audio(id) {
            if (!validId(id)) throw new Error("Ungültige Asset-ID");
            const r = await fetcher("/api/rt/v1/assets/" + id + "/audio",
                {signal: AbortSignal.timeout(60000)});
            if (!r.ok) throw new Error("Audiospur nicht verfügbar");
            return decodeStemWav(await r.arrayBuffer());
        }
    };
}

// Einbaupunkt für die Lab Shell; kein Start bei Mount, nur auf Klick.
// Die Shell liefert die aktuelle Katalogauswahl und optional ihren Player.
export function mountSeparationJobs(host, {selectedPath, onMix, onExport,
        api = createSeparationApi()} = {}) {
    const doc = host.ownerDocument, panel = doc.createElement("section");
    const heading = doc.createElement("h3"); heading.textContent = "Advanced Stem Studio · Offline";
    const model = doc.createElement("select");
    model.setAttribute("aria-label", "Offline-Trennmodell");
    for (const [value, label] of [["roformer", "RoFormer (falls installiert; sonst Demucs)"],
        ["htdemucs", "Demucs · CPU"]]) {
        const option = doc.createElement("option"); option.value = value; option.textContent = label;
        model.append(option);
    }
    const note = doc.createElement("p"); note.textContent = "44,1-kHz-Stereo-WAV; kein Streaming. DrumSep nicht freigegeben.";
    const status = doc.createElement("p"); status.setAttribute("role", "status");
    const preview = doc.createElement("audio"); preview.controls = true;
    const mixer = doc.createElement("div");
    let active = true, running = false, current = null, timer = null, unmount = null, url = null;
    const clearMix = () => {
        if (unmount) unmount();
        unmount = null; preview.pause(); preview.removeAttribute("src");
        if (url) URL.revokeObjectURL(url);
        url = null;
    };
    const button = (label, fn) => {
        const b = doc.createElement("button"); b.type = "button"; b.textContent = label;
        b.addEventListener("click", fn); return b;
    };
    const error = e => { if (active) status.textContent = e.message || "Dateijob fehlgeschlagen"; };
    const idle = () => { running = false; start.disabled = false; cancel.disabled = true; };
    const cancelJob = async () => {
        if (!current) return;
        const id = current;
        current = null; clearTimeout(timer);
        try { await api.cancel(id); if (active) status.textContent = "Abbruch angefordert"; }
        catch (e) { error(e); }
        finally { if (active) idle(); }
    };
    const show = async job => {
        if (!active || job.id !== current) return;
        status.textContent = job.state === "error" ? job.error?.meldung || "Trennung fehlgeschlagen" :
            job.state === "cancelled" ? "Abgebrochen" : "Offline-Job: " + Math.round((job.progress || 0) * 100) + " %";
        if (["queued", "running"].includes(job.state)) {
            timer = setTimeout(async () => {
                try {
                    const state = await api.job(job.id);
                    await show(state.state === "ready" ? await api.detail(job.id) : state);
                } catch (e) { error(e); await cancelJob(); }
            }, 500);
            return;
        }
        if (job.state !== "ready") { current = null; idle(); return; }
        try {
            const list = Object.entries(job.assets || {});
            const expected = job.model === "roformer" ? ["original", "vocals", "instrumental"] :
                job.model === "htdemucs" ? ["original", "vocals", "drums", "bass", "other"] : [];
            if (!expected.length || list.length !== expected.length ||
                !list.every(([name, id]) => expected.includes(name) && validId(id)))
                throw new Error("Ungültige Ergebnisliste");
            const data = {};
            for (const [name, id] of list) {
                const decoded = await api.audio(id);
                if (!active || job.id !== current) return;
                data[name] = decoded.samples;
            }
            const original = data.original; delete data.original;
            const play = samples => {
                if (onMix) return onMix(samples, 44100);
                const wav = wavExport(samples, 44100);
                preview.pause();
                if (url) URL.revokeObjectURL(url);
                url = URL.createObjectURL(new Blob([wav], {type: "audio/wav"}));
                preview.src = url;
            };
            unmount = mountAdvancedStems(mixer, {original, stems: data, rate: 44100,
                onMix: play, onExport: wav => {
                    const exported = onExport ? onExport(wav, job.id) : api.exportMix(job.id, wav);
                    Promise.resolve(exported).then(result => {
                        if (active && result?.file) status.textContent = "Gespeichert im RT-Ordner: " + result.file;
                    }).catch(error);
                }});
            play(original);
            status.textContent = (job.fallback_from ? "Rückfall auf Demucs · " : "") +
                (job.cache_hit ? "Cache-Treffer" : "Trennung fertig") + " · Offline";
        } catch (e) { error(e); }
        finally { if (job.id === current) { current = null; idle(); } }
    };
    const start = button("Offline trennen", async () => {
        if (!active || running) return;
        const path = selectedPath?.();
        if (!path || path === "fixture") { status.textContent = "Zuerst einen Song auswählen"; return; }
        clearMix(); running = true; start.disabled = true; status.textContent = "Job wird angelegt";
        try {
            const job = await api.start(path, model.value);
            if (!validId(job.id)) throw new Error("Ungültige Job-ID");
            if (!active) { await api.cancel(job.id); return; }
            current = job.id; cancel.disabled = false; await show(job);
        } catch (e) { error(e); if (active) idle(); }
    });
    const cancel = button("Abbrechen", cancelJob); cancel.disabled = true;
    panel.append(heading, note, model, start, cancel, status, preview, mixer); host.append(panel);
    return () => {
        active = false; clearTimeout(timer); clearMix(); panel.remove();
        if (current) void cancelJob();
    };
}
