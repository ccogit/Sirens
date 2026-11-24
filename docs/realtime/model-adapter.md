# Adapter v1

probe liefert einen Capability-Descriptor ohne Modell-Download; load konfiguriert die konkrete Revision, warmup bereitet vor, process (bzw. generate) verarbeitet Audio, cancel stoppt kooperativ, unload gibt Ressourcen frei, health meldet Zustand. Supervisor erzwingt Timeout und terminiert ausschließlich den eigenen Prozessbaum. Keine Modellbibliothek im Hauptprozess.

Descriptor: id, mock, available, mode (streaming/lookahead/offline), sample_rates, channels, context_frames, hop_frames, latency_frames, controls (Name, min, max, default), vram_peak_bytes (gemessene Byte oder unknown), device, license, model_revision. Eine Capability beschreibt genau einen Modus; keine Freigabe ohne Gate. Mock ist offline, CPU, synthetischer Gain/Delay und kein KI-Modell. Nach load gilt deklarierte Delay-Latenz. process erwartet normalisierte interleavte Stereosamples; Delay bleibt über Blockgrenzen erhalten, load setzt ihn zurück. Keine Ausgabe nach cancel bis erneutem load. Unload gibt Puffer frei.

Worker-Manifeste und Lockfiles pro Modellfamilie; Code- und Gewichtslizenzen getrennt dokumentieren. IPC siehe ADR. Echte Adapter und GPU-Leases folgen WP03.
