import {test} from "node:test";
import assert from "node:assert/strict";
import {mixStems, wavExport} from "../../web/js/realtime/advanced_stems.js";
test("A/B, Solo, Mute und Gain", () => {
    const original = Float32Array.of(.5, .75);
    const stems = {vocals: Float32Array.of(.25, .25), instrumental: Float32Array.of(.25, .5)};
    assert.deepEqual(mixStems(original, stems), original);
    assert.deepEqual(mixStems(original, stems, {vocals:{mute:true}}, true), original);
    assert.deepEqual(mixStems(original, stems, {vocals:{solo:true,gain:2}}), Float32Array.of(.5,.5));
    assert.deepEqual(mixStems(original, stems, {vocals:{mute:true}}), stems.instrumental);
    assert.throws(() => mixStems(original, {vocals: Float32Array.of(1)}));
});
test("WAV Export und Clipping", () => {
    const bytes = wavExport(Float32Array.of(-1,1),44100);
    const view = new DataView(bytes);
    assert.equal(view.getUint32(24,true),44100);
    assert.equal(view.getInt16(44,true),-32768);
    assert.equal(view.getInt16(46,true),32767);
    assert.throws(() => wavExport(Float32Array.of(2,0),44100));
});
