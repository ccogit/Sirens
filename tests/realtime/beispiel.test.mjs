import assert from 'node:assert/strict';
import { test } from 'node:test';

test('WP00: verschachtelte Node-Tests werden gefunden', () => {
    const framesPerBeat = 48000 * 60 / 120;
    assert.equal(framesPerBeat, 24000);
});
