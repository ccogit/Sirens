// WP17: reine Hilfen für Katalogsuche und expliziten Session-Export.
export function filterCatalog(entries, query, selected="") {
  const words=String(query).trim().toLocaleLowerCase("de-DE").split(/\s+/).filter(Boolean);
  return entries.filter(e=>e.path===selected || words.every(w=>
    (e.label+" "+e.path).toLocaleLowerCase("de-DE").includes(w)));
}

export function sessionExport(source, rate, preset, assets, timeline) {
  if(!/^[a-f0-9]{32}$/.test(source?.asset_id) || !/^[a-f0-9]{64}$/.test(source?.sha256))
    throw new Error("Quellen-Prüfsumme fehlt");
  return {version:1,sample_rate:rate,sources:[source],
    models:[{name:"mock",version:"mock-v1"}],presets:[{name:"A/B",version:"1"}],
    parameters:[{name:"gain",value:1},{name:"delay_frames",value:0},
      {name:"wet",value:preset.wet/100},{name:"bypass",value:Number(preset.bypass)}],
    seeds:[],timeline:timeline.slice(),assets:[...new Set(assets)]};
}

export const unavailableTools=Object.freeze([
  "DEMON", "RAVE", "AFTER", "Stable Audio", "SAM Audio", "Magenta",
  "DrumSep", "DSP Rack", "Drum Architect", "Stem Crossover", "Acid Transformer"
]);
