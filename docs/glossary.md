# Glossary and notation

| Symbol or term | Meaning | Typical unit |
|---|---|---|
| FG | Floating gate containing a distributed nanocrystal ensemble | — |
| `P0`, `P1`, `P2` | Probability of zero, one, or two stored electrons | dimensionless |
| `m` | Normalized occupation, `(P1 + 2 P2)/2` | dimensionless |
| `QFG` | Integrated floating-gate sheet charge | C m⁻² |
| `VFB` | Flat-band voltage | V |
| `ΔVFB` | Charge-induced flat-band shift | V |
| `Veff` | Effective electrostatic voltage used by the compact model | V |
| `E(z)` | One-dimensional electric field | V m⁻¹ |
| `V(z)` | One-dimensional electrostatic potential | V |
| WKB | Wentzel–Kramers–Brillouin barrier approximation | — |
| `T` | Tunnelling transmission probability | dimensionless |
| `tprog` | Compact programming transmission/rate diagnostic | model-dependent |
| `terase` | Compact erase transmission/rate diagnostic | model-dependent |
| retention | Charge evolution after programming at a selected hold bias | s |
| golden reference | Deterministic numerical regression baseline | — |
| DTCO | Design–Technology Co-Optimization | — |

## Coordinate convention

The stack coordinate follows the ordered layer list. Layer positions and FG centroids are reported in nanometres, while physics engines convert to SI units internally.

## Charge convention

Stored electron charge produces a signed sheet charge through the occupancy model. Users should rely on exported signed values and the documented flat-band relation rather than applying an additional sign change during post-processing.
