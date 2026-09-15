# Experimental Fitting and Calibration

NCMemSim v0.11.0 separates parameter fitting from calibration
qualification.

A numerical optimizer can converge successfully without establishing
that a model is experimentally calibrated. The software therefore uses
different provenance states and an explicit validation step.

## Calibration philosophy

The core sequence is:

```text
experimental dataset
        ↓
objective + parameter specification
        ↓
deterministic fitting
        ↓
FITTED parameter set
        ↓
uncertainty + identifiability diagnostics
        ↓
validation dataset
        ↓
explicit CalibrationCriteria
        ↓
CalibrationQualification
        ↓
CALIBRATED only if every criterion passes
```

The distinction is intentional:

- `LITERATURE_FITTED` identifies parameters fitted in a cited source;
- `FITTED` identifies parameters optimized by an NCMemSim workflow;
- `CALIBRATED` requires both fitting and explicit validation
  qualification.

A failed qualification is retained as a scientific result. Thresholds
must not be weakened after observing a result merely to obtain the
`CALIBRATED` label.

## Experimental optical datasets

The first implemented experimental dataset type is
`OpticalAbsorptionDataset`.

```python
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
```

Canonical quantities are:

- wavelength in nm;
- absorption coefficient in \(\mathrm{m^{-1}}\);
- Sn fraction as a dimensionless composition;
- optional pointwise absorption uncertainty in \(\mathrm{m^{-1}}\);
- source, DOI, sample, temperature, and notes metadata.

The CSV loader is:

```python
from ncmemsim.io import load_optical_absorption_csv
```

The accepted optical columns are:

```text
wavelength_nm
absorption_coefficient_m_inv
absorption_uncertainty_m_inv
```

The uncertainty column is optional.

Dataset serialization and hashes use canonical values so a dataset can
be traced through later fit and qualification results.

## Objective functions

For observed values \(y_i\) and predictions \(\hat y_i\), the raw
residual is

\[
r_i = \hat y_i-y_i.
\]

When pointwise uncertainties \(\sigma_i\) are supplied, the optimization
residual is

\[
r_i^{(w)}
=
\frac{\hat y_i-y_i}{\sigma_i}.
\]

NCMemSim retains raw observable-space metrics such as RMSE, MAE, and
\(R^2\) in addition to the weighted least-squares objective.

This distinction matters because a weighted optimizer minimizes
normalized residuals, not necessarily the unweighted raw RMSE.

## Fit parameters and deterministic fitting

Fit parameters are declared explicitly:

```python
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
)
```

Each parameter carries:

- name;
- initial value;
- lower and upper bounds;
- optional unit;
- optional description.

The deterministic fitting runner normalizes each bounded parameter to a
unit interval before calling SciPy least squares. This prevents raw
parameter units from dominating the optimizer scaling.

The base NCMemSim runtime remains NumPy-only. SciPy is required only for
the optional fitting capability.

## Local uncertainty and identifiability

After a successful deterministic fit, NCMemSim can evaluate local
linearized diagnostics:

```python
from ncmemsim.fit_diagnostics import (
    FitUncertaintyDiagnostics,
    analyze_fit_uncertainty,
)
```

The diagnostics include:

- Jacobian rank;
- singular values after bound scaling;
- scaled condition number;
- covariance matrix when estimable;
- parameter standard errors;
- correlation matrix;
- active-bound count;
- local-identifiability flag.

`locally_identifiable=True` means only that the local Jacobian has full
column rank. It does not establish global identifiability or uniqueness
of the physical model.

The standard errors are model-based fit estimates. They are not copied
into source-reported provenance uncertainty fields.

## Calibration criteria

Calibration qualification is configured with:

```python
from ncmemsim.calibration import CalibrationCriteria
```

Available requirements include:

- maximum validation RMSE;
- maximum validation MAE;
- minimum validation \(R^2\);
- maximum scaled condition number;
- distinct validation-dataset hash;
- local identifiability;
- covariance availability.

At least one quantitative validation threshold is required. Optimizer
convergence alone is therefore never sufficient for calibration.

A qualification result records the observed quantities, thresholds,
pass/fail state, failed criteria, and reproducibility hashes.

## Distinct dataset versus independent experiment

`require_distinct_validation_dataset=True` compares dataset hashes.

Two disjoint subsets from the same published experimental curve can
therefore satisfy the software requirement for distinct datasets while
still **not** being independent experiments.

Scientific metadata must preserve that distinction.

The first Tran reference workflow explicitly records:

```text
validation_type = holdout_from_same_published_curve
independent_experiment = false
```

## GeSn near-edge fitting adapter

The GeSn adapter is available from:

```python
from ncmemsim.materials.optics import (
    fit_gesn_near_edge_absorption,
    qualify_gesn_near_edge_fit,
)
```

It fits exactly:

```text
direct_prefactor_A
urbach_energy_eV
```

The direct-gap composition relation and bowing are fixed.

A successful fit constructs a separate
`GeSnNearEdgeParameterSet` with `FITTED` provenance for those two fitted
parameters.

The Tran literature reference set
`gesn-near-edge-tran2016-v1` remains unchanged.

## Promotion to CALIBRATED

`qualify_gesn_near_edge_fit()` evaluates the fitted model against the
declared validation dataset without re-fitting.

If every criterion passes, a **new** parameter-set identity is required
and a new `GeSnNearEdgeParameterSet` is constructed with
`ParameterStatus.CALIBRATED` for the fitted parameters.

If any criterion fails:

- qualification remains fully serialized and auditable;
- no calibrated parameter set is created;
- the original `FITTED` parameter set remains unchanged.

## Tran 2016 reference data

The first real-data workflow uses H. Tran et al.,
*J. Appl. Phys.* **119**, 103106 (2016),
DOI `10.1063/1.4943652`.

The reference package is:

```text
data/reference/tran2016/
```

The selected source is sample A from Figure 6(a):

```text
material: Ge
Sn fraction: 0
reported in-plane strain: 0
film thickness: 300 nm
temperature: room temperature
reported direct gap: 0.805 ± 0.037 eV
```

The published absorption symbols are not raw ellipsometric observables.
The paper derives absorption coefficients from spectroscopic
ellipsometry using the Johs-Herzinger optical model.

NCMemSim therefore classifies the digitized values as:

```text
DIGITIZED_MODEL_DERIVED_EXPERIMENTAL_DATA
```

The lineage is:

```text
spectroscopic ellipsometry
→ Johs-Herzinger optical-model extraction
→ published Figure 6(a) symbols
→ NCMemSim digitization
```

## Digitization and split policy

Eight near-edge markers are retained.

Three additional lower-energy detected markers are preserved in the
digitization audit but excluded because the indirect-absorption region
contaminates the low-energy branch.

The eight selected points are divided deterministically into:

```text
4 fitting points
4 holdout-validation points
```

The split alternates points in ascending photon energy.

The validation subset is therefore disjoint but comes from the same
published curve.

A 5% pointwise absorption uncertainty is assigned as a conservative
digitization uncertainty. It is an NCMemSim estimate, not an
experimental standard deviation reported by Tran et al.

The highest-energy marker digitizes to approximately 1499.7 nm. This is
treated as a boundary-level digitization effect around the nominal
1500 nm literature boundary and does not extend the validated literature
domain below 1500 nm.

## Reproducible workflow

The reference workflow is:

```text
examples/phase_f4f_tran2016_calibration.py
```

It can be run with:

```bash
python examples/phase_f4f_tran2016_calibration.py \
    --output data/reference/tran2016/tran2016_sampleA_fig6a_workflow_result.json
```

The workflow records:

- fit and validation dataset hashes;
- fit parameter specification and hash;
- fitted values;
- objective metrics;
- uncertainty and identifiability diagnostics;
- calibration criteria and hash;
- qualification hash;
- scientific scope and validation type;
- final scientific conclusion.

## Parameter specification

The initial values are the Tran literature-fit central values:

| Parameter | Initial value | Fit bounds |
|---|---:|---:|
| \(A\) | \(3.68\times10^6\ \mathrm{m^{-1}\ eV^{1/2}}\) | \(1.0\times10^6\) to \(7.0\times10^6\) |
| \(\Delta E\) | \(0.01058\ \mathrm{eV}\) | 0.005 to 0.020 eV |

The bounds are numerical/physical search bounds. They are not literature
confidence intervals.

The direct gap is not fitted. The workflow uses the existing NCMemSim
direct-gap relation unchanged.

For pure Ge this relation gives:

\[
E_g^\Gamma = 0.7985\ \mathrm{eV}.
\]

The Tran sample-A table reports:

\[
E_g^\Gamma = 0.805\pm0.037\ \mathrm{eV}.
\]

The difference between the central values is 6.5 meV and lies within the
reported Tran uncertainty.

## Fitted result

The deterministic fit converges successfully to:

\[
A
=
2.417634\times10^6\
\mathrm{m^{-1}\ eV^{1/2}},
\]

and

\[
\Delta E
=
0.00863322\ \mathrm{eV}.
\]

Relative to the Tran central values:

- fitted \(A\) is approximately 34.3% lower;
- fitted \(\Delta E\) is approximately 18.4% lower.

The fitted parameter set remains `FITTED`.

## Fit diagnostics

The local diagnostics are:

| Quantity | Result |
|---|---:|
| Jacobian rank | 2 / 2 |
| Degrees of freedom | 2 |
| Scaled condition number | 3.6539 |
| Parameter correlation | -0.5052 |
| Standard error of \(A\) | \(2.87166\times10^5\ \mathrm{m^{-1}\ eV^{1/2}}\) |
| Standard error of \(\Delta E\) | \(0.00219894\ \mathrm{eV}\) |

The Jacobian is full rank and covariance is available, so the fit is
classified as locally identifiable.

This does not establish global identifiability.

## Predeclared qualification threshold

The reference workflow derives the validation RMSE threshold from the
assigned pointwise digitization uncertainties before evaluating the
validation predictions:

\[
\mathrm{RMSE}_{\max}
=
\sqrt{
\frac{1}{N}
\sum_i \sigma_i^2
}.
\]

For the four holdout points:

\[
\mathrm{RMSE}_{\max}
=
15\,747.6\ \mathrm{m^{-1}}.
\]

This threshold is not tuned after seeing the validation residuals.

## Validation result

The holdout metrics are:

| Metric | Result |
|---|---:|
| RMSE | \(44\,978.9\ \mathrm{m^{-1}}\) |
| MAE | \(31\,598.1\ \mathrm{m^{-1}}\) |
| \(R^2\) | 0.94096 |
| RMSE threshold | \(15\,747.6\ \mathrm{m^{-1}}\) |

The observed RMSE is approximately:

\[
\frac{44\,978.9}{15\,747.6}
\approx
2.86
\]

times the predeclared threshold.

The only failed qualification criterion is:

```text
validation_rmse
```

The scientific conclusion is therefore:

```text
NOT_CALIBRATED
```

No calibrated near-edge parameter set is created.

## Interpretation

The workflow demonstrates several distinct facts:

1. the deterministic optimizer converges;
2. the fitted two-parameter model is locally identifiable;
3. the holdout trend has a high \(R^2\);
4. the absolute holdout error is nevertheless too large relative to the
   declared digitization uncertainty;
5. the model therefore fails the explicit calibration criterion.

A high \(R^2\) is not sufficient to establish calibration.

The mismatch may reflect more than one source, including:

- the restricted two-parameter model;
- the fixed direct-gap relation;
- the NCMemSim-derived C1 direct/Urbach connection;
- digitization error;
- the small number of published points available from the figure.

The present workflow does not determine which source dominates.

Because the holdout comes from the same published curve, even a future
passing result would need to be described as holdout qualification, not
as independent experimental replication.

## What is not calibrated

The current result does **not** calibrate:

- nanocrystal confinement;
- dielectric confinement;
- size-dependent oscillator strength;
- strain corrections;
- indirect absorption;
- field-dependent absorption;
- state filling;
- full-stack optical propagation;
- photo-capture efficiency;
- photo-assisted device kinetics.

In particular, `photo_capture_efficiency` is a device-level kinetics
parameter and should be fitted against device-level observables rather
than material absorption data.

## Reproducibility assets

The reference directory contains:

```text
README.md
tran2016_sampleA_fig6a_digitization_audit.csv
tran2016_sampleA_fig6a_fit.csv
tran2016_sampleA_fig6a_metadata.json
tran2016_sampleA_fig6a_near_edge_all.csv
tran2016_sampleA_fig6a_overlay.png
tran2016_sampleA_fig6a_validation.csv
tran2016_sampleA_fig6a_workflow_result.json
```

The metadata records source identity, digitization calibration, split
policy, limitations, and SHA-256 hashes for the reference artifacts.
