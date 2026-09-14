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
- a literature-supported wavelength range of 1500--2500 nm.

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
fraction outside the interval 0--1, raise an error rather than being
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

## Public API

The main public objects are available from:

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

The model establishes a traceable optical baseline upon which future
strain, confinement, field-dependent, and nanocrystal-specific models
can be built.
