# K07 – lokaler Capability-Spike (Koordinator)

Kein Live-Aufruf durch Sirens oder CI. Claude/Producer Pal ist alleiniger Writer; SecondRoom liefert Material und Chain-Daten. WB-Capture nur nach exklusivem Handoff, frischem Guard/Lease-Receipt und Set-Bindung. Bei unklarem Status stoppen, nicht erneut senden.

1. Read-only: tatsächliche Producer-Pal-Toolliste und Version, Live-Version/Edition, Max for Live, vorhandene Instrumente/Racks/Packs/VSTs, SecondRoom-Status und WB-Capture/Export prüfen. Keine private Inventarliste oder Lizenzdaten in Git. Historischer Deep-House-Pilot und 65/65 Parameter-Readbacks sind keine aktuelle Messung.
2. Nur nach ausdrücklicher Freigabe und exklusiver Lease: neues isoliertes Test-Set (126 BPM, 4/4, 1.1.1), WAV ohne Warp, MIDI, Locator, Automation, verfügbare Devices, Speicherung/Medien sammeln und erneutes Öffnen überprüfen. Editieren und über normalen Exportdialog zurückgeben. Optional vorhandenen WB-Capture nach Handoff prüfen (gespeichertes gebundenes Set, Transport gestoppt, Loop aus, konstantes Tempo). Keine GUI-Automation, keine fremden Sets. Bei nicht nachgewiesenem unbeaufsichtigten Render Offline-Host verwenden.

Ergebnis als lokales JSON, schema_version=1, mit live_version, edition, max_for_live, producer_pal, secondroom, wb, live_writer, guard_status, capture, saved_set, open_set, render, reason, evidence (Operation, Ergebnis true/false/null, Version, Beleg). Unbekannt null. Kein ALS-/Render-Versprechen ohne Messung. Probe-Befehl zur lokalen Auswertung folgt im Adapter.
