import test from "node:test";
import assert from "node:assert/strict";
import { deriveState } from "../../web/js/realtime/capabilities.js";
import { capability } from "../../web/js/realtime/mock_api.js";

test("Status und Bedienbarkeit", () => {
  const caps = { protocol_version: 1, capabilities: [capability] };
  for (const [input, expected, enabled] of [
    [{ error: {status: 503}, capabilities: null }, "Schalter aus", false],
    [{ capabilities: {protocol_version:1, capabilities:[]}, gpu: {available:false} }, "Kein Modell installiert", false],
    [{ capabilities: caps, gpu: {available:false}, mock: true, songs: 1 }, "Testmodus", true],
    [{ capabilities: caps, gpu: {available:false}, mock: false }, "Keine GPU", false],
    [{ error: {status: 502} }, "API-Fehler", false],
    [{ capabilities: caps, mock:true, songs:0 }, "Leere Bibliothek", false],
    [{ capabilities: caps, mock:true, songs:1, error:{error:"busy_gpu"} }, "GPU beschäftigt", false],
  ]) {
    const state = deriveState(input);
    assert.match(state.text, new RegExp(expected));
    assert.equal(state.enabled, enabled);
  }
});
