import {test} from "node:test";
import assert from "node:assert/strict";
import {pack, unpack} from "../../web/js/realtime/pcm.js";

test("PCM v1: Seek-Bit und reservierte Bits", () => {
    const h = {protocol_version:1, stream_id:1, epoch:10, seq:0,
        start_frame:0n, nframes:256, channels:2, flags:1, sample_rate:48000};
    const payload = new Uint8Array(256*8);
    const block = pack(h, payload);
    assert.equal(block[27], 1);
    assert.equal(unpack(block).header.seek, true);
    assert.equal(unpack(pack({...h, flags:0}, payload)).header.seek, false);
    assert.throws(() => pack({...h, flags:2}, payload), RangeError);
    block[27] = 2;
    assert.throws(() => unpack(block), RangeError);
});
