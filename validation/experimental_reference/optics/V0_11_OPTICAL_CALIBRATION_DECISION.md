# NCMemSim v0.11.0 — optical calibration architecture decision

## Status

    Decision status:
        ACCEPTED FOR IMPLEMENTATION

    Release:
        v0.11.0

    Release theme:
        Experimental Optical Calibration

    Phase:
        F1d — scope and architecture decision

---

# 1. Purpose

This document freezes the implementation scope of NCMemSim v0.11.0
following the audit of Tran et al. (2016).

The decision is based on:

- the experimental-dataset audit;
- the absorption-equation audit;
- the direct-gap and strain-sign audit;
- comparison against the existing v0.10.0 optical implementation.

The purpose is to prevent unresolved literature ambiguities from being
introduced silently into runtime physics.

---

# 2. Primary decision

NCMemSim v0.11.0 will introduce an experimentally anchored,
bulk-like, unstrained Ge/GeSn near-edge optical reference model.

The release will NOT attempt to provide a completely calibrated total
GeSn absorption model over all optical regimes.

The calibrated/reference scope is limited primarily to:

    direct absorption
    +
    Urbach-tail absorption

with parameters anchored to Tran et al. (2016).

---

# 3. Backward compatibility

The existing v0.10.0 optical implementation must remain available and
unchanged by default.

The following existing model remains:

    gesn-absorption-compact-v1

The existing:

    CompositeGeSnAbsorptionModel

continues to provide:

    direct
    + indirect
    + Urbach

using its existing provisional parameterization.

v0.11.0 must not silently replace its default parameters.

Existing v0.10.0 regression behavior must remain reproducible.

---

# 4. Existing direct-gap model

The current NCMemSim direct-gap relation remains unchanged:

    Eg_Gamma(x) =
        (1 - x) * Eg_Gamma_Ge
        + x * Eg_Gamma_alpha_Sn
        - b_Gamma * x * (1 - x)

with the existing parameter set:

    Eg_Gamma_Ge = 0.7985 eV
    Eg_Gamma_alpha_Sn = -0.413 eV
    b_Gamma = 2.89 eV

The Tran result:

    b_Gamma =
        2.92 ± 0.11 eV

is quantitatively consistent with the existing NCMemSim bowing
magnitude.

Therefore the Tran value is used as independent literature-fitted
validation and does not automatically replace the existing parameter.

---

# 5. Direct absorption

The existing NCMemSim direct-absorption functional form:

    alpha_D(E) =
        A * sqrt(E - Eg_Gamma) / E

is algebraically identical to Tran Eq. (3).

Therefore no new direct functional form is required.

The literature-fitted Tran parameter is:

    A =
        (3.68 ± 0.86) × 10^6
        m^-1 eV^(1/2)

when photon energy is represented numerically in eV.

This parameter may be used by the new v0.11.0 near-edge reference
parameter set.

The existing provisional v0.10.0 value remains unchanged.

---

# 6. Urbach width

Tran et al. report:

    Delta_E =
        10.58 ± 1.06 meV

or:

    Delta_E =
        0.01058 ± 0.00106 eV

This value is accepted as a literature-fitted constraint for the
v0.11.0 near-edge reference model.

The existing v0.10.0 compact value:

    urbach_energy_eV = 0.012

remains unchanged in the legacy compact parameter set.

---

# 7. Urbach amplitude and connection

The published Tran direct/Urbach equations contain an internal
dimensional and continuity inconsistency when interpreted literally.

Therefore v0.11.0 will NOT claim a literal production implementation
of Tran Eq. (18).

The new reference model will instead use:

    Tran direct branch
    +
    Tran literature-fitted Urbach width
    +
    an explicitly NCMemSim-derived continuity construction

that provides exact value and first-derivative continuity between the
direct and exponential Urbach branches.

This construction must have provenance distinct from the original
literature equations.

It must be described as:

    NCMemSim-derived continuity construction
    constrained by Tran et al. parameters

and not as:

    literal Tran Eq. (18)

---

# 8. Reference-model identity

The new model should not be named in a way that implies that every
equation is copied literally from Tran et al.

A suitable conceptual identity is:

    GeSnNearEdgeReferenceModel

with a parameter set such as:

    gesn-near-edge-tran2016-v1

The exact public Python class names will be finalized during the F2
software-design phase.

---

# 9. Parameter provenance

The new near-edge parameter set must distinguish the origins of its
quantities.

Candidate classification:

    direct prefactor A:
        LITERATURE_FITTED

    Urbach width Delta_E:
        LITERATURE_FITTED

    existing direct-gap endpoint relation:
        LITERATURE

    existing direct-gap bowing:
        LITERATURE

    Tran bowing result:
        independent LITERATURE_FITTED validation

    direct/Urbach connection relation:
        DERIVED

    calibrated-domain definition:
        VALIDATION_METADATA

The exact software enum representation is deferred to F2.

No existing provenance enum is to be reinterpreted silently.

---

# 10. Strain decision

Strain-dependent bandgap physics will NOT be introduced into the
v0.11.0 runtime optical model.

Reasons include:

- the current NCMemSim optical gap model is explicitly unstrained;
- Tran samples are compressively strained;
- the Tran strain equations contain a documented sign ambiguity;
- reproducing the published 3% Sn example requires explicit
  conduction-minus-valence sign handling;
- strain physics is separable from the primary optical-amplitude
  calibration objective.

Therefore v0.11.0 defines its new reference model as:

    unstrained
    bulk-like
    room-temperature

The audited Tran strain equations and sample metadata remain available
for:

- validation;
- future strain-model development;
- future regression tests.

A strain-dependent optical model may be introduced in a later release
as an explicit capability.

---

# 11. Indirect absorption decision

Tran et al. observe indirect absorption but state that the ellipsometry
data are not sufficiently reliable for quantitative characterization of
the indirect contribution.

Therefore v0.11.0 will NOT calibrate:

    indirect_prefactor_A

or claim quantitative calibration of the phonon-assisted indirect
absorption component.

The existing v0.10.0 indirect model remains available with its existing
provisional status.

The new near-edge reference model will not represent its result as a
fully calibrated total absorption coefficient in spectral regions where
indirect absorption is significant.

A dedicated indirect-absorption dataset audit is deferred to a later
release.

---

# 12. Distinction between reference and total absorption

The new v0.11.0 model represents a calibrated/reference near-edge
response:

    direct + Urbach

It is not automatically equivalent to:

    total GeSn absorption

for all photon energies and Sn compositions.

This distinction is particularly important for lower-Sn material where
indirect absorption can contribute significantly below the direct edge.

Any API, documentation, example, or plot must preserve this distinction.

---

# 13. Spectral and composition domain

The literature source domain used for v0.11.0 is:

    0 <= x_Sn <= 0.10

    1500 nm <= wavelength <= 2500 nm

    room temperature

This is the experimental/literature validation domain.

The software may mathematically evaluate outside this interval if the
underlying functions permit it, but such evaluations must not be
described as calibrated by Tran et al.

They must be identifiable as extrapolation.

---

# 14. Nanocrystal limitation

The v0.11.0 reference model remains a bulk-like / epitaxial-material
baseline.

It does not calibrate:

- quantum confinement;
- nanocrystal-size-dependent bandgaps;
- nanocrystal oscillator-strength changes;
- dielectric confinement;
- nanocrystal/matrix interface states;
- embedded-nanocrystal strain;
- nanocrystal disorder.

Therefore documentation must not describe v0.11.0 as experimental
validation of GeSn nanocrystal absorption.

---

# 15. Photo-transition efficiency

The parameter:

    eta_photo

is outside the v0.11.0 optical-material calibration scope.

v0.11.0 calibrates optical absorption quantities, not the complete
light-to-trapped-charge conversion chain.

Therefore experimental agreement of the near-edge absorption model must
not be presented as calibration of optical programming voltage or
memory-window response.

---

# 16. Runtime-default decision

The v0.11.0 release will not automatically replace the existing default
compact absorption model.

The calibrated/reference near-edge model must be selected explicitly
until a later release decision changes this behavior.

This avoids silently changing existing optical-programming regression
results.

---

# 17. Acceptance requirements

The implementation phase must demonstrate at minimum:

1. direct functional form reproduces the existing audited Eq. (3)
   implementation;

2. the literature parameter:

       A = 3.68e6 m^-1 eV^(1/2)

   is represented with explicit uncertainty and provenance;

3. the literature Urbach width:

       Delta_E = 0.01058 eV

   is represented with explicit uncertainty and provenance;

4. the direct/Urbach branch connection is continuous in value;

5. the direct/Urbach branch connection is continuous in first
   derivative;

6. all outputs remain finite and non-negative inside the declared
   domain;

7. the direct absorption edge red-shifts consistently with increasing
   Sn composition;

8. the existing v0.10.0 compact model remains numerically unchanged
   when the new reference model is not selected;

9. existing v0.10.0 regression tests remain green;

10. documentation distinguishes literature-fitted, literature,
    derived, assumed, and extrapolated quantities.

Numerical tolerances will be defined during test design before the
runtime implementation is accepted.

---

# 18. Deferred capabilities

The following are explicitly deferred from v0.11.0:

    strain-dependent runtime absorption

    quantitative indirect-absorption calibration

    new indirect phonon-energy calibration

    eta_photo calibration

    nanocrystal quantum-confinement correction

    dielectric-environment correction

    nanocrystal-size-dependent oscillator strength

    sequential multi-floating-gate optical attenuation

    transfer-matrix optics

    refractive-index calibration

    automatic replacement of v0.10.0 defaults

These exclusions are deliberate scope controls, not missing
implementation tasks for the v0.11.0 release.

---

# 19. Planned implementation sequence

Following completion of F1, the recommended implementation phases are:

    F2:
        provenance and parameter data model

    F3:
        calibrated/reference near-edge equations

    F4:
        unit and scientific validation tests

    F5:
        integration without changing legacy defaults

    F6:
        experimental/literature validation examples

    F7:
        documentation, reproducibility, full regression and release

No optimizer is required merely to reproduce the already published
Tran central parameters.

A generic calibration/fitting engine may be introduced only where it
adds scientific value beyond direct literature parameter adoption.

---

# 20. F1 closure decision

With this architecture decision:

    primary Tran dataset audit:
        COMPLETE

    equation audit:
        COMPLETE

    direct-gap/bowing audit:
        COMPLETE

    strain-sign audit:
        COMPLETE

    v0.11 strain scope:
        DEFERRED

    v0.11 indirect calibration:
        DEFERRED

    v0.11 direct calibration/reference:
        IN SCOPE

    v0.11 Urbach-width calibration/reference:
        IN SCOPE

    v0.11 continuity construction:
        IN SCOPE, with DERIVED provenance

Therefore:

    PHASE F1 IS COMPLETE

and implementation design may proceed to F2.

No runtime source file has been modified during F1.
