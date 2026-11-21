<p><img src="web/logo.svg" width="88" alt="Logo von Sirens"></p>

# Sirens

Eine kleine lokale Seite, die durch die Entstehung eines Songs oder Albums führt. Sie beantwortet
jederzeit zwei Fragen: **Wo steht mein Auftrag?** und **Wer ist dran – ich oder Claude?**

Die Seite erzeugt nichts selbst. Sie ruft MuAPI nicht auf und schreibt nicht in die
Pipeline-Datenbank. Die Erstellung macht Claude Code mit allen Qualitätstoren. Seite und Claude
tauschen sich über eine gemeinsame Auftragsablage aus.

Sirens liegt als Unterordner in dem Projekt, in dem Claude Code arbeitet. Dieses Projekt bringt mit, was Sirens
nur anstößt: den Skill `sirens` (Arbeitsablauf für Claude), die Skripte `scripts/soundcloud_auth.py` und
`scripts/soundcloud_upload.py` sowie die Mastering-Engine. Fehlt etwas davon, sagt die Seite an der Stelle
„nicht eingerichtet“; Aufträge, Anhören und Bewerten gehen trotzdem.

**Die Seite startet Claude Code selbst.** Sobald du etwas an Claude übergibst (abschicken, Rückfrage
beantworten, Plan entscheiden, abschließen), startet der Dienst im Hintergrund eine Claude-Code-Sitzung
mit dem Satz `Bearbeite die Songaufträge`. Es läuft höchstens eine Sitzung; kommt währenddessen etwas
dazu, folgt danach genau eine weitere. Die Seite zeigt, ob Claude gerade arbeitet, und bietet den Knopf
„Claude jetzt starten“, falls ein Start nicht geklappt hat. Den Satz kann man weiterhin selbst in
Claude Code eingeben.

## Start und Stopp

```powershell
cd sirens             # der Ordner dieses Repos
.\start.ps1          # startet im Hintergrund ohne Fenster und meldet die Adresse
.\start.ps1 -Open    # startet und öffnet die Seite im Browser
.\start.ps1 -Stop    # beendet den Dienst
```

Adresse: <http://127.0.0.1:8093/>. Im Vordergrund läuft der Dienst mit
`py -3.11 -m sirens serve` (Ende mit Strg+C). Er bindet ausschließlich an `127.0.0.1`.

## Konfiguration

| Umgebungsvariable | Standardwert | Bedeutung |
|---|---|---|
| `SOUNDCLOUD_…` (in `.env` in diesem Ordner) | – | Zugang für den Upload: `SOUNDCLOUD_CLIENT_ID` und `SOUNDCLOUD_CLIENT_SECRET` eintragen (Vorlage: `.env.example`), dann einmal im Projektordner `py -3.11 scripts/soundcloud_auth.py`; fehlt das Zugangstoken, sagt die Seite es im Schritt SoundCloud |
| `SIRENS_MUSIC_ROOT` | `E:\AMM\generated-music` | Musikordner; die Seite liest ihn und schreibt nur neue Master-Dateien des Studios |
| `SIRENS_FFMPEG` | leer | Pfad zu ffmpeg; leer = `ffmpeg` aus dem `PATH` |
| `SIRENS_DATA_DIR` | `E:\AMM\song-auftraege` | Auftragsablage, außerhalb des Repos |
| `SIRENS_PORT` | `8093` | Port |
| `SIRENS_CLAUDE` | `an` | `aus` schaltet den selbständigen Start von Claude Code ab |
| `SIRENS_CLAUDE_MODE` | `auto` | Berechtigungsmodus der gestarteten Sitzung (`--permission-mode`) |
| `SIRENS_CLAUDE_MODEL` | leer | Modell der gestarteten Sitzung (`--model`); leer = Standard |
| `SIRENS_CLAUDE_CMD` | leer | Ersetzt den Aufruf vollständig (JSON-Liste), z. B. für Tests |

Gestartet wird `claude -p --permission-mode <modus>` im Projektordner; der Satz geht über die
Standardeingabe hinein. `claude` muss im `PATH` des Dienstes liegen.

In der Ablage liegen:

- `claude-laeufe/<zeit>.log` – Ausgabe jeder vom Dienst gestarteten Claude-Sitzung.
- `auftraege/SA-JJJJMMTT-NNN.json` – eine Datei je Auftrag (Aufbau: `auftrag.schema.json`). Es wird nie gelöscht.
- `katalog-bewertungen.json` – Bewertungen aus `song_evaluations`, die Claude über die CLI ablegt (freiwillig).
- `richtungswoerter.json` – eigene Liste der anklickbaren Richtungswörter als JSON-Liste (freiwillig).

## Der Ablauf in zehn Stationen

| Nr. | Station | Was passiert | Wer |
|---|---|---|---|
| 1 | Auftrag | Weg wählen („Wie diese Songs“ oder „Ich beschreibe es“), Song oder Album, abschicken | du |
| 2 | Klären | Claude liest den Auftrag. Fehlt etwas Entscheidendes, kommt eine Rückfrage; du antwortest auf der Seite | Claude, bei Rückfrage du |
| 3 | Plan | Claude legt Konzept, Titel und je Song Idee und Stil fest. Mit „Plan vorher zeigen“ gibst du frei oder schreibst Änderungen | Claude, bei Planfreigabe du |
| 4 | Prüfen und Senden | Texte, Paket, Prüfungen, Versand. Du siehst je Song den Fortschritt | Claude |
| 5 | Anhören | Die Takes liegen vor. Anhören, bewerten, Favorit markieren. Claude übernimmt die Bewertungen; Folgeaufträge mit „Mehr davon“, „Nochmal anders“, „Fortsetzung“ | du, Claude |
| 6 | Mastering | Am Favoriten „Fertig machen“ wählen (je Song einzeln; mit „Zurück zum Anhören“ nimmst du weitere Songs dazu, oben wechselst du zwischen ihnen). Die Seite vermisst den Song und empfiehlt Einstellungen; Master im Studio rendern, angleichen, eigene Datei wählen oder ohne. Dazu jederzeit „Nach Ableton exportieren“ | du |
| 7 | Cover | Claude erstellt ein Cover. Du nimmst es an, verlangst ein neues (höchstens fünf Erzeugungen je Song) oder gehst ohne weiter. Auch später noch änderbar: neues Cover von Claude oder ein anderes Bild aus dem Songordner | Claude, du |
| 8 | Text | Claude legt Songbeschreibung mit Songtext und Tags als Datei beim Song ab | Claude |
| 9 | SoundCloud | Du entscheidest: hochladen (privat oder öffentlich) oder nicht; der Upload verlangt eine zweite Bestätigung. Claude lädt hoch und trägt den Link ein. Änderst du danach das Cover, ersetzt du es dort mit einem Klick. Promotion geht nur bei SoundCloud selbst | du, Claude |
| 10 | Abschluss | Auftrag abschließen | du |

Die Stationen 6 bis 9 gelten nur für den Favoriten und sind freiwillig; ein Auftrag lässt sich auch
direkt nach dem Anhören abschließen und später wieder aufnehmen.

### Fast Mode

Unter „Weitere Angaben und Fast Mode“ lässt sich ein Auftrag als Fast Mode abschicken. Dann entfallen
Rückfrage, Planfreigabe, Zusatzprüfung, Web-Stichprobe und bei Alben der Abgleich der Texte; der Song geht
deutlich schneller an den Anbieter, die Qualität kann leiden.

Das Formular zeigt unter „So läuft es ab“ alle Arbeitsschritte bis zum Versand und markiert, was der
Auftrag verkürzt oder auslässt. Dieselben Schritte stehen im Auftrag im „Ablauf“ unter ihrer Station, mit dem Stand
(erledigt, läuft gerade, offen, entfällt); Claude meldet die Schritte mit `detail`.

### Vorhandenen Song fertig machen

In der Kopfzeile führt „Song fertig machen“ zur Auswahl: ankreuzen, was passieren soll
(Mastern, Cover, Songbeschreibung, SoundCloud), dann den Take wählen. Es entsteht ein Auftrag, der direkt im
Nachlauf beginnt; nicht Angekreuztes gilt als ausgelassen, der Ableton-Export ist immer per Knopf möglich.
Claude wird nur gestartet, wenn Cover, Beschreibung, Ableton oder SoundCloud anstehen.

Der Knopf „Ordner“ neben einem Take oder Master zeigt die Datei im Windows-Explorer.

### Mastering-Station

- **Analyse und Empfehlung:** Beim Öffnen vermisst die Seite den Favoriten mit der vorhandenen
  `mastering_engine` (Lautheit, Spitze, Dynamik, Stereo, fünf Frequenzbänder).
  Verglichen wird mit der Klangvorlage `sirens/klangvorlage.json`: gemessene Paare aus Original und
  eMastered-Fassung desselben Songs. Bewertungen sind keine Klangvorlage; sie meinen die Musik, nicht den Klang.
  Die Voreinstellung „Empfehlung“ überträgt, was eMastered im Mittel verändert (Startpunkt der Regler),
  „Streaming −14“ dasselbe bei −14 LUFS. „Genre-Zielbild“, „Warm“, „Offen“ und „Laut“ sind Schätzwerte der Engine.
- **Studio:** Pult mit Equalizer (Sub 40 Hz, Bass 120 Hz, Tiefmitten 350 Hz, Präsenz 3,5 kHz, Luft 10 kHz),
  Kompressor in drei Bändern, Sättigung, Stereo-Breite, Lautheit (LUFS) und Pegeldecke. Gerendert wird mit der
  `mastering_engine` (Mid/Side-EQ, Multiband-Kompression, Sättigung und Limiter mit Oversampling); fehlt sie,
  vereinfacht mit ffmpeg. Vorhören im Browser mit Vergleich zum Original;
  „Master rendern“ schreibt `<Name> (Studio Master).wav` (24 Bit) neben den Favoriten und zeigt die gemessenen Werte.
- **Automatik (phaselimiter):** Open Source (MIT), mastert vollautomatisch und schreibt `<Name> (Auto Master).wav`.
  Erwartet die Windows-Fassung unter `E:\AMM\tools\phaselimiter\phaselimiter` (oder `SIRENS_PHASELIMITER`).
- **Angleichen (Matchering):** gleicht Klang und Lautheit an einen Referenzsong des Auftrags an und
  schreibt `<Name> (Angeglichen).wav`.
- **Eigene Master-Datei:** Eine anderswo gemasterte Datei im Songordner (oder in `mastered/`) erscheint zur
  Auswahl, wenn ihr Name den Songtitel und „Master“ enthält.

Einmalig einrichten: `py -3.11 -m pip install librosa soundfile imageio-ffmpeg pedalboard matchering`. Fehlt etwas davon,
bleibt das Studio ohne Analyse bzw. ohne Angleichen benutzbar.

Jeder Lauf schreibt eine neue Datei; vorhandene Dateien werden nie überschrieben.

Die Seite „Aufträge“ zeigt drei Spuren nebeneinander: was auf dich wartet, was auf Claude wartet (mit dem Stand der
Claude-Sitzung und dem Startknopf) und was läuft; Erledigtes steht eingeklappt darunter. Die Kopfzeile ist die einzige
Navigation (Aufträge, Neuer Auftrag, Song fertig machen). Im Auftrag steht links der nächste Schritt, rechts alles zum
Nachlesen. Es gibt genau einen „Ablauf“: die zehn Stationen untereinander, je Station aufklappbar mit ihren
Arbeitsschritten, den Notizen und Meldungen, die dort entstanden sind, und bei „Prüfen und Senden“ dem Stand je Song. Ein Entwurf wird beim Tippen automatisch gespeichert.

## Zugang für Claude

```powershell
cd sirens             # der Ordner dieses Repos
py -3.11 -m sirens todo            # alles, wofür Claude dran ist
py -3.11 -m sirens show SA-…       # ein Auftrag vollständig
py -3.11 -m sirens --help          # alle Befehle
```

Befehle: `todo`, `list`, `show`, `claim`, `note`, `ask`, `plan`, `track`, `sent`, `done`, `fail`,
`detail`, `phase`, `ratings`, `ratings-ack`, `catalog-ratings`. Ausgabe ist immer JSON; Fehler haben Exit-Code 1 und
`{"error": …}`. Die CLI arbeitet direkt auf der Ablage und braucht den laufenden Dienst nicht.
Den Arbeitsablauf beschreibt `.claude/skills/sirens/SKILL.md` im umgebenden Projekt.

## Aufbau

```
sirens/
  config.py     Pfade und Port
  contracts.py  Auftragsmodell, Prüfung des Wunsches, sichere Pfade im Musikordner
  workflow.py   Zustände, Übergänge, „wer ist dran“
  store.py      Ablage: eine JSON-Datei je Auftrag, atomar, mit Revision
  service.py    Aktionen des Nutzers (über die Seite)
  arbeit.py     Aktionen von Claude (über die CLI)
  ablauf.py     Arbeitsschritte bis zum Versand und was ein Auftrag davon verkürzt oder auslässt
  nachlauf.py   Nachlauf für den Favoriten: Entscheidungen des Nutzers, Meldungen von Claude
  studio.py     Mastering-Studio: Regler → ffmpeg-Filterkette, Angleichen mit Matchering
  analyse.py    Analyse und Empfehlung über die mastering_engine, übersetzt auf die Regler
  catalog.py    Referenzkatalog aus dem Musikordner, Bewertungsanzeige
  starter.py    Start von Claude Code im Hintergrund (höchstens eine Sitzung)
  server.py     HTTP-API und Auslieferung der Seite
  cli.py        Zugang für Claude
web/            index.html, app.css, js/ (ES-Module ohne Build; logic.js enthält nur reine Funktionen)
tests/          unittest, temporäre Verzeichnisse, nachgebauter Musikordner
```

Nur Python-Standardbibliothek, kein Build-Schritt. Das Studio ruft `ffmpeg` auf; Analyse (`mastering_engine`) und Matchering laufen in eigenen Prozessen und sind freiwillig.

## Tests

```powershell
py -3.11 -m unittest discover -s tests
```

Ist Node installiert, laufen dabei auch die Tests der Seitenlogik (`tests/logic.test.mjs`).

## Spielwiese: Zeitvertreib, solange Claude arbeitet

Wartet ein Auftrag nur noch auf Claude, zeigt die Auftragsseite eine Spielwiese. „Lieblingssong spielen“ holt einen gut
bewerteten Song (+1 oder +2) und spielt ihn; nach dem Stück folgt der nächste. Der Song lässt sich in Echtzeit verbiegen:
auf der Fläche ziehen (links dumpf, rechts dünn, oben Echo), dazu Stottern, Rückwärts, Bremse und Tempo.

Dieselbe Spielwiese steht auch im **Live Lab** (`#/lab`), dort neben dem DJ-Pult mit Beat-Pads; die Übersicht hat
dafür den Knopf „Spielen“.

Zwei Ansichten zum Umschalten:

- **Wellen:** drei Wellenbänder wie im Logo, die mit Bass, Mitten und Höhen gehen.
- **Emblem:** das gespiegelte Spektral-Emblem aus dem Cover-Konzept, gerechnet auf der Grafikkarte (WebGL 2). Die zwölf
  Achsen des Songs (Energie, Tanzbar, Experiment, Wärme, Dunkel, Psychedelik, Organisch, Elektronisch, Melodie, Groove,
  Stimme, Sampling) bestimmen Form und Farbe; am Achsenrad daneben lässt sich jede Achse verziehen, „Profil des Songs“
  stellt zurück. Die Achsen kommen aus den Katalogbewertungen (`achsen` je Datei, siehe `catalog-ratings`); fehlen sie,
  schätzt die Seite Energie, Dunkel, Wärme, Tanzbar und Tempo aus dem Klang, der Rest steht auf Mitte.

### Kick-Tausch

Drittes Spielzeug im Live Lab: ein gut bewerteter Song bekommt die Kick eines anderen. Sirens trennt dafür beide Songs
in Schlagzeug und Rest (je Song einmal, etwa eine Minute; danach aus dem Zwischenspeicher) und rechnet dann den Tausch.
Es wird nicht nur der Takt getroffen, sondern die Entwicklung des Zielsongs übernommen:

- Jeder Schlag sitzt dort, wo die bisherige Kick saß: Groove, Fills, Pausen und Breaks bleiben.
- Jeder Schlag ist so stark wie der ersetzte: leise Stellen bleiben leise, Steigerungen bleiben.
- Der Spender liefert bis zu drei Kick-Klänge (leise bis laut); die Wahl folgt der Stärke im Zielsong.
- Die fremde Kick wird auf den Grundton der bisherigen gestimmt (höchstens fünf Halbtöne), damit sie zum Bass passt.
- Der Bass bleibt unberührt, weil nur der Tiefton der Schlagzeugspur ersetzt wird.

Danach lassen sich „Mit neuer Kick“ und „Original“ an derselben Stelle im Wechsel hören. Ergebnisse und getrennte Spuren
liegen in der Ablage unter `spielzeug/` (je Song rund 30–50 MB), nie im Musikordner. Die Trennung macht ein fremdes
Werkzeug: `SIRENS_STEMS_CMD` in der `.env` (siehe `.env.example`) oder ein installiertes demucs; die Rechnung braucht
numpy, scipy und soundfile. Fehlt etwas davon, sagt das Spielzeug es.

## Songs weiterbearbeiten und Versionen aufräumen

Unter **Songs** stehen alle Songs in Bearbeitung und die in den letzten 30 Tagen aktualisierten Produktionen als
kompakte Zeilen. Ältere Songs lassen sich zusätzlich einblenden. **Bearbeiten** öffnet einen vorhandenen
Song erneut – auch nach dem Abschluss eines Auftrags. Der bestehende Auftrag und die Entscheidungen
bleiben erhalten.

- **Mastering:** Erneut rendern, Master wechseln oder ohne Master weiter. Nach dem Wechsel zwischen
  vorhandenen Fassungen fragt Sirens, ob die alte Datei **behalten** oder **archiviert** werden soll.
- **Cover und Text:** Neue Cover bzw. Beschreibungen anfordern. Entstehen neue Dateien mit anderem
  Pfad, folgt dieselbe Versionsfrage. Ein versehentliches Überschreiben durch externe Skripte kann die
  Oberfläche nicht verhindern; diese sollten daher neue Versionen unter neuem Dateinamen ablegen.
- **Takes:** Nicht mehr benötigte Takes können nach einer zusätzlichen Bestätigung aussortiert werden.
  Aktuelle Favoriten, Referenzen, Dateien in anderen Aufträgen und die bei SoundCloud hinterlegte
  Audiofassung sind geschützt. Werden sie noch benötigt, lehnt der Dienst das Archivieren ab.
- **Dateien:** Archivieren verschiebt die Datei aus dem aktiven Musikordner nach
  `SIRENS_DATA_DIR/versionen-archiv/<Auftrags-ID>/...`. Die Datei wird **nicht endgültig gelöscht**.
  Der Vorgang wird unter `archivierte_versionen` in der Auftrags-JSON dokumentiert. Behalten ist
  die sichere Standardentscheidung; ohne ausdrückliche Bestätigung wird nichts verschoben.
- **SoundCloud:** Nach Textänderungen lassen sich Beschreibung und Tags ausdrücklich **auf dem
  vorhandenen Track** aktualisieren. Cover lassen sich ebenfalls auf dem bestehenden Track ersetzen.
  Einen neuen Upload gibt es bei einer Aktualisierung nicht. Bei Fehlern bleibt der Sync-Hinweis offen.
  **Audiodateien** lassen sich nicht über die SoundCloud-API austauschen: Sirens verweist auf den
  bestehenden SoundCloud-Track und verlangt erst nach manuell bestätigtem Austausch eine
  Synchronmarkierung. Die Funktion „Replace file“ setzt einen passenden SoundCloud-Tarif voraus.

Über den Sonnen-/Mondknopf der Navigation wechselst du zwischen dem hellen Design und dem
navyfarbenen Dark Mode. Die Einstellung wird lokal im Browser gespeichert.

## Live Lab: interaktiver Zeitvertreib während Claude arbeitet

In der Hauptnavigation führt **✦ Live Lab** zu einem kleinen DJ- und Visual-Studio. Während
eine Produktion läuft, verlinken auch die Übersicht und die Auftragsansicht dorthin. Claude
arbeitet im Hintergrund unabhängig von der geöffneten Seite weiter.

- **Zwei Decks:** Gut bewertete Songs aus dem lokalen Katalog wählen (falls keine vorhanden
  sind: andere Katalogtitel) oder über den Dateidialog eigene Musikdateien laden.
  Crossfader und getrennte Geschwindigkeiten ermöglichen einfache Live-Mashups.
- **Effekte in Echtzeit:** Low-pass-Filter, Sättigung (Drive) und Echo. Die Originaldateien
  werden nicht verändert und nichts wird ins Internet geladen.
- **Spielbare Pads:** Kick, Snare, Hi-Hat, Bass und Akkord. Anklicken oder mit
  **A, S, D, F, G** spielen. Die Klänge werden direkt im Browser synthetisiert.
- **Audioreaktive Bilder:** Neon-Tunnel (WebGL2), Frequenzspektrum und Oszilloskop.
  Vor dem ersten Ton läuft eine ausdrücklich markierte Demo-Animation.
- **Rücksicht auf die Generierung:** WebGL2 bittet den Browser um den leistungsfähigen
  Grafikprozessor (z. B. RTX 5080). Die Grafik ist auf etwa 30 FPS, maximal 1600 Pixel
  Breite und 1,5-fache Pixelauflösung begrenzt. Wenn Claude tatsächlich arbeitet,
  wird auf etwa 15 FPS und 1000 Pixel Breite gedrosselt; im Hintergrundtab pausiert das Zeichnen.
  Die Wahl der tatsächlichen GPU trifft der Browser bzw. das Betriebssystem. Es wird
  **kein CUDA-Modell** gestartet, das der Musikgenerierung GPU-Speicher wegnehmen würde.

Für Audio ist nach dem Öffnen ein Klick auf Play oder ein Pad nötig (Autoplay-Schutz des
Browsers). Bei Verlassen des Live Lab werden die Decks gestoppt, der Audiokontext
geschlossen und temporäre Datei-URLs freigegeben. Andere Sirens-Funktionen bleiben
unverändert.

## Grenzen

- Die gestartete Sitzung läuft ohne Fenster und ohne Rückfragen im Chat; Fragen an dich kommen als
  Rückfrage auf der Seite. Scheitert eine Sitzung, startet der Dienst nicht von selbst neu.
- Nach einem Neustart des Dienstes wird nichts automatisch nachgeholt; dafür gibt es den Startknopf.
- Die Seite selbst erzeugt weder Cover noch Upload; das macht Claude nach deiner Entscheidung auf der Seite. Einzige Ausnahme: Das Cover eines schon hochgeladenen Songs ersetzt der Dienst selbst über `scripts/soundcloud_upload.py --replace-cover`.
- Promotion lässt sich über die Schnittstelle von SoundCloud nicht einschalten; das geht nur bei SoundCloud selbst.
- Das Vorhören im Studio ist eine Näherung; maßgeblich ist die gerenderte Datei.
- Texte und Stilbeschreibungen lassen sich auf der Seite nicht bearbeiten; Änderungswünsche gehen als Text an Claude.
- Schreibrechte sind getrennt: Die Seite schreibt nur Wunsch, Antworten und Bewertungen; Plan, Fortschritt,
  Ergebnis und „übernommen“ schreibt nur Claude über die CLI.
- Jede Änderung verlangt die aktuelle Revision; bei gleichzeitiger Änderung wird abgelehnt, nichts überschrieben.
