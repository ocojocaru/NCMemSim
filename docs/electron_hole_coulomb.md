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
