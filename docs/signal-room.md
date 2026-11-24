# Signal Room – Werkzeug integrieren

## Architektur

- `web/js/live_lab.js`: Discovery-Oberfläche, Auswahl, Suche, Status, Session-Host.
- `web/js/signal_tools.js`: einziges Register für Metadaten und Runtime-Fabriken.
- `web/js/signal_model.js`: reine Such-/Speicherlogik und exklusiver Session-Lifecycle.
- `web/js/signal_art.js`: interaktive SVG-Vorschauen, keine GPU-/Audio-Berechnung.
- `web/js/lab_pult.js`: aus der bisherigen Ansicht extrahiertes DJ-Pult.
- `web/signal_room.css`: isolierte visuelle Sprache; kein Framework, kein Build.
- Die bestehenden Module für Auto-DJ, Stem Studio, Spielwiese und Kick-Tausch behalten
  ihre eigentlichen Audio- und Server-Funktionen.

## Neues Tool hinzufügen

1. Neues Modul unter `web/js/` anlegen. Die Fabrik erzeugt den DOM-Knoten erst beim
   Öffnen einer Session, nicht beim Import. Rückgabe: `{ el, activate?, destroy }`.
2. Fabrik in `signal_tools.js` importieren und einen Registereintrag ergänzen.
3. Optional eigene SVG-Vorschau implementieren. Ohne Vorschau erscheint automatisch
   eine generische Signalstudie. Kategorien/Nummern/Filter werden aus dem Register
   berechnet; zusätzliche Änderungen an der Navigation oder CSS sind nicht nötig.

Beispiel (angenommen, das neue Modul exportiert `granularAnsicht`):

```js
import { granularAnsicht } from "./granular.js";

// Eintrag im Array werkzeuge
{
  id: "granular", // stabil, eindeutig, Kleinbuchstaben/Ziffern/Bindestriche
  titel: "Granular Playground",
  kurz: "Granular",
  gruppe: "Sound Design",
  slogan: "FRACTURE\nTHE SOUND.",
  sub: "Mikroskopische Fragmente. Neue Klangwelten.",
  kategorie: "TEXTURE / LIVE DSP",
  farbe: "#c7a4ff",
  text: "Zerlege Musik in kleine Fragmente und forme neue Texturen.",
  tags: ["GRAIN", "LIVE", "TEXTURE"],
  voraussetzung: "SOFORT · Audiodatei wählen",
  experimental: true, // optional, eigener Filter erscheint automatisch
  mount: ({ isProducing }) => granularAnsicht({ isProducing }),
}
```

Im JavaScript-Quelltext steht für einen Zeilenumbruch im Slogan die normale
Escape-Sequenz `\n`. Die Farbe muss ein sechsstelliger Hexwert sein; Titel,
Gruppe, Slogan, Kurzbeschreibung, Kategorie, Beschreibung und Voraussetzung
sind Pflichtfelder. `kurz`, `tags`, `experimental` und `preview` sind optional.

### Lifecycle-Vertrag

- `mount(context)` ist synchron und liefert einen neuen DOM-Knoten `el` sowie
  `destroy()`; langsame Arbeit startet innerhalb des Moduls asynchron.
- `activate()` ist optional und wird erst nach Einhängen in den sichtbaren
  Session-Host aufgerufen. Nicht automatisch Musik abspielen.
- `destroy()` muss Audio stoppen, AudioContexts/URLs/Timer/Animationen und
  globale Event-Listener freigeben sowie noch ausstehende Antworten entwerten.
  Ein serverseitiger Job darf nach dem Schließen weiterlaufen, sofern das bestehende
  Backend ihn entsprechend verwaltet. Keine unbeabsichtigte Wiedergabe nach Rückkehr.
- `context.isProducing()` gibt den zuletzt bekannten Claude-Status zurück.
  Teure Prozesse weiterhin nur nach expliziter Nutzeraktion starten.
- Ein Fehler bei `mount` oder `activate` wird angezeigt und die Auswahl kehrt
  zur Discovery zurück. Eine Fabrik muss bei einem eigenen Fehler während des
  Aufbaus selbst bereits angelegte Ressourcen freigeben.
- Die Spielwiese ist bewusst ein vorhandener gemeinsamer Singleton (auch in
  Aufträgen verwendet). Sie wird beim Schließen pausiert und ausgehängt;
  ausstehende Ladevorgänge dürfen nicht mehr automatisch spielen.

### Eigene Vorschau

```js
preview: {
  label: "Grain Density",
  links: "Sparse",
  rechts: "Dense",
  start: 50,
  zeichnen: (farbe, wert) => granularSvg(farbe, wert), // wert: 0..1, DOM-SVG
}
```

Vorschauen sind didaktische Signalstudien, keine echten Messwerte oder
Audiodemonstrationen. `zeichnen` soll deterministisch und günstig sein, ein SVG
als DOM-Element zurückgeben und weder Audio noch Animationen oder Netzwerkzugriffe
starten. Bestehende SVGs sind Beispiele; keine externen Assets nötig.

## Test / Merge

```powershell
py -3.11 -m unittest discover -s tests
node --test tests/logic.test.mjs
```

Manueller Browser-Check auf dem lokalen Dienst (Chrome/Edge, Light/Dark, Desktop/Mobil):
Suche mit Umlauten, Favoriten und Zuletzt-Filter, Vorschau-Regler aller fünf Tools,
Öffnen und Schließen aller Sessions, Fokus/Vollbild, Route-Wechsel bei aktivem
Audio oder laufender Analyse; keine Wiedergabe aus versteckten Werkzeugen.
Bei realen Songs zusätzlich Decks, Pads, Emblem, Auto-DJ-Übergänge, Kick-Ergebnis
und Stem-Mixer prüfen. GPU-Profile und Claude-Eco-Verhalten mit laufender Produktion
testen. Server-Jobs werden nicht künstlich als abgebrochen dargestellt.

Die geplante **Signal Chain** ist nicht Bestandteil dieser UI-Migration:
Eine verkettete Bearbeitung erfordert einen gemeinsamen Audio-Graphen, ein
Signal-/Stem-Format und Routing zwischen den heute unabhängigen Werkzeugen.
Keine inaktive oder irreführende Chain-Oberfläche wird eingebaut.
