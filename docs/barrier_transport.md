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


## S1 implemented contracts and energy conventions

S1 implements five module-qualified exports in `ncmemsim.barrier_contracts`:
`BarrierProvenance`, `BarrierSegment`, `BarrierProfile`,
`BarrierEvaluationSpec` and `barrier_energy_eV_to_J`.
All contracts own canonical finite native JSON and return independent copies.
Unknown/missing/duplicate fields, nonfinite values, bool-as-number inputs and
changed semantic policy fields are rejected. No evaluator is called on construction,
restoration or reversal. The public package root and existing transport exports
are unchanged.

Each segment stores the electron potential energies U at its two ends in joules,
BEFORE subtracting the incident electron energy. A profile declares one global
incident energy E and a common energy reference for every endpoint. Negative U
or E is allowed relative to that arbitrary common zero. The S2 evaluator must
subtract E exactly once. Electrostatic potential (volts) is not an energy:
the electron contribution is -q times potential, with q the positive elementary
charge. No automatic voltage/optical-gap-to-barrier conversion is provided.

Segments are ordered along traversal; lengths are positive metres and mass is
a positive constant ratio to free-electron mass within each segment. At an
interface, adjacent endpoint energies may differ. These are two one-sided values,
not a finite-width interpolated ramp. Absolute coordinates are not reconstructed
from textual origin/direction declarations. `reversed()` swaps segment order,
segment endpoints, contact labels and traversal direction, retaining the same
axis declaration, energy zero and E. Reversal twice restores identical JSON.
It does not recalculate biased electrostatics, contact supply or current.

### Equation review and numerical policy

[Fitzpatrick's WKB notes, equations 338, 342 and 348](https://farside.ph.utexas.edu/teaching/qmech/lectures/node49.html)
support the smooth-potential, constant-mass forbidden-region exponent and its
applicability limits. The planned segment diagnostic uses

\[
B=\frac{2}{\hbar}\sum_i\int_0^{L_i}
\sqrt{2m_i\max(U_i(s)-E,0)}\,\mathrm{d}s,\qquad \log T=-B.
\]

Applying independent masses and summing across abrupt interfaces is a declared
compact action-only model choice, not a derivation of heterostructure transmission
matching from that reference. Reflections, coherent phases and resonances remain
excluded. At zero forbidden action the approximation yields T=1 without proving
unit physical transmission. Near turning points and abrupt interfaces, smooth-WKB
validity is limited; numerical action accuracy does not remove that model limitation.

The [equation and parameter review](barrier_parameters_review.json) admits no new
material coefficient. `assumed`, `reported` and `fitted` provenance labels are
caller declarations; none grants experimental admission. Source, evidence,
applicability and limitations are required even for synthetic assumptions.

The inert request binds an owned profile and explicit nonnegative exponent
tolerances (at least one positive). The reviewed S2 controls use dimensionless
B absolute tolerance 1e-12 and relative tolerance 1e-10 for B in [0, 10000].
Splitting/reversal controls use 1e-12 absolute and 5e-13 relative tolerance.
The reference-relative comparison is inclusive. These are prospective numerical
acceptance targets for analytic controls and independent refinement checks, not
observed errors or physical uncertainty bounds. S2 must demonstrate them before
acceptance; failures remain failures. Other inputs receive no implied accuracy guarantee.

The new policy retains finite B and log T if exp(-B) underflows to zero; nonfinite
derived action must fail rather than clip. S1 stores this policy but computes no
action, exponent, transmission or current. It does not change the published
direct-kernel exponential floor or the separate TAT conventions.

### Retained published-source boundary

`docs/v1_9_published_surface.json` is generated from the explicit v1.9 metadata
commit `26c7d62109ea3b9e0405538c3b3b2c843e1e453d`, not the evolving inventory.
The v1.9 gate pins its semantic digest and verifies all 146 original module
sources and public surfaces. Its original package-hash review is computed over
those original paths; additive S modules are reviewed separately in the current
inventory/tests. This does not regenerate or weaken the published v1.9 review.
Current package/citation version remains 1.9.0 while the next version is provisional.


## S2 isolated action evaluator

S2 adds `BarrierEvaluationResult` and `evaluate_barrier_profile` in
`ncmemsim.barrier_evaluation`. The input is an S1 `BarrierEvaluationSpec` or its
strict dictionary. Every result owns the original request, source hashes, actual
electron-mass/hbar constants, ordered per-segment diagnostics and aggregate status.
There is no simulator attachment, rate prefactor, current supply, interface
matching, new material coefficient or change to the published kernels.

### Stable analytic integration

The endpoint energies relative to E are formed once. Where both are positive,
the integral uses a rationalized difference of powers. With
a=sqrt(max(U-E)) and b=sqrt(min(U-E)), the mean square root is
(2/3) times (a*a+a*b+b*b)/(a+b); the implementation scales by a and uses b/a.
This avoids cancellation near a flat barrier. A sign crossing contributes only
the positive linear portion; an entirely nonpositive segment has zero action.
No finite-width ramp is inserted at a discontinuous interface.

Positive products and quotients are accumulated as binary mantissa/exponent
factors before the final rounding. This avoids intermediate overflow/underflow
when the final action is representable. Action (J s) and dimensionless exponent
are computed independently to avoid propagating an intermediate rounded action.
If either required positive diagnostic is outside representable range, the segment
fails explicitly. A tiny physical action is not silently turned into zero.

Each segment retains its two signed U-E endpoint values, domain, action, exponent,
log-transmission, transmission and failure. Transmission zero due to exp underflow
is a completed calculation with finite exponent/log retained. Zero forbidden
action, positive subnormal transmission and transmission rounded to one despite
positive action have distinct categories. No exponential floor is introduced.

Segments are independent diagnostic evaluations: all are attempted even if another
fails. Failed rows retain null derived values and a reason. The aggregate is
unavailable if any segment fails; no partial action is presented as a full result.
Aggregate overflow is also a failure even when individual segments completed.
The request tolerances are comparison declarations; they do not claim a measured
error estimate or change the evaluator formula.

### Result restoration and evidence

Result restoration reconstructs the isolated numeric action and checks diagnostics.
For portability across math libraries, the fixed budget is four ULP (units in the
last place) for finite action/exponent. Transmission is checked against exp at
the stored exponent with four ULP, because a one-ULP exponent change can cause a
much larger ULP change in a small transmission. Original accepted values and hashes
are retained. Log-transmission must equal minus the stored exponent; zero values,
attenuation categories, source identity, constants, policies, failures and counts
remain constrained. This narrow roundoff budget is independent of caller-declared
request tolerances. It is consistency checking, not authentication or device replay.

The [S2 kernel review](barrier_kernel_review.json) records source hashes, synthetic
control inputs and independent references. Tests use a 100-digit Decimal primitive
for rectangular, linear, near-flat and turning-point limits, plus independent
adaptive Gauss-Kronrod quadrature at two refinement levels. They apply the S1
acceptance thresholds without fitting them to observed failures. Same-energy
reversal/splitting smoke checks do not complete the broader S3 multilayer study.

Run `python examples/phase_s2_barrier_reference.py` for six explicit synthetic
cases: rectangle, linear, turning point, zero action, transmission underflow and
a retained numerical-range failure. Optional `--output` creates a new JSON file
and refuses to replace an existing file. These are isolated numerical controls,
not experimentally validated device predictions.
