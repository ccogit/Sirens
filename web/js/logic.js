// Reine Funktionen ohne DOM-Zugriff: Zusammenfassung, Zuordnung Status → Anzeige, Auswahl von Referenzen.

export const SATZ = "Bearbeite die Songaufträge";
export const BEZUG = { im_stil: "im Stil von", fortsetzung: "als Fortsetzung von", neufassung: "als Neufassung von" };
export const BEZUG_WAHL = [["im_stil", "im Stil von"], ["fortsetzung", "Fortsetzung"], ["neufassung", "Neufassung"]];
export const SCHRITTE = [["text", "Text"], ["paket", "Paket"], ["geprueft", "Geprüft"], ["gesendet", "Gesendet"], ["fertig", "Fertig"]];
export const SCORES = [[-2, "gar nicht"], [-1, "eher nicht"], [0, "geht so"], [1, "gut"], [2, "genau so"]];
export const VORLAGEN = [["mehr_davon", "Mehr davon"], ["nochmal_anders", "Nochmal anders"], ["fortsetzung", "Fortsetzung"]];

export function leererWunsch(artist = "") {
  return {
    weg: "referenz", umfang: "song", track_count: null, artist_slug: artist, ziel_release_slug: "", bezug: "im_stil",
    referenzen: [], wunsch: "", track_wuensche: [],
    optionen: { titelwunsch: "", sprache: "", gesang: "mit", no_gos: "", provider: "suno", planfreigabe: "aus", zweitgutachten: "an", tempo: "normal" },
  };
}

export function kurz(text, max = 70) {
  const t = (text || "").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1).trimEnd() + "…" : t;
}

export function scoreText(score) {
  return score > 0 ? `+${score}` : score < 0 ? `−${-score}` : "0";
}

// Ein Satz, der sich beim Ausfüllen mitändert.
export function zusammenfassung(w) {
  let satz = w.umfang === "album" ? (w.track_count ? `Album mit ${w.track_count} Songs` : "Album") : "Song";
  if (w.artist_slug) satz += ` für ${w.artist_slug}`;
  if (w.ziel_release_slug && w.umfang === "song") satz += ` im Album ${w.ziel_release_slug}`;
  const teile = [];
  if (w.weg === "referenz") {
    const n = (w.referenzen || []).length;
    teile.push(n ? `${BEZUG[w.bezug] || BEZUG.im_stil} ${n} ${n === 1 ? "Referenz" : "Referenzen"}` : "noch ohne Referenz");
    if (w.wunsch && w.wunsch.trim()) teile.push(kurz(w.wunsch));
  } else {
    teile.push(w.wunsch && w.wunsch.trim() ? `nach deiner Beschreibung: ${kurz(w.wunsch)}` : "Beschreibung fehlt noch");
  }
  if (w.optionen && w.optionen.gesang === "instrumental") teile.push("instrumental");
  if (w.optionen && w.optionen.tempo === "schnell") teile.push("Fast Mode");
  else if (w.optionen && w.optionen.planfreigabe === "an") teile.push("Plan vorher zeigen");
  return [satz, ...teile].join(", ");
}

// Was vor dem Abschicken noch fehlt: Liste {feld, meldung}.
export function fehlend(w) {
  const liste = [];
  if (!w.artist_slug || !w.artist_slug.trim()) liste.push({ feld: "artist_slug", meldung: "Bitte einen Künstler angeben." });
  if (w.weg === "referenz" && !(w.referenzen || []).length) liste.push({ feld: "referenzen", meldung: "Bitte mindestens einen Referenzsong wählen." });
  if (w.weg === "beschreibung" && !(w.wunsch || "").trim()) liste.push({ feld: "wunsch", meldung: "Bitte beschreiben, was entstehen soll." });
  return liste;
}

export function hatRichtungswort(text, wort) {
  return (text || "").split(",").some((t) => t.trim().toLowerCase() === wort.toLowerCase());
}

// Richtungswort an den Text anhängen; steht es schon als eigener Teil da, wieder entfernen.
export function richtungswortUmschalten(text, wort) {
  const teile = (text || "").split(",").map((t) => t.trim()).filter(Boolean);
  const ohne = teile.filter((t) => t.toLowerCase() !== wort.toLowerCase());
  return (ohne.length === teile.length ? [...teile, wort] : ohne).join(", ");
}

// Zuordnung Lage → Anzeige.
export function anzeige(lage) {
  if (lage.dran === "nutzer") return { text: "Du bist dran", klasse: "nutzer" };
  if (lage.dran === "claude") return { text: "Claude ist dran", klasse: "claude" };
  if (lage.dran === "laeuft") return { text: "Läuft", klasse: "laeuft" };
  return { text: "Erledigt", klasse: "niemand" };
}

// Aufträge für die Startansicht sortieren. Ein Auftrag kann bei „Du“ und bei „Claude“ stehen (offene Bewertungen).
export function gruppen(liste) {
  const g = { nutzer: [], claude: [], laeuft: [], erledigt: [] };
  for (const a of liste) {
    const dran = a.lage.dran;
    if (dran === "nutzer") g.nutzer.push(a);
    if (dran === "claude" || a.lage.claude_auch_dran) g.claude.push(a);
    if (dran === "laeuft") g.laeuft.push(a);
    if (dran === "niemand") g.erledigt.push(a);
  }
  const rang = { rueckfrage: 0, plan_wartet: 1, fertig: 2, entwurf: 3 };
  g.nutzer.sort((a, b) => (rang[a.status] ?? 9) - (rang[b.status] ?? 9));
  return g;
}

export function auftragTitel(a) {
  if (a.titel) return a.titel;
  const w = a.wunsch;
  if (w.weg === "referenz" && w.referenzen.length) {
    const erste = w.referenzen[0].titel;
    const art = w.umfang === "album" ? "Album" : "Song";
    return w.referenzen.length > 1 ? `${art} wie „${erste}“ und ${w.referenzen.length - 1} weitere` : `${art} wie „${erste}“`;
  }
  if (w.wunsch) return kurz(w.wunsch, 50);
  return w.umfang === "album" ? "Neues Album" : "Neuer Song";
}

// Künstler, Release, Titel, Version und Fassung aus dem relativen Pfad – wie der Dienst, ohne zu raten.
export function dateiInfo(pfad) {
  const teile = pfad.split("/");
  const name = teile[teile.length - 1].replace(/\.(mp3|wav)$/i, "");
  const m = name.match(/^(.+?) - Version (\d+)(.*)$/);
  return {
    artist: teile.length >= 3 ? teile[0] : "", release: teile.length >= 3 ? teile[1] : "",
    unterordner: teile.slice(2, -1).join("/"),
    titel: m ? m[1].trim() : name, version: m ? Number(m[2]) : null, fassung: m ? m[3].trim() : "",
  };
}

export function takeName(pfad) {
  const d = dateiInfo(pfad);
  const teile = [d.version != null ? `Version ${d.version}` : d.titel];
  if (d.fassung) teile.push(d.fassung);
  if (d.unterordner) teile.push(d.unterordner);
  return teile.join(" · ");
}

// Schritt eines Songs → Zustand jedes Punktes der Leiste Text → … → Fertig.
export function schrittLeiste(schritt) {
  const index = SCHRITTE.findIndex(([name]) => name === schritt);
  return SCHRITTE.map(([name, text], i) => ({
    name, text, zustand: schritt === "fehler" ? "offen" : i < index || schritt === "fertig" ? "erledigt" : i === index ? "aktiv" : "offen",
  }));
}

// Der eine Ablauf eines Auftrags: je Station der Zustand, ihre Arbeitsschritte und was dort geschah.
export function ablaufStationen(order) {
  const lage = order.lage;
  const phase = { 6: "mastering", 7: "cover", 8: "text", 9: "soundcloud" };
  const n = order.status === "nachlauf" ? order.nachlauf : null;
  return lage.stationen.map((name, i) => {
    const nr = i + 1;
    // Wird im Nachlauf ein früherer Schritt wieder geöffnet (z. B. das Cover nach dem Upload), bleiben spätere erledigte abgehakt.
    const zustand = (lage.ausgelassen || []).includes(nr) ? "ausgelassen"
      : order.status === "abgeschlossen" || nr < lage.station ? "erledigt" : nr === lage.station ? "aktiv"
        : n && phase[nr] && n[phase[nr]].stand === "fertig" ? "erledigt" : "offen";
    return { nr, name, zustand, schritte: (lage.detail || []).filter((s) => s.station === nr),
      eintraege: order.verlauf.filter((e, j) => (lage.verlauf_station || [])[j] === nr) };
  });
}

// Songs, die fertig gemacht werden oder als Favorit dafür bereitstehen – immer in der Reihenfolge des Albums,
// damit beim Wechseln nichts den Platz tauscht. Liefert [{pfad, nachlauf, aktiv}]; nachlauf ist null, solange nicht begonnen.
export function fertigmachListe(order) {
  const begonnen = new Map([order.nachlauf, ...(order.nachlauf_weitere || [])].filter(Boolean).map((n) => [n.favorit, n]));
  const favoriten = new Set(order.bewertungen.filter((b) => b.favorit).map((b) => b.pfad));
  return order.tracks_stand.flatMap((t) => t.dateien || []).filter((p) => begonnen.has(p) || favoriten.has(p))
    .map((pfad) => ({ pfad, nachlauf: begonnen.get(pfad) || null, aktiv: order.nachlauf?.favorit === pfad }));
}

// Je Song die bestbewertete, sonst die erste Datei.
export function besteDatei(song) {
  let beste = song.dateien[0];
  for (const d of song.dateien) {
    if (d.bewertung && (!beste.bewertung || d.bewertung.score > beste.bewertung.score)) beste = d;
  }
  return beste;
}

export function releaseReferenzen(release) {
  return release.songs.map((s) => besteDatei(s).pfad);
}

// Referenzen ergänzen, ohne Doppelte, höchstens 12. Liefert {referenzen, uebrig}.
export function referenzenErgaenzen(referenzen, pfade, max = 12) {
  const neu = [...referenzen];
  let uebrig = 0;
  for (const pfad of pfade) {
    if (neu.some((r) => r.pfad === pfad)) continue;
    if (neu.length >= max) { uebrig += 1; continue; }
    neu.push({ pfad, gewicht: "normal", uebernehmen: "" });
  }
  return { referenzen: neu, uebrig };
}

// Welche Takes ein Folgeauftrag als Referenz bekommt: Favoriten, sonst die bestbewerteten, sonst je Song der erste.
export function folgeReferenzen(order) {
  const alle = order.tracks_stand.flatMap((t) => t.dateien || []);
  const bew = new Map(order.bewertungen.filter((b) => alle.includes(b.pfad)).map((b) => [b.pfad, b]));
  const favoriten = alle.filter((p) => bew.get(p)?.favorit);
  if (favoriten.length) return favoriten;
  if (bew.size) {
    const beste = Math.max(...[...bew.values()].map((b) => b.score));
    return alle.filter((p) => bew.has(p) && bew.get(p).score === beste);
  }
  return order.tracks_stand.filter((t) => (t.dateien || []).length).map((t) => t.dateien[0]);
}

export function folgeHinweis(order) {
  const n = folgeReferenzen(order).length;
  const favorit = order.bewertungen.some((b) => b.favorit);
  if (!n) return "";
  if (favorit) return n === 1 ? "Dein Favorit wird die Referenz." : `Deine ${n} Favoriten werden die Referenzen.`;
  return order.bewertungen.length
    ? (n === 1 ? "Der bestbewertete Take wird die Referenz." : `Die ${n} bestbewerteten Takes werden die Referenzen.`)
    : "Noch nichts bewertet: Der erste Take je Song wird die Referenz.";
}

// Feldname einer Fehlermeldung auf das Formularfeld abbilden („referenzen[0].gewicht“ → „referenzen“).
export function fehlerFeld(feld) {
  return (feld || "").replace(/^optionen\./, "").replace(/[.[].*$/, "");
}

export function zeitText(iso, jetzt = new Date()) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const zwei = (n) => String(n).padStart(2, "0");
  const uhr = `${zwei(d.getHours())}:${zwei(d.getMinutes())}`;
  const gleich = d.toDateString() === jetzt.toDateString();
  return gleich ? `heute ${uhr}` : `${zwei(d.getDate())}.${zwei(d.getMonth() + 1)}. ${uhr}`;
}

// --- Spielwiese (Zeitvertreib, solange Claude arbeitet)

// Waagrechte Position auf der Spielfläche (0…1) → Grenzfrequenzen in Hz. Mitte offen, nach links dumpf, nach rechts dünn.
export function spielFilter(x) {
  const t = Math.min(1, Math.max(0, x));
  if (t < 0.45) return { tief: Math.round(200 * 100 ** (t / 0.45)), hoch: 20 };
  if (t > 0.55) return { tief: 20000, hoch: Math.round(20 * 200 ** ((t - 0.55) / 0.45)) };
  return { tief: 20000, hoch: 20 };
}

// Hüllkurve für die Übersicht über ein ganzes Stück: je Abschnitt der größte Ausschlag (jede 16. Probe genügt fürs Bild).
export function spitzen(daten, anzahl) {
  const schritt = daten.length / anzahl;
  return Array.from({ length: anzahl }, (_, i) => {
    let max = 0;
    for (let j = Math.floor(i * schritt), ende = Math.min(daten.length, Math.floor((i + 1) * schritt)); j < ende; j += 16) {
      const v = Math.abs(daten[j]);
      if (v > max) max = v;
    }
    return max;
  });
}

// Gut bewertete Songs aus dem Katalog als flache Liste, je Song die bestbewertete MP3 (leicht zu laden).
export function lieblingsDateien(katalog) {
  const liste = [];
  for (const artist of katalog.artists || []) {
    for (const release of artist.releases) {
      for (const song of release.songs) {
        const mp3 = song.dateien.filter((d) => /\.mp3$/i.test(d.pfad) && d.bewertung);
        if (!mp3.length) continue;
        const beste = besteDatei({ dateien: mp3 });
        liste.push({ pfad: beste.pfad, titel: song.titel, artist: artist.slug, achsen: beste.bewertung.achsen || null });
      }
    }
  }
  return liste;
}

// Die zwölf Achsen eines Songs (je 0–10) in fester Reihenfolge; sie bestimmen Form und Farbe des Emblems.
export const ACHSEN = [["energy", "Energie"], ["danceability", "Tanzbar"], ["experimentalism", "Experiment"], ["warmth", "Wärme"],
  ["darkness", "Dunkel"], ["psychedelia", "Psychedelik"], ["organicness", "Organisch"], ["electronicness", "Elektronisch"],
  ["melodicity", "Melodie"], ["groove", "Groove"], ["vocal_presence", "Stimme"], ["sampling_intensity", "Sampling"]];

// Profil eines Songs als Liste von zwölf Werten; was fehlt, kommt aus der Schätzung, sonst steht es auf Mitte.
export function achsenWerte(profil, schaetzung = {}) {
  return ACHSEN.map(([name]) => {
    const wert = profil?.[name] ?? schaetzung[name] ?? 5;
    return Math.min(10, Math.max(0, Number(wert) || 0));
  });
}

// Was sich aus dem Klang selbst lesen lässt: Tempo, Energie, Dunkelheit, Wärme, Tanzbarkeit. `daten`: ein Kanal, `rate`: Abtastrate.
export function klangProfil(daten, rate) {
  const laenge = Math.min(daten.length, rate * 60);
  const ab = Math.floor((daten.length - laenge) / 2);   // eine Minute aus der Mitte genügt
  const fenster = Math.max(1, Math.floor(rate / 100));  // Hüllkurve mit 100 Werten je Sekunde
  const huelle = new Float32Array(Math.floor(laenge / fenster));
  const alpha = Math.exp((-2 * Math.PI * 300) / rate);  // Tiefpass bei 300 Hz für den Anteil der Tiefen
  let summe = 0; let tief = 0; let tiefSumme = 0; let wechsel = 0; let vorher = 0;
  for (let i = 0; i < huelle.length * fenster; i += 1) {
    const x = daten[ab + i];
    summe += x * x;
    tief = alpha * tief + (1 - alpha) * x;
    tiefSumme += tief * tief;
    if ((x >= 0) !== (vorher >= 0)) wechsel += 1;
    vorher = x;
    huelle[Math.floor(i / fenster)] += x * x;
  }
  const n = Math.max(1, huelle.length * fenster);
  const grenzen = (wert) => Math.round(Math.min(10, Math.max(0, wert)) * 10) / 10;
  const anstieg = Array.from(huelle, (v, i) => Math.max(0, Math.sqrt(v) - Math.sqrt(huelle[i - 1] || 0)));
  const korrelation = (versatz) => { let s = 0; for (let i = versatz; i < anstieg.length; i += 1) s += anstieg[i] * anstieg[i - versatz]; return s; };
  let bestes = 0; let bpm = 120;
  for (let kandidat = 70; kandidat <= 180; kandidat += 1) {  // Schlagabstand, der sich am stärksten wiederholt
    const wert = korrelation(Math.round(6000 / kandidat));
    if (wert > bestes) { bestes = wert; bpm = kandidat; }
  }
  const ruhe = korrelation(0) || 1;
  const db = 10 * Math.log10(summe / n + 1e-12);
  return { bpm, energy: grenzen((db + 28) / 2), darkness: grenzen(10 - ((wechsel / n - 0.02) / 0.12) * 10),
    warmth: grenzen(((tiefSumme / (summe || 1)) - 0.2) / 0.06), danceability: grenzen((bestes / ruhe) * 14) };
}

// Farben des Emblems wie im Cover-Konzept: Farbton aus Wärme und Tongeschlecht (über Violett, nie über Grün),
// Sättigung aus Energie und Psychedelik, Helligkeit aus Dunkelheit. Werte 0–10; liefert [r, g, b] je 0…1.
export function emblemFarben(werte, dur = false) {
  const [energie, , , waerme, dunkel, psy] = werte.map((w) => w / 10);
  const ton = (220 + 160 * waerme + (dur ? 12 : -12)) / 360;
  const satt = Math.min(0.92, 0.38 + 0.45 * energie + 0.2 * psy);
  const hell = 0.66 - 0.26 * dunkel;
  const hsl = (h, s, l) => [0, 8, 4].map((nn) => {
    const k = (nn + (((h % 1) + 1) % 1) * 12) % 12;
    return l - s * Math.min(l, 1 - l) * Math.max(-1, Math.min(k - 3, 9 - k, 1));
  });
  return { haupt: hsl(ton, satt, hell), akzent: hsl(ton + (25 + 140 * psy) / 360, satt, hell + 0.06) };
}
