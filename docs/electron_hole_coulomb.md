# Phase U0 finite-well electron–hole Coulomb correction

## Model and source audit

Use the product of two normalized, independent Phase T spherical ground states
with angular momentum zero. The first-order energy shift is the expectation of
the attractive direct Coulomb interaction with one explicitly supplied uniform
relative permittivity. The same kernel applies inside and outside the sphere.
Its applicability is a caller declaration, with provenance and the screening
convention recorded alongside the value. This diagnostic leaves dielectric
interfaces, polarization self-energy, exchange and wavefunction correlation
for separate studies.

The [T2 result](finite_confinement.md) retains the original well request, radius,
dimensionless wave numbers x and y, energy and inside/outside probabilities.
For each accepted bound state, reconstruct the reduced radial envelope using
the dimensionless radius t = r/R. Before normalization it is sin(x t) for
t ≤ 1 and sin(x) exp[−y(t − 1)] for t ≥ 1. Square and normalize over [0, ∞)
to obtain p(t), the probability density with respect to dt. The stored outside
probability provides a normalization cross-check. Both requests must describe
the same radius, temperature, dot and host, with explicit electron and hole
identities. Retain each carrier's status and reason. If either state is
unavailable, record a null Coulomb correction.

For a uniform dielectric, the angular average of the inverse separation for
two isotropic densities is 1/max(r_e, r_h). Split the radial integral at
t_e = t_h. With F_i(t) = ∫₀ᵗ p_i(s) ds, the dimensionless coefficient is

    K = ∫₀∞ [p_e(t) F_h(t) + p_h(t) F_e(t)] / t dt

The signed correction in joules is −q² K/(4π ε₀ ε_r R). The reduced radial
densities vanish quadratically at the origin. Split quadrature at t = 1 and
include the exterior tails. If both integrals are truncated at L ≥ 1, the
omitted coefficient is bounded above by [P_e(t > L) + P_h(t > L)]/L,
where P_i(t > L) = P_i(t > 1) exp[−2 y_i(L − 1)]. Treat this bound separately
from the numerical integration error. A shallow accepted well may require a
large exterior domain.

## References and acceptance

- [Chhabra, Ranjan and Singh](https://arxiv.org/abs/cond-mat/9902310)
  provides the finite-well mass-discontinuity setting used in Phase T.
- [Brus (1984)](https://doi.org/10.1063/1.447218) gives the effective-mass
  Coulomb model for small crystallites. Use the hard-wall coefficient as a
  reference for the direct term under uniform screening.
- [Goldoni et al.](https://arxiv.org/abs/cond-mat/9906338) analyzes how
  dielectric confinement changes interactions. Its abstract supports
  treating dielectric contrast as a separate modeling problem.

For two hard-wall ground states, p(t) = 2 sin²(πt) on [0, 1]. Substitution
gives K = 2 − [Si(2π) − Si(4π)/2]/π, approximately 1.786. Use the closed form
for the hard-wall kernel check and deep finite wells for a separately refined
limit check. Compare finite-well coefficients against an independent
high-precision two-radius integral split at the diagonal and at the interface.
Include symmetric, unequal-mass and substantial-tail controls.

Proposed U1 numerical targets for the synthetic reference grid are relative
agreement of 10⁻⁸ in K against a refined independent reference and a tail
bound below 10⁻¹⁰ in K. Fix an explicit quadrature budget before evaluating
the grid. Check carrier exchange symmetry, the negative energy sign and
inverse-permittivity scaling. For radius scaling, hold x and y fixed by
scaling each well depth as 1/R². Record a numerical failure when the requested
accuracy cannot be established. These tolerances describe numerical agreement
for the declared model. A later applicability review must assess perturbation
size against relevant level separations before any optical integration.


## U1 evaluator

Pass matched finite-well requests to `evaluate_electron_hole_coulomb` in
`ncmemsim.materials.electron_hole_coulomb`, with an explicit relative
permittivity and structural evidence for the screening choice. The evaluator
solves each request and records both outcomes. An unavailable carrier leaves
the correction undefined. Quadrature or energy range failures return a
distinct numerical failure status.

The reference grid specifies (mass ratio, dimensionless depth parameter)
for electron and hole respectively. It includes (1, 4) and (1, 4) for
identical wells, (0.25, 4) and (2, 3) for unequal masses, and (1, 1.6)
and (1, 1.7) for substantial exterior probability. Nested adaptive integration
of both radial variables provides an independent integration reference.

Production quadrature uses Gauss–Legendre rules of order 16, 32, 64 and
128 at most, with the interface and both exterior decay scales represented
in the subdivision. The accepted change between successive orders plus
the tail bound must be at most 10⁻⁸ times the coefficient. The refinement
change is an error estimate. The tail bound follows from the omitted probability.


## U2 perturbation scale study

```shell
python examples/phase_u2_coulomb_applicability.py --output outputs/u2_study.json
```

The study compares the magnitude of the first-order diagonal energy shift
with the smaller of the two continuum separations, each given by V₀ − E.
The radius, hole depth and permittivity controls each vary one input from the
baseline. A zero-depth hole supplies an unavailable control.

The first unperturbed excitation can lie below the continuum threshold.
A ratio of one or greater flags a correction at least as large as the
continuum separation. Ratios below one are inconclusive. Perturbative
applicability also depends on the discrete spectrum and off-diagonal coupling
matrix elements. A later optical integration decision needs those inputs
or independent evidence for the approximation over the proposed domain.


## U3 excitation scales and angular momentum

```shell
python examples/phase_u3_coulomb_spectral_gap.py --output outputs/u3_study.json
```

U3 reuses the five U2 cases. Each carrier has equal inside and outside masses.
The matching thresholds for the first ℓ = 1 bound state and second ℓ = 0 state
are ρ = π and ρ = 3π/2, respectively. The first ℓ = 1 branch lies below
the second ℓ = 0 branch because its hard-wall wave number is below 3π/2.
Higher angular channels have a larger centrifugal term. The example solves
the excited branches or uses the continuum threshold when a branch is
unavailable. See the [finite spherical well derivation](https://bingweb.binghamton.edu/~suzuki/QuantumMechanicsII/5-4_Finite_spherical_well.pdf)
and [spherical Bessel recurrences](https://dlmf.nist.gov/10.51).

The full unperturbed pair gap is the smaller single-carrier excitation gap.
The direct Coulomb operator is rotationally invariant. From the ground pair
it couples only within total orbital angular momentum L = 0. In that sector
the first excitation is either a radial excitation in one carrier, including
its continuum threshold, or an ℓ = 1 excitation in both carriers coupled to
L = 0. Higher equal-ℓ channels have higher onset energies.

The ratio of the diagonal shift to either gap remains a comparison of energy
scales. Computing off-diagonal couplings or comparing against an interacting
pair solution would provide a separate perturbation accuracy check.


## U4 single-carrier radial couplings

```shell
python examples/phase_u4_coulomb_radial_coupling.py --output outputs/u4_study.json
```

The five U2 cases supply the requests and screening. For each carrier U4
constructs its first excited bound s state, when present, and keeps the
spectator in its ground state. All cases use equal inside and outside masses.
The signed reduced envelope is continuous at the interface. Its normalized
overlap with the corresponding ground state supplies an orthogonality check.

In the direct radial integral, replace the excited carrier's probability
density by the product of its ground and excited envelopes. The spectator
retains its ground-state probability density. The same angular average
1/max(r_e, r_h) applies because both individual angular momenta are zero.
Adaptive nested quadrature integrates each domain to infinity with a split
at the interface. Tolerances 10⁻¹⁰ and 10⁻¹² supply a refinement comparison.

For matrix element M and excitation gap Δ, each channel reports the
first-order amplitude magnitude |M|/Δ and second-order contribution −|M|²/Δ.
The sign of M follows the chosen radial phases. The contributions describe
the included bound radial channels. Additional radial, angular and continuum
channels contribute to the full interacting-pair problem. Optical
applicability remains a further assessment.


## U5 bound angular channel

```shell
python examples/phase_u5_coulomb_angular_coupling.py --output outputs/u5_study.json
```

U5 reuses the five U2 cases and the bound first p states from U3. Both
carriers must have accepted ground states and a bound first p state.
The exterior reduced radial envelope is proportional to t k₁(yt),
matched continuously to t j₁(xt) inside. Normalization integrates the
interior and exterior domains to infinity. Equal masses at each carrier's
interface are required.

With the Condon–Shortley phases, the coupled angular function for the
1p electron–hole pair at total L = 0 is −√3 cos(γ)/(4π), where γ is
the angle between the two carrier positions. The 1s pair angular function
is 1/(4π). The addition theorem and Clebsch–Gordan coefficients give the
angular projection of the inverse separation as
−min(t_e,t_h)/(√3 max(t_e,t_h)²) in dimensionless radii.
This expression is derived from the
[spherical harmonic addition theorem](https://dlmf.nist.gov/14.30.E9) and
[angular momentum coupling coefficients](https://dlmf.nist.gov/34.3.E1).
The test compares it with direct angular integration.

The radial integral uses the products of each carrier's ground and p-state
envelopes. On each triangle of the two-radius domain its inner integral
contains s times the transition density, and its outer factor contains
the other transition density divided by t². The study uses the signed
angular factor −1/√3 and the attractive Coulomb prefactor. A change of
phase changes the sign of the matrix element. The amplitude magnitude
and second-order contribution are invariant under that change.

Nested quadrature with tolerances 10⁻¹⁰ and 10⁻¹² checks refinement. The
change must be below 10⁻⁸ of the coefficient. Quadrature warnings and
refinement failures are retained as numerical failures. The baseline and
weaker-screening cases have this bound angular channel. The smaller-radius
and shallower-hole cases retain an unavailable channel. The zero-depth hole
retains its unavailable ground-state outcome.

The reported |M|/Δ and −|M|²/Δ refer to this single coupled angular channel.
Together with U4 they provide selected-channel diagnostics. Higher radial
and angular states and the continuum enter a complete pair calculation.


## U6 direct Coulomb reporting

```shell
python examples/phase_u6_coulomb_report.py --output outputs/u6_bundle
```

`CoulombStudyReport` in `ncmemsim.coulomb_reporting` accepts an ordered
list of cases, each with a unique label, a U1 result and JSON settings.
It rebuilds both carrier states and the direct energy shift from the
original requests and screening evidence. The report owns a serialized
copy of all cases, counts evaluated, unavailable and numerical-failure
outcomes, and records units, electrostatic constants and the numerical policy.
The included U1 results retain each carrier's finite-well numerical policy.

The example exports all five U2 direct results and an additional artificial
energy-underflow control with relative permittivity 10³⁰⁸. This last case
exercises numerical-range reporting. The writer creates a new directory
containing report.json, report.md, cases.csv and bundle.json. The manifest
records the report hash and SHA-256 hashes of the three projections. The
reader verifies exact directory membership and source reconstruction and
compares each regenerated projection with the saved bytes.

Restoration requires exact diagnostic agreement in a numerically compatible
runtime. Settings and screening evidence retain their caller-declared
provenance. U4 and U5 retain their channel-specific JSON study formats.
Their matrix elements and perturbation amplitudes need an explicit
extension of the reporting schema before source-verified restoration.
