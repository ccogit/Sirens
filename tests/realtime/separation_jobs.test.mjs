import {test} from "node:test";
import assert from "node:assert/strict";
import {createSeparationApi, decodeStemWav, wavExport} from "../../web/js/realtime/advanced_stems.js";

test("PCM16 und ungültige Header", () => {
    const wav = wavExport(Float32Array.of(-1, .5), 44100);
    assert.deepEqual(decodeStemWav(wav), {samples: Float32Array.of(-1, .5), rate: 44100});
    assert.throws(() => decodeStemWav(wavExport(Float32Array.of(0, 0), 48000)));
    assert.throws(() => decodeStemWav(wav.slice(0, -1)));
});

test("PCM24 mit Vorzeichen", () => {
    const wav = new ArrayBuffer(50);
    const view = new DataView(wav);
    const header = new Uint8Array(wavExport(Float32Array.of(0, 0), 44100));
    new Uint8Array(wav).set(header.slice(0, 44));
    view.setUint32(4, 42, true);
    view.setUint32(28, 44100 * 6, true);
    view.setUint16(32, 6, true);
    view.setUint16(34, 24, true);
    view.setUint32(40, 6, true);
    new Uint8Array(wav).set([0, 0, 128, 0, 0, 64], 44);
    assert.deepEqual(decodeStemWav(wav).samples, Float32Array.of(-1, .5));
});

test("Dateijob: keine Client-Ausgabepfade, bestehender Jobstatus und Abbruch", async () => {
    const calls = [], id = "a".repeat(32);
    const api = createSeparationApi(async (url, options) => {
        calls.push([url, options]);
        return {ok: true, json: async () => ({id})};
    });
    await api.start("Album/Song.wav", "roformer");
    await api.job(id);
    await api.cancel(id);
    await api.exportMix(id, wavExport(Float32Array.of(0, 0), 44100));
    assert.deepEqual(JSON.parse(calls[0][1].body), {pfad: "Album/Song.wav", model: "roformer"});
    assert.deepEqual(calls.map(([url]) => url), [
        "/api/rt/v1/separation/jobs", "/api/rt/v1/jobs/" + id,
        "/api/rt/v1/jobs/" + id + "/cancel", "/api/rt/v1/jobs/" + id + "/export"
    ]);
    assert.throws(() => api.job("../other"));
    assert.equal(calls.length, 4);
});
