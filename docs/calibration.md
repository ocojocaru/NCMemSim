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


## Device-level fitting and pulse protocols

The v0.11.0 development branch now includes controlled device-level parameter
bindings and synthetic end-to-end fitting references for electrical
observables.

Implemented reference workflows include:

- single-parameter C–V fitting with `qfix_C_m2`;
- explicit fixed-voltage program pulses followed by zero-dwell
  \(\Delta V_\mathrm{FB}\) readout;
- single-parameter \(\Delta V_\mathrm{FB}(t_\mathrm{prog})\) fitting with
  `nu0_Hz`;
- independent program and erase branches defining a pulse-based memory
  window.

The device-level workflows preserve the same provenance rule used by the
optical calibration layer: successful numerical recovery produces `FITTED`,
not `CALIBRATED`.

Two memory-window definitions are now intentionally separate:

```text
CVResult.memory_window_V
    = forward/backward dynamic C–V hysteresis

PairedPulseMemoryResult.memory_window_V
    = ΔVFB_programmed - ΔVFB_erased
```

`SimulationConfig.dwell_time_s` remains the default per-voltage relaxation
time used by sweeps. It is not the program-pulse duration of the explicit
pulse protocol.

See [Device-level calibration and pulse protocols](device_calibration.md) for
the parameter-binding policy, protocol semantics, implemented workflows, and
current limitations.


### Retention-fraction fitting

The F4h2c2 workflow adds an end-to-end single-parameter fit for
`total_charge_retention_fraction` versus physical time. The production API is
implemented in `ncmemsim.retention_fit` and uses the existing F4g retention
objective adapter rather than a separate fitting-only observable definition.

The workflow requires:

- a caller-supplied `DeviceState` as the retention initial condition;
- an explicit `RetentionFitProtocol` containing the `RetentionConfig`;
- `occupancy_integrator="backward_euler"`;
- `stop_at_quasi_equilibrium=False`, so the declared simulation domain is
  always available to the objective adapter;
- exactly one free parameter in the `DeviceCalibrationSpec`;
- exact matching of the dataset `retention_gate_voltage` condition;
- linear interpolation in physical time;
- no extrapolation beyond the simulated retention interval.

The initial occupation state and protocol are serialized and hashed. Local
field and potential diagnostics are intentionally excluded from the initial
state identity because they are recomputed self-consistently at the retention
bias.

The synthetic reference benchmark uses a pure-P2 initial state and fits the
FG0 effective erase barrier:

```text
observable                 total_charge_retention_fraction
retention gate voltage     -14 V
truth phi_barrier_erase    2.10 eV
fit interval               1e-4 to 3e-2 s
free parameter             FG_PHI_BARRIER_ERASE_EV
scientific status          FITTED
```

The negative gate bias is a deliberately accelerated constant-bias synthetic
identifiability benchmark. It must not be described as representative
zero-bias data retention.

## Numerical refinement of the synthetic retention benchmark

The accelerated fixed-bias retention benchmark was audited separately for
maximum-timestep and output-grid sensitivity. The original coarse
`maximum_dt_s = 1e-3` / `output_points = 81` configuration is not used as the
numerically justified reference for this transition.

A high-resolution numerical audit used:

```text
maximum_dt_s = 1e-7 s
output_points = 5001
```

This high-resolution run is a **numerical reference**, not physical truth and
not experimental calibration. Cross-grid fitting of that reference with the
selected practical example grid,

```text
maximum_dt_s = 1e-5 s
output_points = 321
```

recovered `phi_barrier_erase_eV = 2.099668909 eV` from the synthetic truth
`2.10 eV`, corresponding to an absolute bias of approximately
`-3.31e-4 eV` (`-0.0158%`) and an objective RMSE of approximately
`2.79e-5`.

The selected practical grid is specific to this accelerated synthetic
benchmark. It is not a universal retention timestep or output-grid default.
Same-grid exact recovery remains a workflow regression check and must not be
interpreted as a numerical-convergence result.

The numerical audit can be reproduced with:

- `examples/phase_f4h_retention_timestep_convergence.py`, which establishes
  timestep stabilization using a fixed dense output grid;
- `examples/phase_f4h_retention_practical_grid.py`, which measures cross-grid
  parameter bias and runtime to select the practical benchmark grid.

`phi_barrier_erase_eV` is an **effective compact-model parameter**. In the
current kinetics it controls the erase tunnelling transmission used by both
escape channels and can be strongly correlated with `nu1_Hz`, `nu2_Hz`, and
other tunnelling quantities. The single-parameter benchmark therefore tests
numerical recovery under a fixed model and protocol; it does not establish a
unique microscopic barrier value.

Successful synthetic recovery remains `FITTED`, not `CALIBRATED`. Promotion to
`CALIBRATED` would require a separate experimental validation dataset and
explicit calibration qualification.

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
tran2016_sampleA_fig6a_validation.csv
tran2016_sampleA_fig6a_workflow_result.json
```

A verification overlay derived from the publication figure was used
locally during digitization QA but is intentionally not redistributed.

The metadata records source identity, digitization calibration, split
policy, limitations, and SHA-256 hashes for the reference artifacts.
