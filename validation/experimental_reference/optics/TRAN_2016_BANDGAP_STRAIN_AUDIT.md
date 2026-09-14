# Tran et al. (2016) — bandgap and strain-sign audit

## Purpose

This document records the Phase F1c.3 audit of the direct-bandgap
composition relation and strain correction used by Tran et al. (2016).

The audit compares:

- the published direct-gap bowing relation;
- the current NCMemSim direct-gap convention;
- the published strain-shift equations;
- the numerical strain example reported by Tran et al.;
- the implications for NCMemSim v0.11.0.

No runtime physics is modified in this phase.

---

## Reference

H. Tran et al., Journal of Applied Physics 119, 103106 (2016).

DOI:

    10.1063/1.4943652

---

# 1. Current NCMemSim direct-gap convention

The current NCMemSim direct-gap relation is:

    Eg_Gamma(x) =
        (1 - x) * Eg_Gamma_Ge
        + x * Eg_Gamma_Sn
        - b_Gamma * x * (1 - x)

The current parameter set uses:

    Eg_Gamma_Ge = 0.7985 eV
    Eg_Gamma_alpha_Sn = -0.413 eV
    b_Gamma = 2.89 eV

The bowing parameter is therefore represented as a positive magnitude
and enters the equation with an explicit negative sign.

This convention produces the expected reduction of the direct bandgap
with increasing Sn composition.

---

# 2. Tran Eq. (17)

Tran et al. print the relaxed-GeSn direct-gap relation as:

    Eg_Gamma_GeSn(x) =
        x * Eg_Gamma_Sn
        + (1 - x) * Eg_Gamma_Ge
        + x * (1 - x) * b_Gamma_GeSn

The sign printed in front of the bowing term is therefore:

    +

The fitted bowing factor reported in the same publication is:

    b_Gamma_GeSn =
        2.92 ± 0.11 eV

The publication also reports and plots a strong reduction of the direct
bandgap with increasing Sn composition.

This creates a sign-convention ambiguity if `b_Gamma_GeSn` is interpreted
as the positive numerical value reported in Table III.

---

# 3. Bowing convention

A common semiconductor-alloy convention writes the bandgap as:

    Eg(x) =
        (1 - x) * Eg_A
        + x * Eg_B
        - b * x * (1 - x)

where:

    b > 0

is the magnitude of the downward bowing.

Under this convention, the NCMemSim implementation is consistent with a
positive direct-gap bowing parameter.

Therefore, the Tran Eq. (17) printed `+` sign must not be copied
mechanically into NCMemSim together with a positive `b = 2.92 eV`.

Possible interpretations include:

1. the printed `+` sign is a typographical sign error;
2. Tran's algebraic bowing coefficient is implicitly negative while its
   reported `2.92 eV` is the positive bowing magnitude;
3. another unstated sign convention is being used.

The publication does not resolve this ambiguity explicitly.

NCMemSim must therefore document the convention it uses rather than
silently reproducing the printed sign.

---

# 4. Numerical cross-check with the NCMemSim endpoint convention

Using the current NCMemSim direct-gap endpoints:

    Eg_Gamma_Ge = 0.7985 eV
    Eg_Gamma_alpha_Sn = -0.413 eV

and the Tran bowing magnitude:

    b_Gamma = 2.92 eV

the printed positive-bowing form gives:

    x = 0.10

    Eg_plus approximately 0.940 eV

whereas the negative-bowing convention gives:

    Eg_minus approximately 0.415 eV

The positive-sign result predicts a substantial increase of the direct
bandgap over the investigated Sn range.

That behavior is incompatible with the red-shift and bandgap reduction
reported by Tran et al.

The negative-sign result follows the expected GeSn direct-gap narrowing.

This calculation is a convention cross-check only.

It does not constitute a refit of the Tran data because the endpoint
values above belong to the current NCMemSim literature parameter set,
not to a newly fitted Tran parameter set.

---

# 5. Comparison of bowing magnitudes

Current NCMemSim:

    b_Gamma = 2.89 eV

Tran et al.:

    b_Gamma = 2.92 ± 0.11 eV

The difference between the central values is:

    0.03 eV

which is well inside the uncertainty reported by Tran et al.

Therefore the existing NCMemSim direct-gap bowing magnitude is
quantitatively compatible with the Tran result.

This is an important independent validation of the existing NCMemSim
direct-gap parameterization.

No replacement of the current bowing value is required solely on the
basis of Tran et al.

---

# 6. Current decision for the direct-gap model

For v0.11.0:

    existing NCMemSim direct-gap functional form:
        RETAIN

    explicit negative bowing term:
        RETAIN

    existing b_Gamma = 2.89 eV:
        RETAIN unless a deliberate parameter-set revision is justified

    Tran b_Gamma = 2.92 ± 0.11 eV:
        use as independent LITERATURE_FITTED validation

The Tran value must not silently overwrite the existing literature
parameter set simply because its central value is similar.

---

# 7. Tran strain correction

Tran et al. describe the strain-induced direct-gap change using
conduction- and valence-band shifts.

The printed Eq. (9) is:

    Delta_Eg =
        Delta_E_CB
        + Delta_E_VB

The conduction-band shift is:

    Delta_E_CB =
        dC * (2 * epsilon_parallel + epsilon_perpendicular)

The valence-band shift is:

    Delta_E_VB =
        dV1 * (2 * epsilon_parallel + epsilon_perpendicular)
        + dV2 * (epsilon_perpendicular - epsilon_parallel)

For (100)-oriented material:

    epsilon_perpendicular =
        -2 * (C12 / C11) * epsilon_parallel

Compressive in-plane strain is negative.

---

# 8. Published strain parameters

For Ge, Tran Table II gives:

    dC  = -8.24 eV
    dV1 =  1.24 eV
    dV2 = -2.90 eV

    C12 = 48.26 GPa
    C11 = 128.53 GPa

For Sn:

    dC  = -6.00 eV
    dV1 =  1.58 eV
    dV2 = -2.70 eV

    C12 = 29.3 GPa
    C11 = 69.0 GPa

The publication states that intermediate-composition values are obtained
by linear interpolation between Ge and Sn.

---

# 9. Numerical audit: Ge0.97Sn0.03

Tran reports for sample D:

    x_Sn = 0.03

    compressive in-plane strain magnitude =
        0.24%

    measured strained direct gap =
        0.761 eV

The publication states that its strain-induced direct-gap change is:

    40.7 meV

and gives the strain-relaxed direct gap as approximately:

    0.720 eV

because:

    0.761 eV - 0.0407 eV
        approximately
    0.720 eV

---

# 10. Interpolated material parameters for x = 0.03

Linear interpolation of Table II gives approximately:

    dC =
        -8.1728 eV

    dV1 =
        1.2502 eV

    dV2 =
        -2.8940 eV

    C12 =
        47.6912 GPa

    C11 =
        126.7441 GPa

The compressive in-plane strain is:

    epsilon_parallel =
        -0.0024

Using the published elastic relation:

    epsilon_perpendicular =
        -2 * (C12 / C11) * epsilon_parallel

gives:

    epsilon_perpendicular
        approximately
        +0.00180614

Therefore:

    2 * epsilon_parallel
    + epsilon_perpendicular

        approximately

    -0.00299386

and:

    epsilon_perpendicular
    - epsilon_parallel

        approximately

    +0.00420614

---

# 11. Conduction-band shift

Using the published conduction-band equation:

    Delta_E_CB =
        dC
        * (
            2 * epsilon_parallel
            + epsilon_perpendicular
          )

gives:

    Delta_E_CB
        approximately
        +0.024468 eV

or:

    Delta_E_CB
        approximately
        +24.47 meV

---

# 12. Valence-band shift

Using the published valence-band equation:

    Delta_E_VB =
        dV1
        * (
            2 * epsilon_parallel
            + epsilon_perpendicular
          )
        + dV2
        * (
            epsilon_perpendicular
            - epsilon_parallel
          )

gives:

    Delta_E_VB
        approximately
        -0.015915 eV

or:

    Delta_E_VB
        approximately
        -15.92 meV

---

# 13. Literal evaluation of Tran Eq. (9)

Using the printed Eq. (9):

    Delta_Eg =
        Delta_E_CB
        + Delta_E_VB

gives:

    Delta_Eg
        approximately
        24.47 meV - 15.92 meV

    Delta_Eg
        approximately
        8.55 meV

This does NOT reproduce the value:

    40.7 meV

reported by Tran et al. for the same sample.

---

# 14. Gap-difference evaluation

A semiconductor bandgap is the energy difference between the conduction
and valence edges.

Using:

    Delta_Eg =
        Delta_E_CB
        - Delta_E_VB

with the band-edge shifts calculated above gives:

    Delta_Eg
        approximately
        24.47 meV - (-15.92 meV)

    Delta_Eg
        approximately
        40.38 meV

This agrees closely with the publication's reported:

    40.7 meV

for Ge0.97Sn0.03.

The residual difference is consistent with rounding of the tabulated
material parameters and strain.

---

# 15. Interpretation of the strain-sign result

The numerical reproduction strongly indicates that the calculation
underlying the publication used the conduction-to-valence band-edge
difference:

    Delta_Eg =
        Delta_E_CB
        - Delta_E_VB

rather than the literal plus sign printed in Eq. (9), under the band-edge
sign convention represented by Eqs. (10) and (11).

This is evidence of a sign-convention or typographical inconsistency in
the published equation set.

NCMemSim must not copy Eq. (9) literally without reproducing the authors'
reported numerical example.

---

# 16. Consequence for a Tran strain implementation

If strain correction is introduced in NCMemSim v0.11.0, acceptance must
be based on the reproducible physical and numerical result, not only on
literal transcription of the printed equations.

A candidate regression case would be:

    material:
        Ge0.97Sn0.03

    epsilon_parallel:
        -0.0024

    expected strain-induced direct-gap shift:
        approximately +40.7 meV

    expected relaxed gap from measured 0.761 eV:
        approximately 0.720 eV

The numerical tolerance must be defined before implementation.

---

# 17. Provenance requirement

Any future strain model must state explicitly:

    source equations:
        Tran et al. 2016

    sign convention:
        conduction-minus-valence band-edge shift

    validation target:
        published 3% Sn example, Delta_Eg = 40.7 meV

This avoids presenting a silent correction of the publication as though
it were a literal transcription.

---

# 18. Architectural consequence

The F1 audits now identify three distinct issues that must not be mixed:

1. direct absorption:
       existing NCMemSim form matches Tran Eq. (3);

2. direct/Urbach connection:
       published equations contain a dimensional/continuity inconsistency;

3. direct-gap/strain model:
       published equations contain sign-convention ambiguities that must
       be resolved through numerical reproduction.

Therefore a future `Tran2016...` implementation must be treated as a
carefully audited reconstruction rather than a literal equation copy.

---

# 19. Current v0.11 decision

The current NCMemSim unstrained direct-gap model remains unchanged.

Specifically:

    direct_gap_gesn_eV():
        unchanged

    direct_gap_bowing_eV = 2.89:
        unchanged

    bowing sign:
        retain explicit negative term

The Tran result:

    2.92 ± 0.11 eV

serves as independent support for the magnitude of the existing direct
bowing.

Strain-dependent bandgap physics remains a separate architecture decision.

---

# 20. Status

    Phase F1c.3:
        COMPLETE

    Bowing-sign convention:
        AUDITED

    Existing NCMemSim bowing sign:
        RETAIN

    Existing NCMemSim bowing magnitude:
        CONSISTENT WITH TRAN WITHIN REPORTED UNCERTAINTY

    Literal Tran Eq. (17) plus sign:
        DO NOT COPY WITHOUT SIGN-CONVENTION RESOLUTION

    Literal Tran Eq. (9) plus sign:
        DOES NOT REPRODUCE PUBLISHED 3% Sn EXAMPLE

    Conduction-minus-valence interpretation:
        REPRODUCES PUBLISHED 40.7 meV EXAMPLE

    Runtime code changed:
        NO

    Existing v0.10 regression tests changed:
        NO
