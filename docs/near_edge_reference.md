# GeSn Near-Edge Reference Model

NCMemSim v0.11.0 introduces a literature-anchored near-edge optical
reference model for bulk-like Ge\(_{1-x}\)Sn\(_x\).

The model is designed to provide a quantitatively traceable optical
baseline for near-edge absorption while preserving the compact
v0.10.0 optical models unchanged.

It is implemented as:

```python
from ncmemsim.materials.optics import GeSnNearEdgeReferenceModel
```

## Scientific scope

The reference model represents:

- bulk-like GeSn;
- unstrained material;
- room-temperature conditions;
- near-edge direct and Urbach absorption;
- a literature-supported composition range up to 10% Sn;
- a literature-supported wavelength range of 1500–2500 nm.

The model must not be interpreted as an experimentally calibrated
GeSn nanocrystal absorption model.

It does not currently include:

- nanocrystal quantum-confinement corrections;
- nanocrystal-size-dependent oscillator strength;
- dielectric-confinement effects;
- nanocrystal/matrix interface effects;
- explicit strain corrections;
- field-dependent optical response;
- state filling;
- indirect absorption calibration;
- sequential optical attenuation through multi-floating-gate stacks.

## Primary literature reference

The near-edge absorption parameters are anchored to:

H. Tran et al.,
"Systematic study of Ge1-xSnx absorption coefficient and refractive
index for the device applications of Si-based optoelectronics",
*Journal of Applied Physics* **119**, 103106 (2016).

DOI:

```text
10.1063/1.4943652
```

The experimental optical coefficients reported in that work are
obtained from spectroscopic ellipsometry through an optical model.
The fitted near-edge parameters are therefore represented in NCMemSim
with the provenance status:

```text
LITERATURE_FITTED
```

rather than as direct raw experimental measurements.

## Parameter set

The default parameter set is:

```text
gesn-near-edge-tran2016-v1
```

with:

| Parameter | Value | Reported uncertainty | Provenance |
|---|---:|---:|---|
| Direct prefactor \(A\) | \(3.68\times10^6\ \mathrm{m^{-1}\ eV^{1/2}}\) | \(0.86\times10^6\ \mathrm{m^{-1}\ eV^{1/2}}\) | `LITERATURE_FITTED` |
| Urbach energy \(\Delta E\) | \(0.01058\ \mathrm{eV}\) | \(0.00106\ \mathrm{eV}\) | `LITERATURE_FITTED` |
| Reference temperature | 300 K | -- | numerical room-temperature representation |

The numerical 300 K value is the NCMemSim representation of the
room-temperature reference condition. It is not a fitted temperature
parameter from Tran et al.

## Direct optical gap

The near-edge model deliberately reuses the existing NCMemSim
direct-gap function:

```python
direct_gap_gesn_eV(sn_fraction)
```

The direct gap is therefore not duplicated inside the Tran near-edge
parameter set.

For the current unstrained 300 K parameterization,

\[
E_g^\Gamma(x)
=
(1-x)E_g^\Gamma(\mathrm{Ge})
+
xE_g^\Gamma(\alpha\text{-Sn})
-
b_\Gamma x(1-x),
\]

with the existing NCMemSim values:

\[
E_g^\Gamma(\mathrm{Ge}) = 0.7985\ \mathrm{eV},
\]

\[
E_g^\Gamma(\alpha\text{-Sn}) = -0.413\ \mathrm{eV},
\]

and

\[
b_\Gamma = 2.89\ \mathrm{eV}.
\]

The existing direct-gap parameterization remains unchanged by v0.11.0.

## Direct branch

The direct branch retains the functional form corresponding to Tran
et al. Eq. (3):

\[
\left(\alpha_D E\right)^2
=
A^2(E-E_g).
\]

Therefore,

\[
\alpha_D(E)
=
A\frac{\sqrt{E-E_g}}{E},
\qquad
E>E_g.
\]

This differs from the simpler compact v0.10.0 square-root model because
the photon-energy denominator is retained explicitly.

## Urbach branch

The low-energy branch is represented as:

\[
\alpha_U(E)
=
\alpha_0
\exp\left(
\frac{E-E_g}{\Delta E}
\right).
\]

The Urbach width \(\Delta E\) is taken from the literature fit.

The amplitude \(\alpha_0\), however, is not copied directly from the
published piecewise expression.

Instead, NCMemSim derives it from the requirement that the direct and
Urbach branches join continuously in both value and first derivative.

## NCMemSim-derived C1 connection

Let

\[
y_c = E_c-E_g.
\]

Matching the logarithmic derivatives of the two branches gives

\[
\frac{1}{2y_c}
-
\frac{1}{E_g+y_c}
=
\frac{1}{\Delta E}.
\]

The positive solution is

\[
y_c
=
\frac{
-(2E_g+\Delta E)
+
\sqrt{
(2E_g+\Delta E)^2
+
8\Delta E E_g
}
}{4}.
\]

For numerical evaluation, NCMemSim uses the algebraically equivalent
form

\[
y_c
=
\frac{
2\Delta E E_g
}{
\sqrt{
(2E_g+\Delta E)^2
+
8\Delta E E_g
}
+
(2E_g+\Delta E)
},
\]

which avoids subtractive cancellation when

\[
\Delta E \ll E_g.
\]

The connection energy is then

\[
E_c = E_g+y_c.
\]

The Urbach prefactor is derived from value continuity:

\[
\alpha_0
=
A
\frac{\sqrt{y_c}}{E_c}
\exp\left(
-\frac{y_c}{\Delta E}
\right).
\]

This connection has provenance status:

```text
DERIVED
```

because it is an analytical NCMemSim construction.

It must not be described as a literal implementation of Tran et al.
Eq. (18).

## Piecewise reference model

The resulting absorption model is

\[
\alpha(E)
=
\begin{cases}
\alpha_U(E), & E < E_c,\\
\alpha_D(E), & E \ge E_c.
\end{cases}
\]

The two branches are not added together.

The reference model therefore differs intentionally from the
v0.10.0 composite model, where direct, indirect, and Urbach
contributions are represented as separate additive components.

## No indirect calibration

The Tran et al. publication discusses indirect absorption and
phonon-assisted transitions, but the low-absorption ellipsometric data
are not sufficient to establish a quantitative indirect prefactor for
the current NCMemSim model.

Consequently, the v0.11.0 near-edge reference model does not contain an
independently calibrated indirect absorption component.

The existing v0.10.0 composite model remains available separately.

## Validation domain

The literature-supported reference domain used by NCMemSim is:

```text
0 <= Sn fraction <= 0.10
1500 nm <= wavelength <= 2500 nm
temperature: room temperature
```

The bounds are inclusive.

NCMemSim permits physically valid evaluations outside these composition
and wavelength bounds, but such evaluations are explicitly classified
as:

```text
EXTRAPOLATED
```

Evaluations inside the supported domain are classified as:

```text
WITHIN_VALIDATION_DOMAIN
```

Physically invalid values, such as negative wavelength or an Sn
fraction outside the interval 0–1, raise an error rather than being
classified as extrapolation.

## Provenance categories

The near-edge model preserves the scientific origin of each component.

| Quantity | Status |
|---|---|
| Existing direct-gap parameterization | `LITERATURE` |
| Tran direct prefactor \(A\) | `LITERATURE_FITTED` |
| Tran Urbach width \(\Delta E\) | `LITERATURE_FITTED` |
| Direct/Urbach C1 connection | `DERIVED` |

A user-supplied custom near-edge parameter set does not automatically
inherit the Tran provenance.

Parameters supplied without explicit provenance are treated
conservatively as:

```text
ASSUMED
```

## Fitting and calibration provenance

The v0.11.0 fitting workflow keeps three parameter states distinct:

```text
LITERATURE_FITTED
        ↓
independent NCMemSim optimization against a dataset
        ↓
FITTED
        ↓
explicit validation qualification
        ↓
CALIBRATED
```

`FITTED` means that NCMemSim optimized a parameter against a declared
dataset. It does not mean that the parameter has passed an independent
validation criterion.

`CALIBRATED` is created only after an explicit
`CalibrationQualification` passes every configured criterion. Promotion
constructs a new parameter set; it does not mutate the original fitted
parameter set.

Model-based fit standard errors are stored in fit diagnostics. They are
not copied into `ParameterProvenance.reported_uncertainty`, which is
reserved for source-reported uncertainty.

## Public fitting API

The GeSn-specific fitting and qualification helpers are available from
`ncmemsim.materials.optics`:

```python
from ncmemsim.materials.optics import (
    GESN_NEAR_EDGE_FIT_PARAMETER_NAMES,
    GeSnNearEdgeCalibrationResult,
    GeSnNearEdgeFitResult,
    fit_gesn_near_edge_absorption,
    predict_gesn_near_edge_absorption_m_inv,
    qualify_gesn_near_edge_fit,
)
```

The first near-edge adapter fits exactly:

```text
direct_prefactor_A
urbach_energy_eV
```

The direct-gap relation and bowing remain fixed.

## Tran 2016 digitized reference workflow

NCMemSim includes a reproducible reference workflow based on sample A
from Tran et al. Figure 6(a).

The reference package is stored under:

```text
data/reference/tran2016/
```

The source points are classified as:

```text
DIGITIZED_MODEL_DERIVED_EXPERIMENTAL_DATA
```

because the plotted absorption coefficients were derived by the authors
from spectroscopic ellipsometry through the Johs-Herzinger optical model
and were subsequently digitized from the published figure by NCMemSim.

The selected near-edge dataset contains eight digitized points. They are
split into four fitting points and four disjoint holdout points. The
holdout is from the same published curve and is therefore **not an
independent experiment**.

A 5% pointwise absorption uncertainty is assigned as a conservative
NCMemSim digitization estimate. It must not be described as an
experimental uncertainty reported by Tran et al.

The highest-energy digitized marker corresponds to approximately
1499.7 nm. This is treated as a boundary-level digitization effect near
the nominal 1500 nm literature boundary and does not extend the
literature-supported domain below 1500 nm.

## Reference workflow result

The reproducible workflow is:

```text
examples/phase_f4f_tran2016_calibration.py
```

with its serialized result at:

```text
data/reference/tran2016/tran2016_sampleA_fig6a_workflow_result.json
```

The direct gap remains fixed to the existing NCMemSim relation. For
sample A, the current pure-Ge endpoint is \(0.7985\) eV, while the Tran
table reports \(0.805\pm0.037\) eV for that sample.

The deterministic fit converges to:

| Quantity | Fitted result | Tran literature central value |
|---|---:|---:|
| \(A\) | \(2.417634\times10^6\ \mathrm{m^{-1}\ eV^{1/2}}\) | \(3.68\times10^6\ \mathrm{m^{-1}\ eV^{1/2}}\) |
| \(\Delta E\) | \(8.63322\ \mathrm{meV}\) | \(10.58\ \mathrm{meV}\) |

The fitted \(A\) is approximately 34.3% below the Tran central value,
and the fitted \(\Delta E\) is approximately 18.4% below the Tran
central value.

Local fit diagnostics are:

| Diagnostic | Value |
|---|---:|
| Jacobian rank | 2 / 2 |
| Scaled condition number | 3.6539 |
| Correlation \(A,\Delta E\) | -0.5052 |
| Standard error of \(A\) | \(2.87166\times10^5\ \mathrm{m^{-1}\ eV^{1/2}}\) |
| Standard error of \(\Delta E\) | \(2.19894\ \mathrm{meV}\) |

The fit is therefore locally identifiable under the implemented
linearized diagnostic.

Qualification is based on a validation RMSE threshold derived before
model evaluation from the assigned digitization uncertainties:

\[
\mathrm{RMSE}_{\max}
=
\sqrt{
\frac{1}{N}
\sum_i \sigma_i^2
}.
\]

For the holdout dataset:

| Validation quantity | Value |
|---|---:|
| RMSE | \(44\,978.9\ \mathrm{m^{-1}}\) |
| MAE | \(31\,598.1\ \mathrm{m^{-1}}\) |
| \(R^2\) | 0.94096 |
| Predeclared RMSE threshold | \(15\,747.6\ \mathrm{m^{-1}}\) |

The validation RMSE is approximately 2.86 times the threshold.
Consequently, the qualification fails `validation_rmse` and the
workflow reports:

```text
NOT_CALIBRATED
```

No calibrated parameter set is created.

A good \(R^2\) does not override the failed absolute-error criterion.
The negative qualification result is intentionally preserved rather
than weakening the threshold after observing the result.

Possible contributors to the residual mismatch include the restricted
two-parameter model, the fixed direct-gap relation, the NCMemSim-derived
C1 branch connection, digitization uncertainty, and the small number of
points. The current workflow does not isolate which contribution
dominates.

## Public reference-model API

The main reference-model objects are available from:

```python
from ncmemsim.materials.optics import (
    EvaluationDomainStatus,
    GeSnNearEdgeParameterSet,
    GeSnNearEdgeReferenceModel,
    NearEdgeBranch,
    NearEdgeOpticalPoint,
    OpticalValidationDomain,
    TRAN_2016_NEAR_EDGE_DOMAIN,
    TRAN_2016_NEAR_EDGE_PARAMETERS,
)
```

A minimal evaluation is:

```python
from ncmemsim import make_gesn
from ncmemsim.materials.optics import GeSnNearEdgeReferenceModel

material = make_gesn(0.05)
model = GeSnNearEdgeReferenceModel()

point = model.evaluate(
    material,
    wavelength_nm=2000.0,
)

print(point.direct_gap_eV)
print(point.connection_energy_eV)
print(point.absorption_coefficient_m_inv)
print(point.branch.value)
print(point.domain_status.value)
```

## Interpretation

The v0.11.0 near-edge model should be described as a:

> bulk-like, unstrained, room-temperature,
> literature-anchored GeSn near-edge reference model

It should not be described as:

> experimentally calibrated GeSn nanocrystal absorption

without additional nanocrystal-specific experimental evidence.

The first digitized Tran reference workflow also does not justify such a
claim: its explicit qualification result is `NOT_CALIBRATED`.

The model establishes a traceable optical baseline upon which future
strain, confinement, field-dependent, and nanocrystal-specific models
can be built.
