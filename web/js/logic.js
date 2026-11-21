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
