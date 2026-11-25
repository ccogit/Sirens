# Lizenzmatrix und Installations-Pins (WP20)

Quellen: jeweilige workers/*/requirements.lock, manifests, Gewichtslisten unter
benchmarks/spikes und G1-Berichte unter benchmarks/results/g1.
Keine Rechtsfreigabe; lokale Nutzung und Weitergabe sind getrennt zu prüfen.
Keine Gewichte oder fremden Wheels mit dem Release verteilen.

| Worker | Code / Pin | Gewichte / Einschränkung |
|---|---|---|
| DEMON | AGPL-3.0-or-later (MIT-Anteile), 96acc905204d54bfd3055084ca8e9df8a6d9a33f; Torch 2.9.1+cu128 | ACE-Step MIT, 19671f406d603126926c1b7e2adc169acbcade22; SHA-256 je Datei im G1-Bericht und Gewichtsmanifest |
| RAVE | CC BY-NC 4.0 (IIL); Torch 2.7.1+cu128 | CC BY-NC 4.0, 8471a1691f659ce52fcb2bb393afcc6f80187b17, SHA-256 im G1-Bericht; keine kommerzielle Nutzung |
| AFTER | CC BY-NC 4.0, 21298c907f469d6c7787c60dd38d46f98981b75c; Torch 2.7.1+cu128 | lokale Lizenz und SHA-256 erforderlich; gesperrt |
| Magenta | Apache-2.0, 694a545e4ba0b88bf1150137b129582166d3e07f; magenta-rt 2.0.3, JAX 0.10.1 | CC BY 4.0, 7803d987f43f7142cfc7d68ba3361c5f83023931; workers/magenta/weights.json |
| SAM Audio | SAM License, bb4c6999d2677c7402360e426afc01ddfad6dce0; weitere Code-Pins im Lock | SAM License, gated, Revision/Closure unbestätigt, keine Freigabe |
| RoFormer | MIT, MSST 1523206d12a521bdb20673726562524cf0f9635b; Torch 2.7.1+cu128 | MIT, ac9b0614ab3cd7f77219e18ba494dfd93956c348, SHA-256 87201f4d31afb5bc79993230fc49446918425574db48c01c405e44f365c7559e |
| DrumSep | Code MIT | Gewichtslizenz/Hash ungeklärt, gesperrt |
| Stable Audio 3 | MIT, 790793b89ddceea612be9ce42ff6830d18f6fa57; Torch 2.7.1+cu128 | Community-Lizenz, kommerziell eingeschränkt; 8bdfb53c6b0fbc62113cd571fd37373efe15fa14, Hashes im G1-Bericht |
| Mock | Sirens-Bestand | keine Fremdgewichte |

Direkte Pins sind keine vollständigen transitive Hash-Locks. SAM verlangt
externen vollständigen Hash-Lock und Snapshot-Receipt; andere Worker
haben Lücken (DEMON: fehlendes uv.lock; Magenta: CUDA-Transitive;
RAVE/AFTER, Separation und Stable Audio: unvollständige Paket-Hashes).
Keine Freigabe einer frischen reproduzierbaren Installation, bis diese
Lücken geschlossen und die tatsächlichen Wheels lokal geprüft sind.
Bei nichtkommerziellen Lizenzen keine kommerzielle Verwendung;
bei AGPL die Quellcodepflichten vor Verteilung prüfen.
