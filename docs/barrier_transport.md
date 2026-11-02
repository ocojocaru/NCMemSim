# Explicit barrier profiles and transport diagnostics - Phase S

## S0 status and purpose

S0 is complete as a source audit and development contract, dated 2026-11-02.
No new transport kernel, material parameter or simulator integration is implemented.
The published baseline is v1.9.0, release commit
`af16961c832aaa3c8009450534f59cfbbc7893ea`, metadata closure
`26c7d62109ea3b9e0405538c3b3b2c843e1e453d`, version DOI
[10.5281/zenodo.23664613](https://doi.org/10.5281/zenodo.23664613).
Development branch: `dev/phase-s-barrier-transport`.
The next version remains provisional until compatibility and scope are reviewed.
S0 does not select v2.0 or change package/citation identity.

Phase S investigates explicit, ordered, piecewise-linear barrier-energy profiles
and per-segment effective masses for isolated compact WKB diagnostics. This is a
representation and numerical extension; it does not establish a more accurate
physical barrier or experimental validation merely by adding segments.

## Audited current behavior

The [source audit](barrier_transport_audit.json) records the exact source hashes
at the v1.9 metadata checkpoint. These are observations, not new equations.

| Existing path | Current behavior | Boundary for S |
|---|---|---|
| `ncmemsim/tunneling.py` | Samples a linear barrier relative to injection energy; clamps negative forbidden energy to zero; integrates with a trapezoidal rule; clips the exponential argument at -700 | Retain the published evaluator and defaults; do not silently replace it |
| `ncmemsim/kinetics.py` | Program/erase rates call the published WKB evaluator using configured NC barrier heights | Injection kinetics need a separate integration decision |
| `ncmemsim/transport/network.py` | Records intervening dielectric layer names but supplies one barrier and one mass per link | Layer names alone do not supply a multilayer energetic profile |
| `ncmemsim/transport/engine.py` | Uses the magnitude of the link field for transmission and signed potential difference for directional rates; substrate links are diagnostic | Never reinterpret signed fields or double-count substrate injection |
| `ncmemsim/transport/tat.py` | Already provides an analytic integral for the positive part of a linear barrier; reports exponent and allows transmission to underflow to zero | Reuse its limiting-case evidence, but preserve its trap-referenced semantics and public behavior |
| `ncmemsim/transport/barrier_corrections.py` | Opt-in compact Schottky peak lowering changes TAT interface heights | This is not a resolved spatial image potential; combining it with new profiles requires an explicit rule against double counting |
| `ncmemsim/materials/band_alignment/barriers.py` | Electron-affinity-rule estimate or explicitly supplied barrier | The method name `calibrated` does not supply experimental provenance by itself |

The direct evaluator defaults are injection energy 0.10 eV, oxide effective mass
0.15 times electron mass, 160 integration points and field coupling factor 0.80.
The transport configuration/network defaults include barrier 1.78 eV and mass
0.15 times electron mass. These are existing defaults, not newly approved
material values. No barrier coefficient is inferred from optical-gap shifts.

## Proposed first scope

The first isolated profile must declare ordered positive segment lengths,
finite endpoint energies, positive mass ratios, carrier species, energy reference,
traversal direction and parameter provenance/applicability. Canonical lengths
are metres and energies joules; electron-volts require named explicit conversion.
Endpoint energies must state whether injection energy has already been subtracted.
An energy discontinuity must be representable without a fictitious finite-width
interpolation across the interface. No default profile is inferred from layer names.

S1 must decide the precise public schema and equation conventions before code:
whether endpoint values represent potential energy or forbidden energy relative
to the incident carrier, how reversal changes coordinates, which interface
continuities are required, and how finite-action/underflow diagnostics are stored.
The initial scope is electron tunnelling; a hole model needs its own band-edge,
mass and rate contract. Signed electrostatic potential and electron potential
energy must not be conflated.

An isolated evaluator may sum segment actions only within the declared compact
WKB approximation. This does not include coherent interface matching, resonances,
well-state populations, transmission prefactors or current supply statistics.
Allowed regions contribute zero forbidden-region action, not a claim that every
physical above-barrier scattering problem has unit transmission.

## Staged plan and acceptance

| Stage | Deliverable | Required evidence before acceptance |
|---|---|---|
| S1 | Owned profile and evaluation contracts; primary-source equation/parameter review | Units, references, sign/reversal, interfaces, immutable ownership, strict serialization, applicability and numerical tolerances explicitly fixed |
| S2 | Isolated segment-action evaluator with exponent/log-transmission diagnostics | Independent rectangular/linear/turning-point references, near-flat stability, explicit underflow and invalid-input behavior; no simulator attachment |
| S3 | Controlled multilayer references | Single-segment comparison with both published kernels, segment-splitting invariance, heterogeneous mass, discontinuities, reversal and refinement studies |
| S4 | Conditional opt-in transport integration | Separate approved link/profile mapping; disabled behavior unchanged; conservation, mechanism separation and substrate diagnostic boundary verified; no automatic kinetics replacement |
| S5 | Sensitivity and controlled design studies | Thickness/height/mass/injection-energy effects separated; failed/unavailable points retained; numerical error distinguished from model uncertainty |
| S6 | Strict source-linked reports and bundles | Original profiles, actions, settings, provenance, limits and failures retained; static reconstruction/tamper rejection and portable archives |
| S7 | Compatibility review and release decision | Published APIs/defaults/archives retained, full regression, documentation and installed distributions, supported-Python CI, version rationale and exact-commit publication gates |

S1 requires primary references for the selected approximation and any proposed
material parameters. S0 uses repository source evidence only and admits no new
coefficient. A literature review may narrow or reject the proposed integration.
Tolerances must be justified against analytic limits and independent numerical
checks before implementation; they must not be selected after seeing failures.

S4 is a decision gate, not a promise that an arbitrary profile can be attached
to every existing transport link. If a consistent integration cannot be justified,
the isolated diagnostic scope remains useful and the reduced release scope must
be approved explicitly. No speedup or fidelity claim follows from S0.

## Compatibility and exclusions

Keep existing tunnelling, TAT, image-force, thermal, optical and retention defaults
unchanged. Old archives keep their original source identities, units and numerical
meaning. The direct evaluator's exponential floor and TAT underflow policy remain
distinct historical behaviors; a new diagnostic policy must be explicit.

Out of scope: self-consistent Schroedinger-Poisson/NEGF, full TCAD co-simulation,
resonant tunnelling, a spatial image-potential solver, automatic dielectric band
offsets, optical-to-transport barrier conversion, experimental fitting without
admitted data, new device families and silently extending the hole model.
Experimental P4B/P5B/P6B qualification remains deferred.

## Connection to published work

See [transport and retention](transport_retention.md),
[advanced transport](advanced_transport.md),
[performance/interoperability](performance_interoperability.md) and the
[roadmap](roadmap.md). Phase R timing evidence remains historical and scoped;
new profile diagnostics do not inherit its measured performance claims.
