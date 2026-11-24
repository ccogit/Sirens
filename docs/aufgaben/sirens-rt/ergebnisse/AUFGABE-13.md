# AUFGABE-13 – WP13 Semantic Stem Extractor

Depends-on: WP03, WP21; ADR 0006 / WP25 (Dateijobs) und KETTE-43 (UI-/Routeneinbau).
G1 SAM Audio small: **nicht gemessen**, keine Freigabe. Offline-Kandidat.

## Umgesetzt

- Separater Worker unter workers/sam_audio/: IPC-v1 (probe/load/warmup/file_job/health/cancel/unload,
  Heartbeat mit Fortschritt), SAM-Backend nach dem WP21-Messpfad mit lokalem Snapshot,
  predict_spans=False, reranking_candidates=1, Seed 0. Kein Modellimport im Hauptprozess.
- Adapter verarbeitet PCM16-Stereo 44,1/48 kHz in 15-Sekunden-Blöcken; mono Modellziel auf beide
  Kanäle, Residual je Sample aus Original minus Ziel; beide PCM16-quantisiert und gemeinsam begrenzt.
  Exakt gleiche Framezahl, Rate und Rekonstruktion (0 LSB Abweichung). Original bleibt unverändert.
  Keine Behauptung zeitlicher Quellenausrichtung/Isolation ohne Hör- und Referenzprüfung.
- Serverseitig nutzbarer Cache mit SHA-256 der Quelle, Modellrevision, Prompt und Algorithmusrevision;
  validiert beide Dateien, Pfade, Shape und exakte PCM-Summe vor atomarer Publikation.
  Abbruch vor Publikation; Koordinator/WP25 muss Cancel/Publish im Job-Lock serialisieren und
  Prozessbaum/privates Staging bei Abbruch aufräumen.
- Gesperrtes schema-konformes Manifest (manifest.pending.json), Wheelhouse-Installer, Teil-Lock
  und Snapshot-Receipt-Prüfung; kein Download. Keine Registry-Anmeldung vor lokaler Installation/G1.
  UI-Platzhalter, Preview/Dry, Route, Job- und Cache-Einbau in docs/realtime/hooks/WP13.md.
- Messskript für fünf Beschreibungen in benchmarks/semantic/messen.py, JSON/Markdown nach
  benchmarks/result.py und lokaler Hörbericht; keine Audiodateien im Repo.

## Abnahme und Belege

1. CI [Run 45461751592](https://github.com/ccogit/Sirens/actions/runs/45461751592) auf
   0d2ae5cb3b04e846eb0a765ee6f254a935f55676: sieben neue Tests in
   tests/realtime/test_semantic_stem.py **ok** (Job-Lebenszyklus IPC, Abbruch, Cache/Revision/Prompt,
   PCM-Rekonstruktion einschließlich Extremwerten, Fake-SAM-Schnittstelle, Snapshot-Hash-Prüfung,
   gesperrte Capability). Keine GPU, kein Netz, keine echten Gewichte.
   Danach Registrierung auf Manifestvorlage umgestellt (siehe unten) und Capability-Test um
   simulierte lokale Freigabe mit/ohne Interpreter ergänzt. Diesen neuen Stand erneut in PR-CI prüfen.
   Kein produktiver Supervisor-Dateijob-Test möglich, solange WP25 nicht eingebaut ist.
2. Hardware-/Hörmessung **nicht gemessen**. Nach Audit, lokaler Installation, Netzisolation und
   Lizenzfreigabe durch den Koordinator, fünf passende lokale PCM16-Stereo-Tracks (Lead Vocals,
   Kick, Bass, Hi-Hat, Piano) in dieser Reihenfolge angeben:
   
       <Worker-Python> -m benchmarks.semantic.messen --receipt <lokales Receipt> --tracks <WAV1> <WAV2> <WAV3> <WAV4> <WAV5> --out <neuer externer Ordner>
       python -m benchmarks.result <externer Ordner>/result.json

   Je Fall target.wav/residual.wav; result.json/result.md und hoerbericht.md (Hörurteile offen).
   Kalt inklusive Laden, Warm vier weitere Fälle, Torch allocated Peak (keine Gesamt-GPU-Messung);
   qualitative Isolation, Leakage, Alignment, Übergänge und Browser-Preview separat beurteilen.
   Installationsanleitung und Receipt-Format: workers/sam_audio/README.md.
3. PR-CI ist maßgeblich. Run 45461751592: **174 Tests, 2 Fehler, 4 übersprungen**.
   Beide Fehler stammen aus Bestandsannahme einer leeren Registry ohne installierte Modelle:
   `realtime.test_rt_contracts.HTTP.test_switch_and_security` (Zeile 169) und
   `realtime.test_worker_supervisor.Workers.test_oom_and_rejection` (Zeile 67):
   AssertionError: capabilities mit gesperrtem sam_audio-Descriptor != [].
   Korrektur ausschließlich in eigenen Dateien: manifest.pending.json bleibt außerhalb
   Registry-Glob, UI-Hook zeigt bei fehlender Capability ausdrücklich „nicht installiert /
   nicht gemessen“. Keine Bestands-Tests geändert. Neue CI maßgeblich.
   Lokaler vollständiger Checkout nicht möglich: git ls-remote meldet
   "Could not resolve host: github.com"; daher keine lokalen Tests.
   Standardbefehl: python -m unittest discover -s tests -v (Python 3.11, Node 22).
   board.md und Register nicht eigenständig bearbeitet.

## Versionen, Grenzen, Abweichungen

- SAM Audio 0.1.0 / facebookresearch/sam-audio @ bb4c6999d2677c7402360e426afc01ddfad6dce0
  (SAM License), Git-Pins dacvae 414c20785fc3a28373073ea8ef7a1316eeeaca6e, ImageBind
  53680b02d7e37b19b124fa37bae4b6c98c38f5be, CLAP b85cb7ecac0af7d064cbf03ebd990e709e959fe7,
  perception_models e72b6810b1133e1c879f2cc965d276eb73803f1f laut WP21. Fremdcode-/Lizenzclosure
  noch nicht vollständig auditiert.
- SAM small checkpoint.pt ca. 5,1 GB, gated SAM License 19.11.2025. Gewichtrevision, exakte Größe
  und SHA-256 fehlen wegen verweigertem HF-Zugang (laut WP21/Koordinator). T5 base Safetensors:
  google-t5/t5-base @ fe6d9bf207cd3337512ca838a8b453f87a9178ef, Apache-2.0, SHA-256
  a90903540cc02cbeb7ff9f823f1a80eb778c7e22426a0e620b01c77a5ec8f5b4; weitere T5-Dateien offen.
- Torch/Torchaudio 2.7.1+cu128, Torchvision 0.22.1+cu128 vorgesehen wie CUDA-Wheel-Vorbild;
  SAM-Kompatibilität, torchcodec/FFmpeg, transitiver Hash-Lock und alle Git-Wheels offen.
  Kein erfundener vollständiger Lock. Installer verweigert nicht gepinnte/ungehashte Pakete,
  benötigt geprüftes lokales Wheelhouse, vollständigen externen Lock und Receipt.
- Ziel RTX 5080 16 GB Windows 11; Peak unbekannt, 15 s Segmente vorläufige Begrenzung, keine
  Streaming-Freigabe. Keine Überlappung/Fades; mono Zielschätzung und Begrenzung können
  Trennqualität verschlechtern. Nur PCM16-Stereo; andere Formate vorher lokal normalisieren.
- Offline-Flags und weights_only=True als Schutz, aber Drittcode benötigt Audit und
  ausgehende Netzsperre; lokale Betreiberbestätigung ist kein Sicherheits- oder Gate-Nachweis.
- Anpassungsbedarf: eingefrorene Capability-Controls sind ausschließlich numerisch;
  ADR 0006 verlangt Controls-Validierung. WP25/Koordinator muss textuellen Prompt explizit
  für diesen Dateijob zulassen. Kein Schema-/Supervisor-Umbau in dieser Kette.
  WP25 war bei letztem Integrationsabgleich nicht gemergt. Hook enthält angenommene IPC-Felder.
- Capability bleibt nicht registriert, bis eine geprüfte lokale manifest.json aus der
  Vorlage erstellt wird. KETTE-43 muss den nicht anklickbaren UI-Platzhalter auch bei
  fehlendem Descriptor anzeigen und vor Freigabe Receipt/Gate/Interpreter abgleichen.

## Übergabe

Fertig: Worker-/Adapterprototyp, exakte PCM-Rekonstruktion, Cache-Baustein, gesperrtes Manifest,
Installer mit fail-closed Lock/Receipt, Fake-Tests, Messskript, Hook. Alle Dateien gepusht.
Die sieben neuen Tests waren im ersten vollständigen CI-Lauf grün; erneuter Lauf nach
Manifestkorrektur erforderlich.

Offen: vollständige geprüfte Wheel-/Gewichtsclosure und Modellinstallation, WP25-Textprompt-
Validierung und end-to-end Job-/Cache-Anbindung, Freigabe/Preview über KETTE-43, Hardware-
und Hörprüfung. Kein echtes Modell installiert oder gestartet. Bis dahin deaktiviert lassen.

Nächster Schritt: aktuelle PR-CI prüfen; nach WP25-Merge integration/sirens-rt hineinmergen,
Dateijob-Felder/Publish/Cancel und Prompt-Validierung abstimmen. HF-Freigabe und Audit abwarten,
vollständigen Hash-Lock erstellen, G1 messen und erst dann passende lokale Manifestrevision
mit Peak freigeben. Hook einbauen; G3/Hörprüfung durchführen.

Fehlerausgabe: Run 45461751592 "FAILED (failures=2, skipped=4)", oben beide Assertions;
Manifestkorrektur danach gepusht. Git-Checkout lokal: "Could not resolve host: github.com".
Keine gemessenen G1-Werte. Kein Merge durch Bearbeiter.

Rollback: PR nicht mergen bzw. nur WP13-Dateien revertieren; lokale Aktivierungsdatei entfernen,
Worker beenden, optional lokalen Cache und venv entfernen. Keine Originaldateien überschreiben.
