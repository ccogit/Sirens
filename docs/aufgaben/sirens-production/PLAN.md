# SIRENS / Local Music Production Engine

Stand: 24.11.2026 · Basis: main @ 94fe9001fec31d11bab77c0b434cf8a83a74b486 · Zielbranch: integration/sirens-production
Arbeitsauftrag für Codex und Claude; keine Aussage über bereits erzielte Audioqualität.
Zielrechner laut bestehenden Messberichten: Windows 11, RTX 5080 (16 GB VRAM), Python 3.11 im Hauptprozess, Node 22, lokaler Sirens-Dienst. Tatsächliche Hardware/Plugins zur Laufzeit prüfen.

## 1. Mission und Nicht-Ziele

Aus Stilprompt, Lyrics, Negativ-Tags und vorhandenen eigenen musikalischen Referenzen neue, eigenständige elektronische Songs erzeugen. Klang, Groove, Komposition und emotionale Wirkung sollen sich in wiederholbaren Hörvergleichen Suno annähern. GPT/Codex/Claude agieren als Produzenten; lokale Instrumente, Audio-Modelle und Mixer als ausführende Werkzeuge. Kein weiterer ausschließlich aus simplen Oszillatoren bestehender Songgenerator. Kein Echtzeit-Zwang: Offline-Rendering ist ausdrücklich erwünscht.

Nicht-Ziele für V1: DAW neu bauen, eigenes großes Musikmodell trainieren, alle Modelle/Genres gleichzeitig unterstützen, automatischer Cloud-Upload, Veröffentlichung, neue Datenbank, Änderungen am bestehenden Auftragsworkflow/Realtime-System. Keine erzwungene ACE-Step-Integration: bisherige Nutzererfahrung negativ. Kein blindes Vertrauen in KI-Bewertung oder LUFS als Ersatz für musikalische Qualität. Keine automatische Weiterverwendung von Referenz-Audio als Sample oder Trainingsmaterial. Keine API-Kosten ohne explizite Freigabe.

## 2. Bestand wiederverwenden

| Quelle | Nutzen / Einschränkung |
|---|---|
| sirens/config.py, Store, Katalog.scan/baum, bekannte_bewertungen | SIRENS_MUSIC_ROOT / DATA_DIR, lokale Songs, Scores −2..+2, Favoriten, Ästhetik-Achsen. Aggregation nimmt Maximalwert je Pfad; Rohbewertungen und Kommentare separat aus Store lesen, nicht durch Maximalwert ersetzen. Unbewertet ist unbekannt. |
| sirens/catalog.py _release_texte, docs/musikablage.md, songprofile.py | Release- und Songbeschreibungen, vorhandene Lyrics-Dateien, Alt-/Neuablage; Kurzprofil ist verkürzt und Tempo dort ggf. Textangabe, nicht Messwert. Volltexte und Prompt-Metadaten nur über tatsächlich vorhandene Quellen/Sidecars/Orders erfassen; fehlende Werte null. Kein fragiles Abgreifen einer externen DB. |
| auftrag.schema.json | Referenzen mit Übernahme-Gewichten, Bewertungen mit Kommentar und Favoritenmarkierung, provider suno/minimax. Keine Schemaänderung für V1. |
| sirens/beat.py, dramaturgie.py, realtime/music_analysis.py | Rhythmus, Tempo, Abschnitte, musikalische Analyse; Ergebnisse und Konfidenz prüfen, nicht als Ground Truth behandeln. |
| sirens/stems.py, stem_notes.py, realtime/stem_adapter.py, Stem Studio | Vorhandene Trennung, Notenextraktion, Cache; erst Mix-Analyse, dann selektiv Stems ausgewählter Referenzen. |
| sirens/analyse.py, klangvorlage.json, studio.py | Vorhandene Klangvorlagen aus Original/eMastered-Paaren, EBU-Lautheit, EQ, Kompression, Referenzangleichung. Nutzerbewertungen meinen ausdrücklich Musik, nicht Klang; Mastering unabhängig beurteilen. Studio schreibt Master neben Quelle: im Produktionszweig nur mit isolierter Run-Kopie / Adapter verwenden. |
| workers/stable_audio, benchmarks/results/g1/stable-audio-3.md | Small-Music auf RTX 5080 technisch gemessen, kalte 8-s-Generierung 21,2 s inkl. Laden, warme Messwerte schnell, Prompt-Treue/Hörqualität noch offen; Gewichte mit eingeschränkter kommerzieller Lizenz. Kein pauschaler Schluss über Medium oder Vollsongs. |
| sirens/realtime/gpu_manager.py, worker_supervisor.py | Vorhandene Leases, Worker-Isolation, Dateijobs. Bestehender file_job verlangt Quelldatei und festes Ausgabeformat; keinen Dummy-Quelltrack unterschieben. Generative Jobs mit geeignetem Wrapper und denselben Sicherheitsregeln. |
| docs/signal-room.md, web/js/signal_tools.js | Neue Session-Fabrik, Lifecycle, kein Autoplay, kein neues UI-Framework. |

Musikdateien, Bewertungen und Modelle liegen außerhalb von Git. Diese Planung hat Repo-Code/Dokumentation gelesen, nicht den lokalen Katalog oder die Musik gehört. Der erste lokale Lauf inventarisiert den Bestand selbst; keine erneute Frage nach Lieblingssongs. Existierende externe AutomaticMusicMaker-Projekte nur read-only über explizite lokale Adapter; keine Annahme, dass API-Zugänge oder Plugins bereits vorhanden sind.

## 3. Minimalarchitektur

Prompt/Lyrics + automatisch gewählte Referenzprofile
→ Produzent (Claude oder Codex; strukturierter Songplan)
→ Instrumente/Samples + optionale KI-Audiobausteine + gesprochene Stimme
→ Offline-Multitrack-Render → Mix/Master → Analyse/Blindvergleich
→ gezielte Plan-/Spuränderung → neuer Run → manuelle Übernahme in Sirens.

Ein Python-CLI-Einstieg und JSON-Dateien genügen. Keine neue Agentenplattform; keine dauerhafte Job-DB. Claude/Codex erhalten dieselben dokumentierten Befehle, anonymisierte Referenzprofile und Run-Berichte und schreiben einen Plan, nicht beliebigen ausführbaren Code als Songformat. Kein Modell im Hauptprozess importieren. Audio-/Modellbibliotheken in isolierten Worker-venvs. Agenten erzeugen keine ungeprüften Shell-Kommandos oder Python-Ausdrücke in JSON. Hardwarefremde Installationen und Modellgewichte nicht committen.

### Gemeinsamer Vertrag V1 (verbindlich ab Start)

Dateiformate siehe CONTRACT.md. Alle Teams können mit Mock-Fixtures arbeiten. A0 besitzt Vertrag und Querschnittsdateien. Ein Job ist ein lokales Verzeichnis unter DATA_DIR/production/runs/<uuid>/, mit brief.json, plan.json, assets.json, stems.json, mix.wav, master.wav, report.json, status.json und Logs. Relative Pfade, explizite Versionen/Seeds/Provenienz; kein Überschreiben abgeschlossener Runs. Cache und Referenzdaten lokal. WAV PCM24 48 kHz Stereo (Mono-Einzelspuren erlaubt, dokumentiert); Sample-Rate einmalig kontrolliert konvertieren, Start/Ende auf ganzzahliger Sample-Zeitachse. MIDI 960 PPQ, BPM konstant V1, 4/4. Tail max. 4 s im Plan; Stems gleich lang, Start bei Sample 0. Lautheit nicht durch erzwungene Überkompression erzielen.

### Werkzeuge (Kandidaten, keine ungeprüften Versprechen)

- Hauptpfad: professioneller Synth/Sampler, z.B. Surge XT über einen nachgewiesenen Offline-Host (DawDreamer falls kompatibel, andernfalls REAPER oder ein nachgewiesener CLI-Host). Native lokale Drum-/Multisample-Bibliothek. Ein Host, keine parallele Neuentwicklung mehrerer Hosts. Optional SFZ/SoundFont als pragmatischer Fallback, Qualität messen; synthetischer Stub nur für CI.
- Stable Audio Small für Texturen, Foley, Fills, kurze musikalische Passagen; pro Asset Prompt/Seed/Tempo/Key/Lizenz dokumentieren; nahtloses Schneiden, Taktlänge und Tonart verifizieren. Nicht als zuverlässigen Full-Song-Ersatz annehmen. Optional besseres lokales Modell nur bei überzeugendem kontrolliertem Hörtest und Hardware-/Lizenz-Gate.
- Spoken Word: ein lokal ausführbares neuronales TTS (z.B. Qwen3-TTS, Kandidat; 16 GB prüfen), keine Stimmkopie ohne Zustimmung. Keine Gesangspflicht V1; gesungene Songs als Folgephase. Keine Roboterstimme als Qualitätsfallback verkaufen.
- Mix: vorhandene Mastering-Engine/ffmpeg/Matchering nur soweit tatsächlich verfügbar; reproduzierbare Spurautomation, EQ, Sidechain, Kompression, Headroom, Limiter. Referenz-Mastering optional, kein Zwang zu Ziel-LUFS.
- Samples: lokale Bibliotheken und rechtmäßig nutzbare Aufnahmen. Asset-Manifest mit Quelle/Lizenz/Erlaubnis; bei unklarer Freigabe sperren für Veröffentlichung. Referenzstems nur zur Analyse. Keine Downloads im CI und keine nicht genehmigte Übertragung lokaler Musik/Prompts an Dritte. Agenten-Abonnements sind keine automatisch verfügbare API-Berechtigung.

## 4. Qualitätsstrategie

Zwei getrennte Achsen: (a) Musik/Interpretation (Groove, Komposition, emotionaler Ausdruck, Prompt-Treue, Übergänge), (b) Produktion (Sounddesign, Kick/Bass, Transparenz, Stereo, Stimme, Artefakte). Nutze +1/+2 als bevorzugte Musikbeispiele, −1/−2 als Kontrast, unbewertet separat. Gruppierung nach Songfamilie/Release/Version; kein Leakage zwischen Profilbildung und Holdout, keine eMastered-Duplikate als weitere Stimmen. Roh- und Masterfassungen nach Möglichkeit paaren. Referenzanalyse bevorzugt genre-/tempoähnlich; kein globaler Durchschnitt als Ziel für jeden Track.

Musikalische Merkmale: tatsächliches BPM/Downbeat und Varianz, Phrasenlängen, Groove/Onset-Microtiming, Kick/Bass-Rhythmus und spektrales Verhältnis, harmonische/tonale Verteilung mit Konfidenz, Dichte/Dramaturgie, Instrumentrollen, Sprachanteil. Audioqualität: Lautheit, true peak, Clip/NaN/Dropouts, Bandenergien, Mono-Sub/Korrelation, Transienten, Dynamik, Sprachverständlichkeit (optional ASR), Stems-Artefakte. Jede Messung mit Verfahren und Konfidenz; fehlende Features null, nie erfunden. Keine starren Genre-Lautheits- oder Stereovorgaben aus Favoriten ableiten. Rhythmische Timingvorgaben vs tatsächlich gemessen getrennt.

### Testkorpus und Freigaben

- B0: reproduzierbarer 30–45-s-Groove für Clear Head, Broken Heart, 126 BPM, gesprochen; Vergleich mit vorhandenen Original/Prototyp-Dateien sofern lokal auffindbar. Kein Audio in Git. Zwei weitere kontrastierende lokale +1/+2-Prompts mit echten Lyrics/Negativ-Tags, z.B. treibend vs atmosphärisch; automatisch auswählen, wenn geeignet. Alle Originale auf der Platte belassen. Wenn keine Prompt-Metadaten, klar als neuer Testbrief kennzeichnen.
- B1: pro Brief 3 Kandidaten (verschiedene Seeds/Arrangements), 30–60 s; stichprobenweise Lautheitsabgleich auf vergleichbares Niveau, Original und Kandidaten randomisiert, verdeckt und ohne Modellname. Erst die Abschnitte, dann Vollsong; keine blinde Batch-Massenproduktion.
- B2: mindestens drei vollständige 2–5-min-Songs, mit mindestens zwei unterschiedlichen musikalischen Charakteren; je zwei Kandidaten. Vergleiche mit jeweils passendem vorhandenen Suno-Referenzsong und, falls verfügbar, altem lokalen Prototyp. Zwei Wiederholungen zeitlich getrennt, insgesamt mindestens 12 blind bewertete A/B-Vergleiche gegen Suno (3 Briefs × 2 Kandidaten × 2 Durchgänge). Gleichlautheit innerhalb ca. 0,5 LU; Rohmaster ebenfalls verfügbar. Gewinner/Tie/Verlierer plus optional Kommentar, 1–5 je Qualitätsachse. Ein einzelner Nutzer ist personalisierte Evidenz, keine statistische allgemeine Suno-Parität.
- G0: Verträge/Mock-Tests, lokale Inventur und Referenzmanifest bereit; keine Audioqualität behauptet.
- G1: echter Groove mit Stimme und professionellen Instrumenten, 3 Seeds; keine harten Fehler; Nutzer bewertet mindestens eine Variante besser als alten Prototyp (falls nicht vorhanden: mindestens 3/5 Groove/Produktion). Bei Nichtbestehen Instrumente/Arrangement statt UI optimieren.
- G2: Vollsong-Pipeline, regenerierbare Einzelspur und Abschnitt, Stems und Provenienz, erfolgreiche Fehler-/Cancel-Tests. Metrische technische Mindestwerte: 48 kHz PCM24, keine NaNs/Clipping, true peak <= −1 dBTP im Master (mit Messverfahren), 126 BPM beim Testbrief innerhalb ±0,2 BPM sofern konstantes Raster vorgegeben, kein ungewollter Beatdrift, wortgetreue Spoken-Passagen, keine gesungene Melodie, keine abrupten unbeabsichtigten Schnitte; Hören entscheidet über wahrgenommene Qualität.
- G3: Fortschrittsziel: in mindestens 8/12 A/B-Vergleichen Gleichstand oder Präferenz für lokale Fassung, mediane Produktion und Musik je >=4/5, kein Brief durchgehend klar schlechter, keine technischen/licenzrechtlichen Blocker. Diese Schwelle ist ein vorgeschlagenes persönliches Freigabekriterium, keine Garantie. Bei Nichterreichen Defizite nach Achse priorisieren und je Run nur 1–2 gezielte Änderungen. Nie Ergebnisse erfinden oder Scores nachträglich umdefinieren. Kein automatisches Ersetzen von Suno.

Metrische Tests dienen als Filter, nicht Ranking allein. Der Agent soll aus Bericht und Referenzmerkmalen gezielt verbessern; Hörurteil des Nutzers bleibt entscheidend. Bestehende Bewertungen automatisch nutzen, neue kurze Hörurteile nur für neue Kandidaten. Negative Tags als überprüfbare Regeln, soweit möglich; subjektive Tags beim Hörtest. Keine automatischen Lernläufe auf persönlichen Audiodaten.

## 5. Parallelisierbarkeit: sieben Ketten, zwei Wellen

A0/Lead besitzt Vertrag, Fixtures, Runner, GPU-Adapter, Integration/PR-Merges. Die übrigen sechs Ketten haben disjunkte Dateien. K1–K6 können sofort parallel vom Plan-Commit starten, da CONTRACT.md die Dateischnittstellen festlegt; K6 arbeitet zunächst mit künstlichen WAVs. Integration erfolgt erst nach ihren jeweiligen Tests. Die Ketten sind bewusst groß genug für eigenständige Agenten, aber maximal zwei Phasen pro Kette. Siehe KETTEN.md und Einzelaufträge.

| Kette | Schwerpunkt | Implementierung parallel? | Laufzeitabhängigkeit |
|---|---|---|---|
| K0 | Runner/Verträge/Mock | sofort | keine |
| K1 | Referenzprofil/Katalog | sofort | lokaler Katalog, GPU optional |
| K2 | Produzent/Arrangement | sofort | nutzt Mock-Referenzprofil, später K1 |
| K3 | Instrumente/MIDI/Render | sofort | nutzt Mock-Plan, später K2 |
| K4 | Generative Assets/Spoken Word | sofort | nutzt Mock-Plan, später K2; GPU |
| K5 | Mix/Master | sofort | nutzt Mock-Stems, später K3/K4 |
| K6 | Benchmark/Hörvergleich/kleines UI-Modul | sofort | Mock-Runs, später echte Ergebnisse |

Kritischer Pfad reale Qualität: Referenzprofil → musikalischer Plan → professionelle Instrumente / Assets parallel → Mix → Hörtest → gezielte Revision. K0 baut parallel, danach K0 integriert und führt Pipeline aus. Keine Kette wartet auf fertig implementierte Nachbarn, solange sie den Vertrag einhält. Alle erhalten eigene Fixtures aus CONTRACT.md, schreiben nur eigene Dateien. Mit zwei gleichzeitig arbeitenden Agenten: Codex K0 → K3 → K5; Claude K1 → K2 → K4; K6 an zuerst freien Agenten (oder zusätzlicher Worktree ab Start). K0-Lead integriert/prüft nach jedem PR, nicht erst am Ende. Bei zusätzlichen Agentensitzungen jeweils eine Kette separat; max. 7 Code-Stränge, nicht 7 GPU-Prozesse. Mehr als ein Agent pro Kette nur mit Unteraufträgen in getrennten Dateien.

Ressourcen: CPU-Analyse, Code, Fixtures und Mix dürfen parallel laufen, begrenzte Prozesse und Speicherbudget. GPU-Inferenz standardmäßig eine schwere Lease, keine Umgehung des vorhandenen Managers. Der ManagedClaudeStarter hält eine exklusive Lease über die Sitzung; externe CLI-Agenten dürfen Modelljobs nicht nebenbei außerhalb der Lease starten. Plan/Code zuerst, Sitzung/Lease sauber beenden, dann ausdrücklich angestoßener lokaler Render; Ergebnis anschließend vom Agenten lesen. Falls automatischer Agenten-Zyklus später erforderlich: Lead gestaltet expliziten Handoff, keine Aufweichung von WP29. Keine gleichzeitig laufenden GPU-Benchmarks. Task-Parallelisierung ≠ GPU-Parallelisierung.

## 6. Einfache Bedienung und Iteration

V1 CLI, dann eine einzige Signal-Room-Kachel „Production Engine“: Brief aus bestehendem Auftrag oder Prompt/Text, automatisch vorgeschlagene Referenzen (optional ändern), „Groove testen“, „Vollsong rendern“, Status/Abbrechen, A/B-Player, Ergebnisbericht, neue Bewertung, „als neue Version übernehmen“. Kein neues Dashboard/DAW. Agent kann gezielt Planfelder, MIDI/Instrumentparameter oder einzelne Assets ändern, Runner rendert abhängige Schritte neu; Cache nach Input-Hash, Versions-/Seed-/Backend-Pin, kein globales Überschreiben. Auf Wunsch Referenzvergleich und Diagnosereport; Origin/Host/Safe-Path-Regeln des Dienstes beibehalten. Import/Export nur nach Klick/CLI-Bestätigung; V1 kann zunächst geprüfte Exportdatei liefern, keine automatische Auftragsmutation. Audio und Referenzprofile bleiben lokal.

## 7. Erster Durchstich: Clear Head, Broken Heart

126 BPM, 4/4, D-Moll als frei gewählte musikalische Ausgangsannahme (nicht angeblich aus Suno gemessen). Intro ~15 s / 8 Takte; Chorus gesprochen; Interlude 1 ~35 s / 18 Takte; Verse gesprochen; Interlude 2 ~45 s / 24 Takte; Bridge gesprochen; Interlude 3 ~45 s / 24 Takte; Chorus; Outro ~5 s / 3 Takte. Auf Taktgrenzen quantisieren, Worte nicht abschneiden. Bass wie rotierende Mechanik, tight mono sub, punchy kick, dezenter Motorik-Swing der oberen Elemente, Glockenboje als synkopierter Hook, Stereo-Beam einmal je Takt auf oberen Klanganteilen, Nebelhorn als Riser, Mandoline/Cello/Schiffsglocke und Möwen. Keine gesungene Melodie, kein EDM-Drop, keine Shanty, keine harte Höhen/Überkompression. Exakte vorhandene Lyrics aus lokalem Auftrag/Sidecar; falls fehlend, Testbrief in BRIEF-CLEAR-HEAD.md. Erst Kick/Bass/Glocken-Hook 16–24 Takte überzeugend machen, dann Vollsong. Drei bewusst unterschiedliche Varianten, kein bloßes Seed-Roulette. Keine Originalmelodie/Samples aus Suno übernehmen.

## 8. Abschluss/Definition of Done

PRs in Integrationsbranch, main bleibt unangetastet. Standard-CI: python -m unittest discover -s tests -v, node --test tests/logic.test.mjs plus neue isolierte Tests; keine Modelle im CI. Lokal: Installations-/Lizenzbericht, echte Messwerte (Renderzeit, VRAM, Ausfälle), reproduzierbare Runs und Hörbericht. Keine nicht getesteten Funktionen als bereit anzeigen. Erst nach G2/G3 Entscheidung über Integration in main. Nicht bestandene Gates und Abhängigkeiten dokumentieren. 
