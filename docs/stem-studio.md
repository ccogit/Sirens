## Stem Studio: Instrumente mit KI live mischen

Unter **✦ Live Lab → 🎚 KI Stem Studio** gibt es ein drittes Spiel:
Ein Song aus dem lokalen Sirens-Katalog wird einmalig von **Demucs** in einzelne
Instrumentenspuren (Stems) getrennt. Danach startet der Web-Audio-Mixer alle Spuren
**samplegenau auf demselben Zeitgeber**. Gesang, Schlagzeug, Bass und „Other“ können
solo, stumm oder mit eigenem Pegel gemischt werden. Das experimentelle Modell
`htdemucs_6s` ergänzt Gitarre und Klavier (die Trennqualität kann hier schwanken).

- `htdemucs`: vier Spuren – Gesang, Drums, Bass und Other.
- `htdemucs_6s`: sechs Spuren – zusätzlich Piano und Guitar.
- Beim ersten Aufruf lädt Demucs die Modellgewichte herunter; **Audiodateien
  werden nicht hochgeladen**. Alle separierten WAV-Dateien liegen unter
  `SIRENS_DATA_DIR/stems/<cache-schluessel>/`; die Quelldatei wird nicht verändert.
- Nachfolgende Aufrufe verwenden den Cache, solange Pfad, Größe und Änderungszeit
  der Quelldatei unverändert sind. Der Cache kann bei Bedarf manuell gelöscht werden.
- Die KI-Inferenz erfolgt **nur nach Klick auf „KI-Trennung starten“**, nie automatisch.
  Es läuft höchstens ein KI-Trennauftrag gleichzeitig (Zeitlimit 60 Minuten);
  ein Fehler wird sichtbar gemeldet und im jeweiligen `demucs.log` protokolliert.
- Beim Abspielen werden die WAV-Stems nacheinander vollständig in den Browser geladen
  und anschließend gemeinsam über Web Audio wiedergegeben. Für längere Stücke
  benötigen Browser und Demucs entsprechend Arbeitsspeicher.

### Warp Stage: 3D-Show für die RTX 5080

Im Stem Studio läuft zusätzlich eine **audioreaktive GPU-Bühne** mit drei Welten:
**Neon-Kathedrale**, **Hypercube** und **Quantum Nebula**. Ein prozeduraler
WebGL2-Raymarching-Shader erzeugt 3D-Tunnel, Fraktalstrukturen, leuchtende Portale,
Nebel und Lichteffekte; Bass, Mitten, Höhen und Beat-Impulse beeinflussen Geometrie,
Bewegung und Farben. Ohne laufenden Song steht eine klar beschriftete **Demo** bereit.

Drei GPU-Profile: **Eco** (15 FPS, 34 Schritte), **Live** (45 FPS, 76 Schritte),
**RTX Ultra** (60 FPS, 160 Schritte bis 3840 × 2160 Pixel). Im Ultra-Modus
lässt sich die **Renderdichte 50–150 %** einstellen; die Maximalauflösung
wird trotzdem begrenzt. Per Knopf geht die Bühne ins **Vollbild**. Die Bildrate
ist ein Sollwert, keine Garantie: sie hängt vom Browser, der Bildschirmauflösung,
dem Grafiktreiber und der tatsächlich gewählten GPU ab. Der Browser kann die
RTX nicht direkt durch die Web-Anwendung erzwungen zuweisen.

**Während Claude produziert, rendert die Bühne automatisch im Eco-Profil**.
In inaktiven Ansichten und Hintergrundtabs werden keine neuen Shader-Bilder
gezeichnet. Das schont Grafikleistung, VRAM und laufende Musikproduktionen.
Bei fehlendem WebGL2 gibt es eine reduzierte Canvas-2D-Animation.
Bei aktivierter Systemoption für reduzierte Bewegung gilt ebenfalls Eco.

### Instrumente austauschen (optional: Basic Pitch)

Im darunterliegenden **Instrument-Labor** kann ein Stem eine andere Klangfarbe
erhalten: etwa Bass als Synth Lead, Gesang als Crystal Bells oder Gitarre
als Cyber Strings. Die optionale KI **Spotify Basic Pitch** erkennt zunächst
Tonhöhen und Notenereignisse in der getrennten Audiospur. Beim Abspielen
synthetisiert Web Audio diese Noten auf derselben Song-Zeitachse in fünf
Klangfarben (Neon Lead, Crystal Bells, Electric Keys, Cyber Strings, Sub Bass).
Original-Stem und Ersatzinstrument lassen sich jederzeit umschalten.
Die Erkennung funktioniert besonders gut bei klaren, melodischen Einzelstimmen;
sie ersetzt keine professionelle Instrumenten- oder Transienten-Resynthese.

Für die optionale Notenerkennung eine eigene Python-Umgebung einrichten:

```powershell
py -3.11 -m venv .venv-pitch
.\.venv-pitch\Scripts\python.exe -m pip install --upgrade pip
.\.venv-pitch\Scripts\python.exe -m pip install basic-pitch
$env:SIRENS_STEMS_PITCH_PYTHON = (Resolve-Path ".\.venv-pitch\Scripts\python.exe").Path
```

Wie bei Demucs werden nur bei Klick auf **„KI-Noten erkennen“** Berechnungen
gestartet. Die Notendateien liegen im lokalen Stem-Cache. Basic Pitch
kann Modellgewichte aus dem Internet nachladen; Songs werden nicht zu
einem externen Anbieter hochgeladen.


### Installation mit RTX 5080 / 16 GB VRAM / 32 GB RAM (Windows, PowerShell)

Empfohlen ist eine **eigene Python-3.11-Umgebung**, damit die bestehende
Musikproduktion und ihr PyTorch nicht verändert werden:

```powershell
py -3.11 -m venv .venv-stems
.\.venv-stems\Scripts\python.exe -m pip install --upgrade pip
.\.venv-stems\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.\.venv-stems\Scripts\python.exe -m pip install demucs
.\.venv-stems\Scripts\python.exe -c "import torch; print(torch.__version__, torch.version.cuda); print(torch.cuda.is_available(), torch.cuda.get_device_capability() if torch.cuda.is_available() else None)"
```

Für die RTX 5080 (Blackwell, `sm_120`) ist ein passendes CUDA-fähiges
PyTorch-Build erforderlich (beispielsweise CUDA-12.8-Wheels oder neuer).
Bei `torch.cuda.is_available() == False` bzw. fehlender `sm_120`-Unterstützung
die PyTorch-Installation korrigieren oder den CPU-Modus verwenden.
Siehe die offizielle [PyTorch-Installationsseite](https://pytorch.org/get-started/locally/)
und [Demucs](https://github.com/facebookresearch/demucs).

Damit Sirens die gesonderte Umgebung benutzt, beim Start in derselben
PowerShell-Sitzung setzen (Pfad ggf. absolut angeben):

```powershell
$env:SIRENS_STEMS_PYTHON = (Resolve-Path ".\.venv-stems\Scripts\python.exe").Path
.\start.ps1
```

Im Stem Studio ist **CPU** als ressourcenschonende Voreinstellung gewählt.
Für CUDA die Auswahl **„RTX 5080 · CUDA“** treffen. Wenn eine Claude-Produktion
läuft, nimmt Sirens keine neue CUDA-Stem-Trennung an, um GPU-Speicherkonflikte
zu vermeiden. CPU-Trennung bleibt möglich. Eine bereits gestartete Trennung
lässt sich nicht unterbrechen; der eigentliche Browser-Mixer benötigt keine GPU-KI.

Hinweis: Demucs ist MIT-lizenziert. Die Nutzung und Weiterverwertung getrennter
Songs richtet sich weiterhin nach den Rechten an der jeweiligen Aufnahme.

