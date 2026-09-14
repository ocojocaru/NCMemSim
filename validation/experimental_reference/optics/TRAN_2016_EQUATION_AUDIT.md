# Tran et al. (2016) — absorption-equation audit

## Purpose

This document records the Phase F1c equation-level comparison between the
published Tran et al. (2016) GeSn near-edge absorption model and the current
NCMemSim optical implementation.

The audit covers:

- direct absorption;
- dimensional consistency;
- Urbach absorption;
- direct/Urbach continuity;
- parameter mapping to NCMemSim;
- consequences for the v0.11.0 architecture.

No runtime physics is modified in this phase.

---

## Reference

H. Tran et al., Journal of Applied Physics 119, 103106 (2016).

DOI:

    10.1063/1.4943652

---

# 1. Direct absorption

Tran et al. Eq. (3) gives:

    (alpha_D * E)^2 =
        A^2 * (E - Eg_Gamma)

where E = hν.

Therefore:

    alpha_D(E) =
        A * sqrt(E - Eg_Gamma) / E

for E > Eg_Gamma.

The current NCMemSim `direct_absorption_m_inv()` implementation is
algebraically identical:

    alpha_direct =
        direct_prefactor_A
        * sqrt(E - Eg_Gamma)
        / E

Therefore:

    direct functional form:
        TRAN == NCMemSim CompositeGeSnAbsorptionModel

This is an exact algebraic match.

The simpler `CompactOpticalMaterialModel`, which does not contain the
division by photon energy, is a separate compact model and must not be
confused with `CompositeGeSnAbsorptionModel`.

---

# 2. Direct parameter mapping

Tran et al. report:

    A =
        (3.68 ± 0.86) × 10^4
        cm^-1 eV^(1/2)

Using:

    1 cm^-1 = 100 m^-1

the corresponding numerical value in NCMemSim length units is:

    A =
        (3.68 ± 0.86) × 10^6
        m^-1 eV^(1/2)

provided photon energy continues to be represented numerically in eV.

The current NCMemSim provisional value is:

    direct_prefactor_A = 1.0e7

Therefore the current default amplitude is approximately 2.72 times the
central Tran value.

No default is changed during Phase F1.

Candidate v0.11 provenance:

    parameter:
        direct_prefactor_A

    source:
        Tran et al. 2016

    status:
        LITERATURE_FITTED

    value:
        3.68e6 m^-1 eV^(1/2)

    uncertainty:
        0.86e6 m^-1 eV^(1/2)

---

# 3. Dimensional audit of the direct branch

For:

    alpha_D =
        A * sqrt(E - Eg) / E

and:

    [A] = cm^-1 eV^(1/2)

the dimensions are:

    cm^-1 eV^(1/2)
    * eV^(1/2)
    / eV

which gives:

    cm^-1

Therefore Tran Eq. (3) is dimensionally consistent with the published
unit of A.

---

# 4. Published Urbach relation

Tran Eq. (4) uses:

    alpha_U(E) =
        alpha_0
        * exp[(E - Eg_Gamma) / Delta_E]

The authors then impose the stated connection conditions:

    alpha_U(Ec) = alpha_D(Ec)

and:

    d(alpha_U)/dE at Ec
        =
    d(alpha_D)/dE at Ec

The publication gives:

    Ec =
        Eg_Gamma + Delta_E / 2

and:

    alpha_0 =
        A
        * exp(-1/2)
        * sqrt(Delta_E / 2)

which produces Eq. (7):

    alpha_U(E) =
        A
        * exp(-1/2)
        * sqrt(Delta_E / 2)
        * exp[(E - Eg_Gamma) / Delta_E]

The same Urbach branch appears in Eq. (18).

---

# 5. Dimensional inconsistency

Using the published unit:

    [A] = cm^-1 eV^(1/2)

the prefactor of the published Urbach expression has dimensions:

    [A * sqrt(Delta_E)]
        =
    cm^-1 eV

rather than:

    cm^-1

Therefore the published Urbach branch is not dimensionally consistent
with alpha when combined literally with the published unit of A.

This inconsistency must be retained explicitly in the provenance audit.

NCMemSim must not silently repair the equation and still describe the
result as a literal implementation of Tran Eq. (18).

---

# 6. Value-continuity audit

The published connection energy is:

    Ec =
        Eg_Gamma + Delta_E / 2

At this energy, Tran Eq. (3) gives:

    alpha_D(Ec) =
        A
        * sqrt(Delta_E / 2)
        / Ec

while the published Urbach branch gives:

    alpha_U(Ec) =
        A
        * sqrt(Delta_E / 2)

because:

    exp(-1/2) * exp(+1/2) = 1

Therefore:

    alpha_D(Ec) != alpha_U(Ec)

when Eq. (3) and Eq. (7) are interpreted literally.

If energy values are inserted numerically in eV, the numerical ratio is:

    alpha_U(Ec) / alpha_D(Ec) = Ec

This ratio is not dimensionally meaningful as a physical ratio, which
is another manifestation of the same inconsistency.

For representative Tran direct-gap values and the central Urbach width:

    Delta_E = 0.01058 eV

the literal equations imply a substantial numerical mismatch at the
published branch point.

For approximately:

    Eg_Gamma = 0.805 eV

the mismatch is about 19%.

For approximately:

    Eg_Gamma = 0.604 eV

the mismatch is about 39%.

Therefore the mismatch is not negligible compared with the intended
accuracy of a calibrated optical model.

---

# 7. Derivative-continuity audit

The published Eq. (6) connection energy:

    Ec =
        Eg_Gamma + Delta_E / 2

would give exact value and derivative continuity for a direct law of the
form:

    alpha_D =
        A * sqrt(E - Eg_Gamma)

without the `1 / E` factor.

However, Tran Eq. (3) contains the `1 / E` factor.

Consequently, Eqs. (6) and (7) are algebraically consistent with the
simpler square-root direct law, but are not exactly consistent with the
direct law obtained from Eq. (3).

This observation is an inference from the published equations.

It must not be represented as proof of which equation contains a
typographical or derivational error.

---

# 8. NCMemSim continuity-consistent derivation

A mathematically exact direct/Urbach connection can be derived while
retaining Tran Eq. (3).

Let:

    y =
        E - Eg_Gamma

and let `yc` be the value at the connection point.

The direct branch is:

    alpha_D =
        A * sqrt(y) / (Eg_Gamma + y)

The Urbach branch is:

    alpha_U =
        alpha_0 * exp(y / Delta_E)

Matching logarithmic derivatives gives:

    1 / (2 * yc)
    - 1 / (Eg_Gamma + yc)
    =
    1 / Delta_E

which leads to:

    2 * yc^2
    + (2 * Eg_Gamma + Delta_E) * yc
    - Delta_E * Eg_Gamma
    =
    0

The positive root is:

    yc =
        (
            -(2 * Eg_Gamma + Delta_E)
            + sqrt(
                (2 * Eg_Gamma + Delta_E)^2
                + 8 * Delta_E * Eg_Gamma
            )
        ) / 4

The exact connection energy is then:

    Ec =
        Eg_Gamma + yc

and value continuity gives:

    alpha_0 =
        A
        * sqrt(yc)
        / Ec
        * exp(-yc / Delta_E)

This construction provides exact value and first-derivative continuity
between the Tran Eq. (3) direct branch and an exponential Urbach branch.

However:

    THIS IS AN NCMemSim-DERIVED RELATION.

It is not Tran Eq. (6), Eq. (7), or Eq. (18).

It must therefore have separate provenance if it is ever implemented.

---

# 9. Small-Urbach-width limit

For:

    Delta_E << Eg_Gamma

the exact connection offset approaches:

    yc approximately Delta_E / 2

which explains why the published connection energy is close to the
solution obtained when the photon-energy denominator is treated as
locally slowly varying.

Nevertheless, approximate agreement of the connection energy does not
remove the missing dimensional factor in the published Urbach
amplitude.

---

# 10. Current NCMemSim Urbach model

The current NCMemSim v0.10.0 Urbach model is:

    alpha_U(E) =
        alpha_edge
        * exp[(E - Eg_Gamma) / E_U]

for:

    E < Eg_Gamma

and zero for:

    E >= Eg_Gamma

with:

    urbach_energy_eV = 0.012
    urbach_edge_alpha_m_inv = 1.0e5

The current amplitude is independent of the direct-absorption
prefactor.

Therefore this model is not equivalent to the Tran Urbach
parameterization.

The current NCMemSim function also switches the Urbach contribution off
at `Eg_Gamma`, while Tran places its published direct/Urbach branch
connection above the direct gap.

---

# 11. Published Urbach-width mapping

Tran et al. report:

    Delta_E =
        10.58 ± 1.06 meV

or:

    Delta_E =
        0.01058 ± 0.00106 eV

This value can be compared directly with the NCMemSim quantity:

    urbach_energy_eV

The current provisional value:

    0.012 eV

is close to the literature-fitted central value.

However, numerical closeness does not make the existing Urbach model
fully calibrated because its amplitude and branch construction differ
from Tran.

Therefore:

    urbach_energy_eV:
        quantitatively constrained by Tran

    urbach_edge_alpha_m_inv:
        NOT calibrated by Tran

---

# 12. Architectural conclusion

The existing v0.10.0 compact model must remain backward compatible.

No existing parameter should be silently reinterpreted.

The preferred architecture for v0.11.0 is to preserve:

    gesn-absorption-compact-v1

as the existing compact model.

A separate literature-anchored near-edge implementation may then be
introduced after the equation inconsistency is resolved explicitly.

At minimum, the architecture must distinguish:

    published Tran equation
    NCMemSim continuity-consistent derivation
    existing compact model

These are not scientifically identical models.

---

# 13. Immediate v0.11 conclusions

The following result is established:

    current CompositeGeSnAbsorptionModel direct form
        ==
    Tran Eq. (3) direct form

Therefore the Tran direct amplitude can be transferred to a dedicated
literature parameter set without changing the direct functional form.

The following result is also established:

    current NCMemSim Urbach model
        !=
    Tran published Urbach construction

and:

    Tran Eq. (3)
        is not exactly consistent with
    Tran Eqs. (6), (7), and (18)
        under literal dimensional and continuity analysis.

Therefore no Tran-specific Urbach runtime implementation should be
added until its intended semantics are explicitly selected and
documented.

---

# 14. Status

    Phase F1c.1:
        COMPLETE

    Phase F1c.2:
        COMPLETE

    Runtime code changed:
        NO

    Existing v0.10 regression tests changed:
        NO

    Tran direct parameter accepted for future parameter-set work:
        YES

    Tran Urbach width accepted as literature-fitted:
        YES

    Tran Urbach amplitude accepted literally for production runtime:
        NO

    Indirect absorption calibrated:
        NO
