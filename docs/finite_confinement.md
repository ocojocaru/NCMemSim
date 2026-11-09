# Finite-barrier spherical confinement - Phase T

## T0 status and baseline

T0 defines the source/literature audit and staged scope on 2026-11-06, after the
v1.10 documentation consolidation. Baseline: clean commit
`b9ede096aa6c1e6f1094ebbab375f5d32db65d6b`, with CI/Documentation/deploy passed.
Latest published stable remains v1.10.0, DOI
[10.5281/zenodo.23973765](https://doi.org/10.5281/zenodo.23973765).
The next release version is undecided. T0 adds no runtime API, eigenvalue solver,
material preset, simulator attachment, fitted coefficient or experimental claim.
The [machine-readable audit](finite_confinement_audit.json) pins the current sources.

## Existing implementation and separation rules

| Source | Audited behavior | Phase T boundary |
|---|---|---|
| materials/structural.py | Explicit Ge-only confinement domain, Gamma/L targets, scalar electron/hole masses and evidence; infinite-barrier/kinetic-only schema constants | Preserve O1 profile/archive meaning; introduce a distinct finite-well contract |
| materials/structural_confinement.py | Ground-state energies h^2/(8 m R^2), separate electron/hole terms, positive gap sum, strict static restoration | Retain O3 evaluator/defaults and high-barrier reference; do not cap its output to emulate a finite well |
| layers.py | NC diameter and FG thickness are separate geometry variables | R is half the NC diameter, not FG thickness or tunnel spacer length |
| materials/base.py / kinetics.py | NC transport mass, program/erase barriers and charging energy already have other owners | Do not reuse these as optical carrier masses, band offsets or exciton energies |
| structural_optical_context.py | Exact O-profile types; GeModel with zero Sn; diameter-derived radius; one thermal baseline plus explicit strain and kinetic shifts | Existing context does not accept a finite profile; any new integration needs an explicit new contract, one confinement owner per target |
| structural_reporting.py | Source-linked O contexts and original infinite-confinement diagnostics | Keep old archives; new finite sources need separate schemas/readers |
| materials/structural_strain.py / temperature_context.py | Independent strain and anchored temperature owners | A finite-well result must not infer a strain law, band offset or temperature dependence |

## First physical scope

Start with the isolated lowest s-like state (angular momentum l=0) of one carrier
in a spherical dot of radius R, embedded in one homogeneous host extending to
infinity. Use a one-band, isotropic, piecewise-constant effective mass and a finite
step potential. Electron and hole requests are separate. Both require explicit
inside/outside masses and an outside potential-energy cost with provenance.
This is a restricted effective-mass diagnostic, not a multiband Ge/GeSn solution.

The energy zero is the corresponding dot band edge: U=0 inside, U=V0 outside.
R>0, both masses>0 and V0>=0 are finite real declarations; bool inputs are invalid.
V0=0 is an unconfined control. A bound state requires strictly 0<E<V0 and an
exponentially decaying exterior envelope. E=V0 is not a normalized bound state.
For holes, V0 is the positive energy cost for the hole to enter the host, with
energy measured from its dot valence-band edge. It is not the signed electron
valence-band energy. No mass, offset or GeSn interpolation is supplied by T0.

Do not infer either carrier's offset from an optical gap shift, electron affinity
alone, or phi_barrier_prog/erase. Do not infer a host from an FG's neighboring
SiO2/HfO2 layers: the homogeneous spherical-host approximation needs its own
applicability declaration. Material qualification for a real embedded dot remains open.

## Equation and boundary-condition review

Use the stated divergence-form Hamiltonian

\[
H=-\frac{\hbar^2}{2}\nabla\!\cdot\!\left(\frac{1}{m(r)}\nabla\right)+U(r).
\]

For the radial envelope F(r), impose continuity of F and (1/m)dF/dr at R,
regularity at the origin and decay at infinity. With u=rF, the corresponding
derivative condition is continuity of (u'-u/R)/m, not u'/m alone.

For l=0, F_in is proportional to sin(kr)/r and F_out to exp[-kappa(r-R)]/r,
where k=sqrt(2 m_in E)/hbar and kappa=sqrt(2 m_out(V0-E))/hbar.
The following dimensionless form is a repository design derivation of those
conditions, consistent with equation (13) of the spherical reference below:

\[
\beta=m_{in}/m_{out},\quad \rho=R\sqrt{2m_{in}V_0}/\hbar,\quad
x=kR,\quad y=\kappa R=\sqrt{(\rho^2-x^2)/\beta},
\]
\[
x\cot x+\beta y+\beta-1=0,
\qquad 0<x<\min(\pi,\rho).
\]

T1 must fix units at the API boundary (SI energies internally, explicit eV
conversion, relative masses in m0) and distinguish an equation residual from
an energy error bound. T2 must bracket only the ground-state branch, avoid
cotangent poles and cancellation near x=0, and retain threshold uncertainty.
An arbitrary root, a clipped infinite-well energy or a residual alone is insufficient.

## Independent limits and prospective acceptance

For equal masses, the condition reduces to x cot x = -sqrt(rho^2-x^2). Its
lowest bound state exists only for rho>pi/2. At equality the exterior is not
square-integrable. For unequal masses, the threshold follows from
rho_c cot(rho_c)+beta-1=0, with 0<rho_c<pi, obtained by taking E upwards to V0.
These threshold equations are derived controls, not fitted material parameters.

For fixed R and positive masses, V0 tending to infinity must recover the O3
ground-state energy pi^2 hbar^2/(2 m_in R^2). For a bound finite well, E remains
below V0 and approaches the infinite-barrier energy from below. At equal masses,
increasing R or V0 must follow the selected model's ground-state trends. Do not
assert a universal monotonic rule when varying inside/outside masses together.

The future result must distinguish bound, no_bound_state, threshold_unresolved
and numerical_failure, with a retained reason. Missing bound states are a physical
outcome, not solver failure; failed/unresolved points must not be dropped. Normalize
the radial probability with the infinite exterior tail, and report inside/outside
probability, penetration depth, bracket/error diagnostics and applicability.
Near threshold, a large exterior probability is not a measured escape rate or lifetime.
Numerical-range failures must not be repaired by clipping E or inventing zero leakage.

Before implementation acceptance, T1 fixes tolerances and a synthetic control grid;
T2 validates equal/unequal masses, both sides of the threshold, normalization,
interface continuity/flux condition, unit conversions, large-barrier convergence
and representational extremes. Use independent high-precision roots and a separately
discretized radial eigenproblem with domain/grid refinement, not only a second call
to the production equation. An exterior cutoff belongs to the independent numerical
reference and needs convergence evidence; it is not the production host model.

## T3 controlled carrier and pair study

Run from the repository root to produce a JSON record of the controlled cases.

```shell
python examples/phase_t3_finite_confinement_reference.py --output outputs/t3_reference.json
```

The electron baseline uses a radius of 2 nm, a well depth of 0.8 eV and
inside/outside masses of 0.2 times the free electron mass. Four sweeps vary
radius, well depth, inside mass and outside mass individually. The
infinite-barrier comparison uses the same radius and inside mass, with
energy `h²/(8 m_in R²)` relative to the well bottom. The 10,000 eV
depth is an artificial limit check. The 0.05 eV control has no bound state.
Energies are exported in joules alongside the original requests, solver
status and, for bound states, penetration depth and interior/exterior probabilities.

The pair study uses the same radii (1, 2 and 4 nm) for both carriers.
The hole fixture uses a depth of 0.15 eV and inside/outside masses of 0.4
times the free electron mass. At 1 nm the electron has a bound state and
the hole has none, so the finite kinetic sum is unavailable. The 2 and
4 nm cases retain both carrier energies and their sum. All inputs are synthetic.
The pair sums describe independent-particle kinetic confinement only.
Optical transition energies and excitonic effects remain outside the study.

## Optical interpretation and integration gate

Only if both explicit electron and hole problems have accepted bound states may
a later independent-particle adapter form Delta E=E_e+E_h for the named optical
transition. This is a confinement contribution, not an excitonic transition energy.
No Coulomb attraction, dielectric self-energy, oscillator-strength correction,
selection-rule, broadening or absorption-amplitude law is added by that sum.
If either carrier lacks an accepted bound state, the pair correction is unavailable;
no silent substitution of the old infinite-well value is permitted.

A new opt-in context must replace the selected O3 kinetic contribution, not add
both finite and infinite confinement to the same target. Thermal/strain baselines
retain their current owners. Ge Gamma/L, hole-branch and radius applicability must
be explicit; no automatic GeSn, multivalley or multiband promotion is allowed.
Disabled behavior and every published O/S archive must retain its meaning.

## Primary references and access limits

- [BenDaniel and Duke, Phys. Rev. 152, 683 (1966)](https://doi.org/10.1103/PhysRev.152.683):
  original effective-mass heterointerface framework. Publisher metadata/abstract
  were accessible; the publisher full-text endpoint returned an authorization error.
  T0 does not claim to have inspected its full equations.
- [Chhabra, Ranjan and Singh, author preprint cond-mat/9902310](https://arxiv.org/abs/cond-mat/9902310),
  [full text](https://arxiv.org/pdf/cond-mat/9902310): section II, equations (1),
  (7)-(13), explicitly distinguish matching the full radial envelope from the
  reduced radial function. Full-text equations were read; the screenshot endpoint
  was unavailable. No numerical table or material coefficient is admitted here.
- [Moskalenko et al., author preprint cond-mat/0609193](https://arxiv.org/abs/cond-mat/0609193):
  abstract describes a multiband treatment of spherical Si/SiO2 electron/hole states.
  This is a scope warning, not Ge parameter evidence; its full equations were not reviewed.

The O3 [structural parameter review](structural_parameters_review.json) and its
Brus framework reference remain unchanged. No reference above qualifies masses,
band offsets or optical spectra for the user's Ge/GeSn device.

## T1-T7 sequence

| Stage | Deliverable | Acceptance boundary |
|---|---|---|
| T1 | Separate owned finite-well requests/provenance and numerical policy | Carrier/edge conventions, radius, two masses, V0, state labels, applicability and units fixed; material presets remain independently reviewable |
| T2 | Isolated l=0 ground-state evaluator | Threshold classification, stable bracketing, exterior normalization and independent reference/refinement checks; no simulator attachment |
| T3 | Controlled single-carrier and electron/hole-pair studies | Finite/infinite comparison, separate radius/depth/mass effects, retained unavailable pair corrections and no exciton claim |
| T4 | Conditional explicit optical-context integration | One confinement owner per transition, no double counting, source-bound rebuild after radius/parameter changes and disabled parity |
| T5 | Controlled optical/spectral studies | Numerical refinement separated from physical parameter sensitivity; failures/unbound outcomes included; no fabricated device calibration |
| T6 | Strict finite-confinement reports/bundles | Original profiles, bound-state classification, tails, references, limits and failures preserved; static reconstruction/tamper controls |
| T7 | Compatibility and release decision | Published sources/defaults/archives retained, full matrix/docs/distributions and exact-commit release gates; version justified from actual scope |

T4 is conditional, not guaranteed by solving an isolated spherical problem.
T0 does not select a version or approve material coefficients. Excitonic Coulomb
terms, dielectric polarization, nonspherical/multishell dots, higher angular/excited
states, anisotropic/multiband masses, nonparabolicity, field/strain-dependent offsets,
transport escape rates and self-consistent Poisson/Schrodinger coupling are separate
research scopes. Experimental P4B/P5B/P6B qualification remains deferred.

## T1 request and prospective numerical policy

`FiniteConfinementRequest` and `confinement_depth_eV_to_J` are available from
`ncmemsim.materials.finite_confinement_contracts` on the development branch.
Each immutable request declares one carrier, dot and host labels, radius in metres,
two masses relative to the free electron mass, depth in joules and a temperature
in kelvin. Temperature records the point of applicability for the supplied inputs.
Declare radius, each mass and depth with individual `StructuralEvidence` records.
Report their uncertainties in m, m0 and J respectively. The applicability record
describes the whole request and points to the conditions under which its inputs apply.
Material labels are caller declarations. The evaluation stage uses the supplied inputs.

The request records the carrier-specific band edge, geometry, angular momentum,
interface convention and four prospective outcome labels. JSON restoration checks
these fixed values and the policy below. The same canonical payload determines
the request hash. Result construction and classification belong to T2.

For positive depth, let the matching residual be
`g(x) = cos(x) + (beta*y + beta - 1)*sin(x)/x`, with the analytic limit at zero.
Use the scale `max(1, beta, sqrt(beta)*rho)` for the dimensionless residual.
For `0 < rho < pi`, a scaled endpoint value at `x = rho` within an absolute
guard of 1e-12 is classified as `threshold_unresolved` in binary64 when the sign
cannot be established under this policy. Values above the guard imply
`no_bound_state`. Values below its negative imply a ground-state bracket.
Zero depth gives `no_bound_state`. At `rho >= pi` the ground state exists in
the mathematical model. A result still requires a representable bracket and
strictly interior energy. The exact threshold is a continuum endpoint.

The prospective solver must retain a sign-changing bracket or certify an exact
interior zero. Require bracket widths at most 1e-12 in x and in E/V0 and a
scaled residual magnitude at most 1e-11. The iteration budget is 256. The
bracket width bounds localization of a root of the declared equation,
conditional on reliable signs. The residual measures interface matching.
The two checks address different numerical errors. A collapsed floating-point
bracket with unmet checks, an out-of-range intermediate, or an exhausted budget
requires an explicit numerical failure or threshold-unresolved outcome as applicable.

Predeclared synthetic dimensionless controls use beta = 0.1, 1 and 10 and
rho/rho_c = 0.5, 1 - 1e-6, 1, 1 + 1e-6, 2 and 100. The equal-mass
case uses the analytic pi/2 threshold. An independent high-precision calculation
supplies the unequal-mass thresholds and interior reference roots. For separated
bound controls require absolute differences at most 1e-9 in E/V0 and 1e-8
in exterior probability, with inside plus outside probability agreeing with one
within 1e-10. The exact-threshold target checks the mathematical limit and allows
the recorded binary64 unresolved classification. Include a zero-depth control,
unit conversion, large-barrier comparison with O3 and overflow/underflow controls.
Use independently refined radial discretizations on well-separated controls.
These are prospective numerical targets, with physical applicability recorded
separately. No numerical outputs have been generated by these declarations.

## T2 isolated ground-state evaluation

`evaluate_finite_confinement` takes a typed T1 request and returns a
`FiniteConfinementResult` from `ncmemsim.materials.finite_confinement`.
For rho below pi the solver bisects in the exterior decay fraction
sqrt(1-E/V0), keeping more resolution in the tail near the threshold.
Deeper wells use the interior coordinate x. Both routes check the archived
T1 widths and matching residual. Numerical failures and threshold outcomes
retain their reason and available diagnostics.

For a bound state use the reduced radial function proportional to sin(x r/R)
inside and to sin(x) exp[-y(r/R-1)] outside. Integrating its squared magnitude
over the two intervals gives the dimensionless weights
0.5 - sin(2x)/(4x) and sin(x)^2/(2y). The result reports the two normalized
probabilities, penetration length R/y and the original request and its hash.
The result dictionary records the physical constants and the retained bracket.
Strict result restoration is scheduled for T6.

Validation uses all 18 predeclared T1 threshold and depth cases. Decimal
logarithmic-derivative matching supplies independent interior roots and tail
probabilities. A separate cell-centred spherical flux discretization checks
two well-separated cases at rho = 4 and beta = 0.25 and 1. Its interface face
uses the harmonic conductance of the two half cells. Refinement uses 40, 80, 160 and
320 cells per radius with an exterior Dirichlet boundary at 6R, then 9R on the
finest grid. The grid check requires decreasing errors, a domain sensitivity
below 1e-8 in E/V0 and finest-grid agreement within 2e-5 in E/V0. The Decimal
comparisons use the tighter T1 criteria. Tests also cover the O3 high-barrier
limit, zero depth and unrepresentable binding and dimensionless inputs.
