# Album- und Single-Ablage

Die Songbibliothek liest `Alben/<Album>` und `Singles/<Single>`. Ein Release-Ordner kann mehrere Songs oder Fassungen enthalten. Die Datei `.sirens-release.json` trägt den Anzeigenamen, den bisherigen Release-Slug und die musikalische Stilreferenz. Die Stilreferenz gilt für die enthaltenen Songs. Sirens kann auch den bisherigen Stilordneraufbau lesen.

`python -m sirens.migrate_music MUSIKORDNER DATENORDNER STILORDNER …` zeigt die geplante Zuordnung und die betroffenen Dateien. Mit `--anwenden` führt das Werkzeug den Umzug aus. `--musicmaker-container NAME` bezieht die Dateipfadfelder der lokalen Musicmaker-PostgreSQL-Instanz in Podman ein. Pfadzuordnung, Originalwerte und JSON-Sicherungen liegen in `_sirens/strukturmigration-…` unterhalb des Musikordners. Während des Umzugs sollten keine anderen Prozesse in die betroffenen Ordner oder Aufträge schreiben.

Der separate Musicmaker-Downloader erzeugt bislang weiterhin den bisherigen Stilordneraufbau. Sirens kann solche neu erzeugten Dateien lesen und zeigt sie in der gemeinsamen Ansicht an. Für neue Downloads direkt in die flache Ablage muss der Pfadgenerator in AutomaticMusicMaker angepasst werden.
