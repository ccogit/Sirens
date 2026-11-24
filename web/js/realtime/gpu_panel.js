const numeric = value => typeof value==="number" && Number.isFinite(value) && value>=0;
const mib = value => numeric(value) ? Math.round(value/1048576)+" MiB" : "unbekannt";
const value = (v,unit="") => numeric(v) ? v+unit : "unbekannt";
export function leaseText(leases) {
  if (!Array.isArray(leases)) return "Leases: unbekannt";
  if (!leases.length) return "Leases: keine";
  return "Leases: "+leases.map(l=>`${({claude:"Claude",legacy_cuda:"Legacy CUDA",worker:"Worker"})[l?.owner] || "Unbekannt"} (${mib(l?.peak_bytes)}, ${l?.priority || "unbekannt"})`).join(" · ");
}
export function gpuText(gpu, leases) {
  if (!gpu?.available) return "Keine GPU-Telemetrie · VRAM: unbekannt · Warteschlange: "+value(gpu?.queue_depth)+(leases === undefined ? "" : " · "+leaseText(leases));
  return [gpu.device || "GPU", "VRAM: "+mib(gpu.vram_used_bytes)+" / "+mib(gpu.vram_total_bytes),
    "Auslastung: "+value(gpu.compute_percent,"%"),"Temperatur: "+value(gpu.temperature_c," °C"),
    "Warteschlange: "+value(gpu.queue_depth),"Deadline-Verfehlungen: "+value(gpu.deadline_misses),
    "Underruns: "+value(gpu.underruns), ...(leases === undefined ? [] : [leaseText(leases)])].join(" · ");
}
export function latencyText(cap) {
  if (!numeric(cap?.latency_frames) || !numeric(cap?.sample_rates?.[0]) || !cap.sample_rates[0]) return "Latenz: unbekannt";
  return "Deklarierte Latenz: "+(1000*cap.latency_frames/cap.sample_rates[0]).toFixed(1)+" ms (nicht gemessen)";
}
