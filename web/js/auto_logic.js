// Auto-DJ: reine Auswahl-, Tag- und Beatgrid-Funktionen (ohne Browser-Abhängigkeiten).
const STILE = ["house","techno","trance","disco","funk","soul","jazz","hiphop",
  "drum","breakbeat","ambient","electro","pop","rock","metal","synth","dub","reggae","lofi"];

export function katalogSongs(daten) {
  const songs = new Map();
  for (const artist of daten.artists || []) for (const release of artist.releases || []) {
    for (const song of release.songs || []) for (const file of song.dateien || []) {
      const key = [artist.slug, release.slug, song.titel].join("\u0000");
      const text = [artist.slug, release.slug, song.titel, file.fassung || ""].join(" ");
      const genres = STILE.filter((w) => new RegExp("(^|[^a-z])" + w + "([^a-z]|$)", "i").test(text));
      const rating = Number(file.bewertung?.score || 0);
      const item = { pfad: file.pfad, titel: song.titel, artist: artist.slug,
        release: release.slug, rating, genres, text: artist.slug + " · " + song.titel };
      const old = songs.get(key);
      const quality = rating * 10 + (/master/i.test(file.fassung || "") ? 2 : 0);
      const oldQuality = old ? old.rating * 10 + (/master/i.test(old.pfad) ? 2 : 0) : -Infinity;
      if (quality > oldQuality) songs.set(key, item);
    }
  }
  return [...songs.values()].sort((a,b) => a.text.localeCompare(b.text, "de"));
}

export function tempoAngleichung(bpm, ziel) {
  if (!(bpm > 0) || !(ziel > 0)) return null;
  const normalized = [bpm / 2, bpm, bpm * 2].reduce((a,b) =>
    Math.abs(Math.log(b/ziel)) < Math.abs(Math.log(a/ziel)) ? b : a);
  const rate = ziel / normalized;
  return { rate, normalized, abweichung: Math.abs(Math.log(rate)),
    kompatibel: rate >= 0.84 && rate <= 1.19 };
}

export function naechsterTakt(zeit, info, normalized = info.bpm) {
  const takt = 240 / normalized; // vier logische Beats; 4/4 ist eine Annahme
  if (!Number.isFinite(takt) || takt <= 0) return 0;
  const first = Number(info.beat0) || 0;
  return first + Math.max(0, Math.ceil((zeit - first - 1e-6) / takt)) * takt;
}

export function uebergangsZeit(dauer, info, normalized, bars) {
  const takt = 240 / normalized;
  if (!(dauer > 0) || !(takt > 0)) return 0;
  const fenster = Math.max(1, bars) * takt;
  const limit = Math.max(0, dauer - fenster - 0.5);
  const first = Number(info.beat0) || 0;
  if (limit <= first) return Math.max(0, limit);
  return first + Math.floor((limit - first) / takt) * takt;
}

export function stimmung(info) {
  if (!info) return "Noch nicht analysiert";
  const bpm = Math.round(info.bpm);
  if (bpm < 95) return "entspannt";
  if (bpm < 118) return "groovy";
  if (bpm < 143) return "treibend";
  return "schnell";
}

export function waehleNaechsten(songs, history = [], ziel = null, zufall = Math.random) {
  if (!songs.length) return null;
  const letzte = new Set(history.slice(-Math.min(6, Math.max(0, songs.length - 1))));
  const pool = songs.filter((s) => !letzte.has(s.pfad));
  const liste = pool.length ? pool : songs;
  const vorher = songs.find((s) => s.pfad === history[history.length-1]);
  const gewichte = liste.map((s) => {
    const match = s.beat && ziel ? tempoAngleichung(s.beat.bpm, ziel) : null;
    const kompatibilitaet = match ? (match.kompatibel ? 3.5/(1+match.abweichung*15) : 0.25) : 1;
    const common = vorher?.genres?.filter((g) => s.genres?.includes(g)).length || 0;
    return Math.max(0.01, (1 + Math.max(-2, s.rating || 0) * 0.18 + common*0.4) * kompatibilitaet);
  });
  const sum = gewichte.reduce((a,b)=>a+b,0);
  let ticket = Math.max(0,Math.min(0.999999,Number(zufall()) || 0)) * sum;
  for (let i=0; i<liste.length; i++) { ticket -= gewichte[i]; if (ticket < 0) return liste[i]; }
  return liste[liste.length-1];
}


export function findeUebergang(von, nach, jetzt=0, taktzahl=8, erlaubteAbweichung=0.19) {
  if (!(von?.bpm>0) || !(nach?.bpm>0)) return null;
  const t=tempoAngleichung(nach.bpm,von.bpm);
  if (!t || Math.abs(1-t.rate)>erlaubteAbweichung) return null;
  const dauer=taktzahl*240/von.bpm;
  let beste=null;
  for (const a of von.cues_out||[]) for (const b of nach.cues_in||[]) {
    if (a.zeit<jetzt+Math.max(2,dauer*.7) ||
        a.zeit+dauer>=von.duration-0.25 ||
        b.zeit+dauer/t.rate>=nach.duration-0.5) continue;
    const energiematch=1-Math.abs(a.energie-b.energie);
    const ruhe=1-(a.energie+b.energie)/2;
    const score=.31*a.score+.32*b.score+.18*energiematch+.10*ruhe+
      .09*Math.max(0,1-t.abweichung*6);
    if(!beste||beste.score<score) beste={
      startA:a.zeit,startB:b.zeit,rateB:t.rate,normalB:t.normalized,
      bpm:von.bpm,bars:taktzahl,dauer,score,
      ausgang:a.grund,eingang:b.grund,energieA:a.energie,energieB:b.energie,
      confidence:Math.min(von.confidence||0,nach.confidence||0,
        von.phrase_confidence||0,nach.phrase_confidence||0)
    };
  }
  return beste;
}

export function klassifizierung(info) {
  if (!info) return ["Analyse offen"];
  const tags=[stimmung(info)];
  const seg=info.timeline||[];
  if (seg.some((s)=>/Break/i.test(s.phase))) tags.push("Breaks");
  if (seg.some((s)=>/Aufbau/i.test(s.phase))) tags.push("Build-ups");
  const energy=seg.reduce((sum,s)=>sum+s.energie,0)/Math.max(1,seg.length);
  tags.push(energy>=.68?"druckvoll":energy<.35?"zurückhaltend":"dynamisch");
  return tags;
}
