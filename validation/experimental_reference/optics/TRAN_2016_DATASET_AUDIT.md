# Tran et al. (2016) — GeSn optical absorption dataset audit

## Purpose

This document records the Phase F1 audit of the primary experimental literature source used to establish the optical absorption calibration strategy for NCMemSim v0.11.0.

The purpose of this audit is to determine:

* which quantities are directly associated with experiment;
* which quantities are derived from an optical model;
* which parameters were fitted and published by the authors;
* which parts of the current NCMemSim optical model can be constrained by this publication;
* which parts must remain provisional or require an independent experimental source.

No NCMemSim parameter is to be reclassified as experimentally calibrated solely because it appears in a model that qualitatively reproduces the published curves.

The following provenance categories are used conceptually during this audit:

* `EXPERIMENTAL` — directly measured experimental quantities;
* `MODEL_DERIVED` — quantities extracted from experimental measurements using an optical model;
* `LITERATURE` — quantities, relations, or constants adopted from published literature;
* `LITERATURE_FITTED` — parameters fitted by the publication authors to their experimentally derived data;
* `DIGITIZED` — numerical values reconstructed from a published figure;
* `FITTED` — parameters fitted subsequently by NCMemSim;
* `ASSUMED` — provisional model quantities not established experimentally;
* `BENCHMARK` — quantities deliberately selected for numerical or physical benchmark purposes;
* `EXTRAPOLATED` — model evaluations outside the experimentally supported calibration domain.

These labels describe scientific provenance. The exact NCMemSim software representation of these categories will be decided in a later development phase.

---

## Primary reference

H. Tran, W. Du, S. A. Ghetmiri, A. Mosleh, G. Sun, R. A. Soref, J. Margetis, J. Tolle, B. Li, H. A. Naseem, and S.-Q. Yu,

"Systematic study of Ge1-xSnx absorption coefficient and refractive index for the device applications of Si-based optoelectronics",

Journal of Applied Physics 119, 103106 (2016).

DOI:

```text
10.1063/1.4943652
```

Publication date:

```text
11 March 2016
```

---

## Experimental material system

The study investigates Ge1-xSnx thin films with Sn compositions from 0% to 10%.

The GeSn layers were grown by reduced-pressure chemical vapor deposition on a strain-relaxed Ge buffer grown on Si (001).

The reported sample set contains eleven samples, labelled A through K:

* sample A: Ge reference;
* samples B–K: GeSn with Sn composition increasing from 1% to 10%.

All GeSn layers were unintentionally p-type, with a reported background doping concentration of approximately:

```text
1e17 cm^-3
```

Material characterization including X-ray diffraction and transmission electron microscopy was used to establish quantities including:

* Sn composition;
* GeSn layer thickness;
* strain.

---

## Spectroscopic ellipsometry measurements

Spectroscopic ellipsometry measurements were performed using a variable-angle spectroscopic ellipsometer.

The full instrumental measurement range reported in the publication is:

```text
0.496–4.768 eV
260–2500 nm
```

with a wavelength resolution of:

```text
10 nm
```

Measurements were performed at three incidence angles:

```text
65 degrees
70 degrees
75 degrees
```

The part of the spectrum specifically discussed for the GeSn near-IR and shortwave-IR optical model is:

```text
0.496–0.826 eV
1500–2500 nm
```

The measurements were performed at room temperature.

---

## Important provenance distinction

The spectral absorption-coefficient values shown in the publication are not direct raw measurements of alpha.

The directly measured ellipsometric quantities were processed using the Johs-Herzinger optical model.

The workflow used by the authors is therefore conceptually:

```text
ellipsometric measurement
        |
        v
measured Psi / Delta
        |
        v
Johs-Herzinger optical model
        |
        v
spectral optical properties
        |
        v
alpha(hν), n(lambda)
        |
        v
physical-model fitting
        |
        v
published optical parameters
```

Consequently, the absorption-coefficient points obtained from the Johs-Herzinger model should be classified as:

```text
MODEL_DERIVED
```

rather than raw `EXPERIMENTAL` alpha measurements.

The original ellipsometric measurements remain experimental.

The parameters subsequently obtained by fitting physical models to the derived alpha data should be classified as:

```text
LITERATURE_FITTED
```

from the perspective of NCMemSim.

---

## Sample metadata

Table I of the publication provides Sn composition, GeSn thickness, compressive in-plane strain, measured direct bandgap, and ellipsometry fitting MSE for samples A–K.

| Sample | Sn (%) | Film thickness (nm) | Compressive in-plane strain (%) | Measured direct gap (eV) |   MSE |
| ------ | -----: | ------------------: | ------------------------------: | -----------------------: | ----: |
| A      |      0 |                 300 |                            0.00 |            0.805 ± 0.037 | 3.876 |
| B      |      1 |                 327 |                            0.02 |            0.792 ± 0.027 | 9.917 |
| C      |      2 |                  40 |                            0.22 |            0.772 ± 0.022 | 13.58 |
| D      |      3 |                 128 |                            0.24 |            0.761 ± 0.046 | 11.40 |
| E      |      4 |                  70 |                            0.50 |            0.723 ± 0.020 | 12.85 |
| F      |      5 |                  88 |                            0.67 |            0.721 ± 0.042 | 10.42 |
| G      |      6 |                  96 |                            0.82 |            0.713 ± 0.024 | 13.49 |
| H      |      7 |                 240 |                            0.45 |            0.682 ± 0.017 | 9.322 |
| I      |      8 |                  90 |                            0.80 |            0.626 ± 0.015 | 5.450 |
| J      |      9 |                 117 |                            1.01 |            0.617 ± 0.012 | 8.640 |
| K      |     10 |                  59 |                            1.16 |            0.604 ± 0.012 | 8.818 |

The direct-gap values in this table correspond to the strained samples.

They must not be interpreted as relaxed bulk GeSn direct-gap values without application of the strain correction used in the publication.

---

## Special case: sample H

The 7% Sn sample, sample H, requires special attention.

Its GeSn film thickness is:

```text
240 nm
```

The authors identify this thickness as exceeding the critical thickness, leading to gradual relaxation of the GeSn film.

They therefore note that the measured strain represents an averaged strain state and attribute the deviation of the 7% Sn sample from the fitted relaxed-bandgap trend to this partial relaxation.

Sample H should therefore be treated carefully in any subsequent validation or uncertainty analysis.

It must not silently receive the same interpretation as fully coherent samples.

---

# Absorption model used in the publication

## General decomposition

The publication first writes the general absorption coefficient as:

```text
alpha(hν) =
    alpha_indirect(hν)
    + alpha_direct(hν)
    + alpha_Urbach(hν)
```

This decomposition is conceptually similar to the decomposition used in NCMemSim v0.10.0.

However, the final quantitative formula published by Tran et al. does **not** retain an independently parameterized indirect-absorption term.

This distinction is essential for v0.11.0.

---

# Direct absorption

Near the direct band edge, the publication uses the relation:

```text
(alpha_D * hν)^2 =
    A^2 * (hν - Eg_Gamma)
```

which gives:

```text
alpha_D(hν) =
    A * sqrt(hν - Eg_Gamma) / hν
```

for photon energies in the direct-transition region.

Here:

* `alpha_D` is the direct-transition absorption coefficient;
* `hν` is photon energy;
* `Eg_Gamma` is the direct Gamma-valley bandgap;
* `A` is a material parameter.

This functional form is important because the factor:

```text
1 / hν
```

is explicitly present.

Therefore, the Tran direct-absorption formula is not necessarily identical to a compact model consisting only of a constant prefactor multiplying:

```text
sqrt(hν - Eg_Gamma)
```

Any mapping between the current NCMemSim `direct_prefactor_A` and the Tran parameter `A` must therefore be derived explicitly rather than assumed.

---

## Published direct-absorption parameter

The authors report that the slopes of the direct-absorption curves are approximately identical across the investigated samples despite differences in Sn composition and strain.

They therefore treat `A` as approximately independent of Sn composition and strain over the investigated range.

The fitted value is:

```text
A = (3.68 ± 0.86) × 10^4 cm^-1 eV^(1/2)
```

This parameter is:

```text
LITERATURE_FITTED
```

from the NCMemSim perspective.

Converted to SI absorption-length units:

```text
A = (3.68 ± 0.86) × 10^6 m^-1 eV^(1/2)
```

provided photon energy continues to be represented numerically in eV in the corresponding empirical expression.

This conversion does not remove the need to preserve the original formula and dimensional convention.

---

# Direct bandgap and Sn composition

For relaxed GeSn, Tran et al. use the quadratic composition relation:

```text
Eg_Gamma_GeSn(x) =
    x * Eg_Gamma_Sn
    + (1 - x) * Eg_Gamma_Ge
    + x * (1 - x) * b_Gamma_GeSn
```

where:

* `x` is the Sn mole fraction;
* `b_Gamma_GeSn` is the direct-gap bowing factor.

The fitted bowing factor reported in the publication is:

```text
b_Gamma_GeSn = 2.92 ± 0.11 eV
```

This value is:

```text
LITERATURE_FITTED
```

The relation applies to relaxed GeSn.

The direct gaps measured for the actual samples cannot be inserted directly into this relaxed-material relation because the experimental samples are compressively strained.

---

# Strain treatment

Strain is not merely descriptive metadata in the Tran optical model.

It enters the calculation of the bandgap used to predict the absorption spectrum.

The publication computes the strain-induced bandgap shift from conduction- and valence-band edge shifts.

Conceptually:

```text
Delta_Eg =
    Delta_E_CB
    + Delta_E_VB
```

The conduction-band and valence-band shifts are calculated using deformation potentials and the in-plane and out-of-plane strain.

For (100)-oriented films, the out-of-plane strain is related to the in-plane strain through the elastic constants.

The material parameters reported for the strain calculation include:

| Material | Conduction deformation potential Γ (eV) | dV1 (eV) | dV2 (eV) | C12 (GPa) | C11 (GPa) | Lattice constant (Å) |
| -------- | --------------------------------------: | -------: | -------: | --------: | --------: | -------------------: |
| Ge       |                                   -8.24 |     1.24 |     -2.9 |     48.26 |    128.53 |               5.6573 |
| Sn       |                                   -6.00 |     1.58 |     -2.7 |      29.3 |      69.0 |               6.4892 |

For intermediate GeSn compositions, the publication assumes linear interpolation between the Ge and Sn values.

---

## Example: Ge0.97Sn0.03

For the 3% Sn sample:

```text
x_Sn = 0.03
compressive in-plane strain = 0.24%
measured strained direct gap = 0.761 eV
```

The publication calculates a strain-induced direct-bandgap change of:

```text
40.7 meV
```

and obtains a strain-relaxed direct gap of approximately:

```text
0.720 eV
```

This example demonstrates that strain corrections are quantitatively significant relative to the desired accuracy of an optical calibration.

---

# Urbach absorption

The publication describes the Urbach tail using:

```text
alpha_U(hν) =
    alpha_0 *
    exp[(hν - Eg_Gamma) / Delta_E]
```

where:

* `Delta_E` is the Urbach width;
* `alpha_0` is an amplitude parameter;
* `Eg_Gamma` is the direct bandgap.

However, `alpha_0` is not treated as an independent free parameter in the final model.

The authors impose continuity between the direct-absorption branch and the Urbach branch, including continuity of the first derivative at the connection energy.

The resulting connection energy is:

```text
E_connection =
    Eg_Gamma + Delta_E / 2
```

and the Urbach amplitude is determined by the direct parameter `A` and the Urbach width.

Therefore, in the Tran parameterization:

```text
Urbach amplitude != independent fitted parameter
```

This is an important difference from the current NCMemSim v0.10.0 compact parameterization.

---

## Published Urbach width

The authors extract an Urbach width for each sample.

They report an overall value:

```text
Delta_E = 10.58 ± 1.06 meV
```

and conclude that the Urbach width is constant or only weakly dependent on Sn composition and strain over the investigated sample set.

The reported individual values span approximately:

```text
9.00–12.05 meV
```

excluding the large-deviation 7% Sn sample from the reported statistics.

The mean value:

```text
10.58 ± 1.06 meV
```

is classified as:

```text
LITERATURE_FITTED
```

---

## Apparent unit typo in the publication text

In the prose describing the individual Urbach-width range, the publication prints values corresponding to:

```text
9.00
to
12.05
```

with the unit rendered as `eV`.

This is inconsistent with:

* the scale of Figure 6(b);
* the physical magnitude of the Urbach width;
* the explicit value `10.58 ± 1.06 meV`;
* Table III.

The intended unit for the individual values is therefore interpreted as:

```text
meV
```

This apparent typographical inconsistency must be documented rather than silently copied into NCMemSim.

---

# Published final near-edge absorption formula

Combining the direct absorption relation and the Urbach relation, Tran et al. give the near-band-edge absorption coefficient as a piecewise expression.

For:

```text
hν >= Eg_Gamma + Delta_E / 2
```

the direct branch is:

```text
alpha(hν) =
    A * sqrt(hν - Eg_Gamma) / hν
```

For:

```text
Eg_L <= hν <= Eg_Gamma + Delta_E / 2
```

the Urbach branch is:

```text
alpha(hν) =
    A * exp(-1/2)
    * sqrt(Delta_E / 2)
    * exp[(hν - Eg_Gamma) / Delta_E]
```

The authors derive this piecewise expression from continuity conditions
between the direct and Urbach regions. However, the published Urbach
branch in Eqs. (7) and (18) does not contain the 1/hν factor present in
the direct branch of Eq. (3). The published form must therefore be
reproduced literally and subjected to an explicit dimensional and
continuity audit before NCMemSim adopts or modifies it.

The three published parameters summarized in Table III are:

| Parameter      |                                 Value |
| -------------- | ------------------------------------: |
| `A`            | `(3.68 ± 0.86) × 10^4 cm^-1 eV^(1/2)` |
| `b_Gamma_GeSn` |                      `2.92 ± 0.11 eV` |
| `Delta_E`      |                    `10.58 ± 1.06 meV` |

These constitute the principal quantitative optical-absorption result of Tran et al. relevant to NCMemSim v0.11.0.

---

# Indirect absorption

## Experimental observation

Indirect absorption is visible in the low-energy region for lower-Sn samples.

The publication identifies contributions associated with:

* phonon absorption;
* phonon emission.

For samples with Sn composition below approximately 8%, the indirect transition can be distinguished from the direct transition and Urbach tail because the Gamma- and L-valley energies remain sufficiently separated.

At higher Sn composition, the direct and indirect conduction-band edges approach one another and the indirect feature becomes suppressed relative to the direct/Urbach response.

---

## Critical measurement limitation

The authors explicitly state that the indirect absorption coefficient is small and difficult to measure accurately using their ellipsometry method.

They note that the reliability becomes problematic particularly in the low-absorption regime.

For this reason:

```text
the indirect absorption coefficient was not included
in the final quantitative absorption formula
```

The publication further states that another technique, such as transmission measurement, would be needed to investigate indirect absorption more reliably.

---

## Consequence for NCMemSim

Tran et al. (2016) must **not** be used to calibrate:

```text
indirect_prefactor_A
```

in the current NCMemSim model.

The status of the NCMemSim indirect-absorption amplitude therefore remains:

```text
ASSUMED
```

unless and until an independent experimental dataset suitable for indirect absorption is identified and audited.

The qualitative observation of indirect absorption in Tran et al. can still be used for:

* physical sanity checks;
* regime identification;
* qualitative validation.

It cannot support a claim of quantitative indirect-absorption calibration.

---

# Comparison with the current NCMemSim v0.10.0 model

The current NCMemSim model uses the decomposition:

```text
alpha_total =
    alpha_direct
    + alpha_indirect
    + alpha_urbach
```

with provisional parameters including:

```text
direct_prefactor_A
indirect_prefactor_A
phonon_energy_eV
urbach_energy_eV
urbach_edge_alpha_m_inv
```

The Tran audit shows that these parameters cannot all be calibrated from a single publication.

The provisional mapping for v0.11.0 is therefore:

| NCMemSim quantity                | Tran support                          | Candidate status after v0.11 work                   |
| -------------------------------- | ------------------------------------- | --------------------------------------------------- |
| direct absorption amplitude/form | quantitative                          | LITERATURE_FITTED / calibrated implementation       |
| direct-gap bowing                | quantitative                          | LITERATURE_FITTED                                   |
| Urbach width                     | quantitative                          | LITERATURE_FITTED                                   |
| independent Urbach amplitude     | not independently fitted by Tran      | model architecture to review                        |
| indirect absorption amplitude    | not quantitatively reliable           | ASSUMED                                             |
| indirect phonon energy           | not established by Tran final formula | requires separate audit                             |
| strain dependence                | quantitatively relevant               | LITERATURE model / implementation decision required |
| nanocrystal correction           | not addressed                         | UNCALIBRATED                                        |

---

# Important architectural consequence

The current NCMemSim Urbach model contains an independently specified quantity:

```text
urbach_edge_alpha_m_inv
```

The Tran formulation does not require such an independent parameter.

Instead, the Urbach amplitude follows from:

```text
A
Delta_E
Eg_Gamma
```

together with continuity at the direct/Urbach connection.

Therefore v0.11.0 must explicitly decide between two approaches:

1. retain the existing generic compact Urbach parameterization and derive a Tran-equivalent parameter set for it; or
2. introduce a literature-specific calibrated absorption model that reproduces the Tran piecewise formulation directly.

This decision must be made before fitting or modifying the current runtime defaults.

No silent reinterpretation of `urbach_edge_alpha_m_inv` is acceptable.

---

# Important direct-model consequence

The Tran direct branch contains:

```text
1 / hν
```

as part of the absorption expression.

Therefore, before assigning the published `A` directly to the existing:

```text
direct_prefactor_A
```

NCMemSim implementation, the current direct-absorption equation must be compared algebraically and dimensionally with Tran Eq. (3).

The parameters must not be treated as numerically interchangeable unless the underlying expressions are equivalent.

---

# Strain consequence for v0.11.0

The original preliminary scope considered keeping strain only as experimental metadata.

The full-paper audit shows that this would not reproduce the Tran parameterization rigorously.

Strain is used to transform between measured strained bandgaps and relaxed material bandgaps and therefore affects the absorption edge directly.

Consequently, v0.11.0 must choose explicitly between:

### Option A — full Tran reconstruction

Implement the strain correction required by the Tran parameterization.

This would allow the model to calculate a strain-dependent direct gap from:

```text
Sn composition
+
strain
```

and then evaluate the published near-edge absorption formula.

### Option B — restricted relaxed-material calibration

Use the Tran relaxed-bandgap parameterization only and document that NCMemSim v0.11.0 represents the relaxed bulk-like baseline.

Experimental strained sample values would then serve for validation only after applying the published correction externally or in calibration tooling.

The choice between these options belongs to the architecture phase following F1.

It must not be hidden inside fitted optical amplitudes.

---

# Nanocrystal applicability

The Tran et al. measurements concern epitaxial GeSn thin films.

NCMemSim ultimately applies the optical material response to Ge/GeSn nanocrystals embedded in a dielectric floating-gate structure.

Therefore, even after successful implementation of the Tran parameterization, the calibrated result must be described as:

```text
bulk-like / epitaxial GeSn optical baseline
```

and not as:

```text
experimentally calibrated GeSn nanocrystal absorption
```

The Tran dataset does not establish:

* quantum-confinement corrections;
* nanocrystal-size-dependent bandgaps;
* nanocrystal-size-dependent oscillator strengths;
* dielectric-confinement effects;
* nanocrystal/matrix interface effects;
* strain states of embedded nanocrystals;
* disorder specific to embedded nanocrystals.

These effects require separate models and experimental evidence.

---

# Validity domain

The primary experimentally supported domain of this publication is:

```text
Sn composition:
0 <= x_Sn <= 0.10

spectral range discussed for the optical formula:
1500 nm <= wavelength <= 2500 nm

temperature:
room temperature
```

The full ellipsometric measurement extends to shorter wavelength, but the publication's near-IR/SWIR parameterization and discussion relevant to the present NCMemSim calibration are based on 1500–2500 nm.

Model use outside the calibration domain must be identified explicitly as extrapolation.

Examples include:

```text
x_Sn > 0.10
wavelength < 1500 nm
wavelength > 2500 nm
```

---

# Numerical data availability

The publication provides:

* complete sample metadata in Table I;
* measured/derived bandgap values with uncertainty;
* published physical equations;
* fitted direct-absorption parameter `A`;
* fitted direct-gap bowing factor;
* fitted Urbach width;
* uncertainty for the three principal Table III parameters;
* graphical absorption curves.

The article does **not** provide a numerical table containing the complete point-by-point spectral absorption coefficient for all samples.

The plotted alpha values therefore must not be represented as author-provided raw numerical data.

Before any digitization is performed, the following hierarchy remains preferred:

1. author-provided machine-readable data, if obtainable;
2. supplementary numerical data, if available;
3. direct use of the published analytical parameterization;
4. digitization of figures for independent validation only.

For the primary v0.11.0 implementation, the published analytical parameterization is preferable to digitizing curves merely to refit parameters that the authors already report.

---

# Recommended role of digitization

Digitization is **not currently required for parameter extraction** because the principal near-edge parameters are already published numerically.

Digitization may later be useful for:

* checking implementation against Figure 4;
* checking implementation against Figure 6;
* estimating residuals between the published formula and plotted Johs-Herzinger-derived points;
* producing a graphical validation benchmark.

Any digitized dataset must be labeled:

```text
DIGITIZED
```

and must store:

* publication DOI;
* figure number;
* panel identifier;
* sample identifier;
* curve identity;
* extraction tool or method;
* axis units;
* data transformations;
* estimated digitization uncertainty where possible.

Digitized data must not be called raw experimental measurements.

---

# Revised scientific scope for v0.11.0

Following the full Tran audit, the recommended scope is narrower and more rigorous than the preliminary plan.

NCMemSim v0.11.0 should establish an experimentally anchored bulk-like GeSn optical baseline based primarily on:

```text
direct absorption
+
Urbach absorption
+
direct-gap composition dependence
```

using the published Tran parameters and their uncertainties.

The release must **not** claim that Tran et al. quantitatively calibrates the indirect absorption component.

Therefore:

```text
direct component -> candidate for quantitative calibration
Urbach component -> candidate for quantitative calibration
direct-gap bowing -> candidate for quantitative calibration
indirect component -> remains provisional
eta_photo -> remains provisional
nanocrystal correction -> remains uncalibrated
```

---

# Revised calibration strategy

The preferred sequence is now:

```text
Tran publication
        |
        v
reproduce published equations
        |
        v
reproduce published parameters
        |
        v
verify dimensional conventions
        |
        v
compare against current NCMemSim model
        |
        v
implement calibrated direct + Urbach baseline
        |
        v
validate against publication figures / sample metadata
        |
        v
retain indirect term as explicitly provisional
```

This is scientifically preferable to performing a new unconstrained optimizer fit to digitized Tran curves.

A NCMemSim fitting framework may still be developed later for:

* independent datasets;
* uncertainty propagation;
* future optical datasets;
* eventual calibration of additional model components.

However, reproducing an already published physical fit should precede re-fitting the same information.

---

# F1 conclusions

The full-paper audit resolves the main questions posed at the beginning of Phase F1.

## What is experimental?

Directly experimental quantities include:

* ellipsometric measurements;
* XRD-derived strain information;
* composition and structural characterization.

## What is model-derived?

The spectral absorption coefficient used for subsequent fitting is obtained through the Johs-Herzinger optical model applied to the ellipsometry measurements.

It is therefore experimental-data-derived rather than a direct raw measurement of alpha.

## What is literature-fitted?

The principal published near-edge parameters are:

```text
A =
(3.68 ± 0.86) × 10^4 cm^-1 eV^(1/2)

b_Gamma_GeSn =
2.92 ± 0.11 eV

Delta_E =
10.58 ± 1.06 meV
```

## What cannot be calibrated from this publication?

The following cannot be quantitatively calibrated from Tran et al. alone:

```text
indirect absorption amplitude
indirect phonon-assisted absorption model
eta_photo
nanocrystal-specific absorption corrections
```

---

# Remaining F1 items

Before Phase F1 can be considered fully closed, the following items remain:

1. compare the exact Tran direct-absorption equation with the current NCMemSim implementation;
2. compare the exact Tran Urbach formulation with the current NCMemSim implementation;
3. determine whether a separate experimental source should be adopted for quantitative indirect absorption;
4. decide whether strain correction belongs in v0.11.0 runtime physics or only in calibration/reference tooling;
5. decide the software provenance categories required for `MODEL_DERIVED`, `LITERATURE_FITTED`, and `EXTRAPOLATED`;
6. establish the exact calibrated-domain semantics used by the runtime model;
7. define acceptance tests based on reproduction of the published Tran parameterization.

---

# Current audit status

```text
Status: PRIMARY SOURCE AUDIT COMPLETE
Phase F1: IN PROGRESS
```

Confirmed from the full publication:

* complete sample table;
* Sn compositions 0–10%;
* film thicknesses;
* per-sample compressive strain;
* per-sample measured direct bandgaps;
* bandgap uncertainties;
* ellipsometry MSE values;
* ellipsometry wavelength range;
* ellipsometry resolution;
* measurement angles;
* room-temperature measurement;
* Johs-Herzinger extraction workflow;
* direct-absorption equation;
* direct parameter `A`;
* direct-gap bowing factor;
* Urbach equation;
* Urbach width;
* continuity construction between Urbach and direct absorption;
* strain-correction methodology;
* deformation-potential and elastic-constant table;
* unreliability of quantitative indirect absorption from this ellipsometry dataset;
* exclusion of indirect absorption from the final quantitative absorption formula;
* lack of point-by-point numerical alpha tables in the article;
* analytical formula sufficient to reproduce the authors' principal near-edge model.

Still requiring NCMemSim-specific analysis:

* exact algebraic comparison against the current direct implementation;
* exact algebraic comparison against the current Urbach implementation;
* separate source audit for indirect absorption, if included in v0.11.0 calibration;
* architecture decision for strain;
* provenance software model;
* acceptance-test definitions.

No NCMemSim runtime parameter has yet been changed.

No v0.11.0 calibration code has yet been implemented.

No existing v0.10.0 regression test has been modified.
