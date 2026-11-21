// Zugriff auf den lokalen Dienst. Fehler kommen als {error, meldung, feld, status}.

async function ruf(methode, pfad, body) {
  let antwort;
  try {
    antwort = await fetch(pfad, {
      method: methode,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw { error: "offline", meldung: "Der Dienst antwortet nicht. Läuft er noch? (start.ps1)", feld: null, status: 0 };
  }
  let daten = {};
  try { daten = await antwort.json(); } catch { /* leere Antwort */ }
  if (!antwort.ok) throw { error: "fehler", meldung: "Das hat nicht geklappt.", feld: null, ...daten, status: antwort.status };
  return daten;
}

const auftrag = (id) => `/api/auftraege/${encodeURIComponent(id)}`;

export const api = {
  einstellungen: () => ruf("GET", "/api/einstellungen"),
  katalog: (q = "", minScore = null) =>
    ruf("GET", `/api/catalog?q=${encodeURIComponent(q)}${minScore == null ? "" : `&min_score=${minScore}`}`),
  katalogNeuLesen: () => ruf("POST", "/api/catalog/refresh", {}),
  liste: () => ruf("GET", "/api/auftraege"),
  lesen: (id) => ruf("GET", auftrag(id)),
  anlegen: (wunsch) => ruf("POST", "/api/auftraege", wunsch),
  folge: (vorgaengerId, vorlage) => ruf("POST", "/api/auftraege", { vorgaenger_id: vorgaengerId, vorlage }),
  aendern: (id, revision, wunsch) => ruf("PUT", auftrag(id), { ...wunsch, revision }),
  aktion: (id, name, revision, body = {}) => ruf("POST", `${auftrag(id)}/${name}`, { ...body, revision }),
  ablauf: (wunsch) => ruf("POST", "/api/ablauf", { umfang: wunsch.umfang, optionen: wunsch.optionen }),
  mastern: (pfad, schritte) => ruf("POST", "/api/mastern", { pfad, schritte }),
  explorer: (pfad) => ruf("POST", "/api/explorer", { pfad }),
  claude: () => ruf("GET", "/api/claude"),
  claudeStarten: () => ruf("POST", "/api/claude/start", {}),
  beat: (pfad) => ruf("GET", `/api/beat?pfad=${encodeURIComponent(pfad)}`),
  bildUrl: (pfad) => `/api/bild?pfad=${encodeURIComponent(pfad)}`,
  audioUrl: (pfad) => `/api/audio?pfad=${encodeURIComponent(pfad)}`,
  stemStatus: (pfad, modell) => ruf("GET", `/api/stems?pfad=${encodeURIComponent(pfad)}&modell=${encodeURIComponent(modell)}`),
  stemStart: (pfad, modell, device = "cpu") => ruf("POST", "/api/stems", { pfad, modell, device }),
  stemAudioUrl: (pfad, modell, stem) => `/api/stems/audio?pfad=${encodeURIComponent(pfad)}&modell=${encodeURIComponent(modell)}&stem=${encodeURIComponent(stem)}`,
  stemNoten: (pfad, modell, stem) => ruf("GET", `/api/stems/notes?pfad=${encodeURIComponent(pfad)}&modell=${encodeURIComponent(modell)}&stem=${encodeURIComponent(stem)}`),
  stemNotenStart: (pfad, modell, stem) => ruf("POST", "/api/stems/notes", { pfad, modell, stem }),
  kickStart: (ziel, spender) => ruf("POST", "/api/kicktausch", { ziel, spender }),
  kickStand: (id) => ruf("GET", `/api/kicktausch?id=${encodeURIComponent(id)}`),
  kickUrl: (id) => `/api/kicktausch/audio?id=${encodeURIComponent(id)}`,
};
