import {test} from "node:test";
import assert from "node:assert/strict";
import {gpuText, leaseText} from "../../web/js/realtime/gpu_panel.js";

test("Leases auch ohne GPU-Telemetrie erkennbar", () => {
  assert.match(gpuText({available:false}, [{owner:"claude",peak_bytes:8*1024**3,priority:"BACKGROUND"}]), /Claude \(8192 MiB, BACKGROUND\)/);
  assert.equal(leaseText([]), "Leases: keine");
  assert.equal(leaseText(null), "Leases: unbekannt");
});
