# Reproducibility, validation, and benchmarking

NCMemSim v0.10.0 treats reproducibility as part of the scientific model rather
than as a post-processing task.

A reproducible result should preserve enough information to reconstruct:

```text
software version
+
device definition
+
material models
+
initial state
+
simulation settings
+
electrical conditions
+
optical conditions
+
photo-transition configuration
+
parameter provenance
+
calibration status
+
raw numerical outputs
```

Reproducing numerical inputs does not by itself establish that the physical
model is experimentally valid.

## Reproducibility manifest

`build_reproducibility_manifest()` creates a structured record of the software
and simulation environment.

The manifest can record information including:

- NCMemSim version;
- Git commit when available;
- Python version;
- NumPy version;
- platform and runtime information;
- deterministic device hash;
- deterministic simulation hash;
- random seed;
- material-model identifiers;
- caller-supplied metadata.

A typical call is:

```python
from ncmemsim import build_reproducibility_manifest

manifest = build_reproducibility_manifest(
    device,
    simulation_config={
        "gate_voltage_V": 2.0,
        "dwell_time_s": 1e-3,
    },
)
```

Save the manifest beside the numerical data that it describes.

A hash establishes identity of serialized inputs.

It does not prove that:

- the selected physical model is complete;
- the parameters are experimentally correct;
- the simulation is calibrated to a fabricated device.

## Device reproducibility

The complete device description should be preserved.

For floating-gate nanocrystal memories this includes quantities such as:

- ordered layer structure;
- layer thicknesses;
- dielectric constants;
- floating-gate positions;
- nanocrystal material;
- nanocrystal diameter;
- floating-gate thickness;
- nanocrystal volume fraction where applicable;
- electrically active fraction;
- device temperature;
- relevant material and interface parameters.

For multi-FG devices, per-FG values must be preserved rather than replacing
them with only a global average.

## State reproducibility

A complete transient study also depends on its initial `DeviceState`.

For every floating gate, the state contains distributed probabilities:

```text
P0
P1
P2
```

A scalar total charge is generally not sufficient to reconstruct a multi-FG
state.

For workflows in which the initial occupation is scientifically important,
preserve either:

- the complete initial state;
- the script that deterministically constructs it;
- or a validated serialized representation.

## Simulation configuration

Record all numerical inputs capable of changing a result.

Typical examples include:

```text
gate voltage
dwell time
internal timestep
voltage grid
retention duration
retention timestep settings
C-V range
C-V point count
temperature
fixed charge
interface charge
```

A simulation configuration should not rely on undocumented local defaults when
the result is intended for publication or long-term comparison.

## Timestep reproducibility

The requested dwell interval and the internal timestep are separate quantities.

NCMemSim subdivides the requested dwell interval and uses an effective
integration timestep that spans that interval exactly.

Therefore reproducible transient work should record both:

```text
dwell_time_s
internal_dt_s
```

Numerical results can change when timestep semantics change even if all physical
parameters remain identical.

Such changes should be treated as numerical-model changes rather than cosmetic
implementation details.

## Material-model provenance

Material parameters should preserve provenance whenever possible.

For each important parameter, record:

- numerical value;
- unit;
- source or citation;
- interpolation or composition model;
- temperature range;
- composition range;
- strain assumptions where relevant;
- whether the parameter is literature-supported, provisional, fitted, or
  experimentally calibrated;
- uncertainty when available.

A material name alone is not always sufficient to reproduce a scientific
result.

## Optical reproducibility

Optical studies require additional configuration beyond the electrical device
definition.

A reproducible optical dataset should preserve, where relevant:

```text
source type
wavelength
optical power density
photon-flux convention
Ge or GeSn composition
optical parameter set
absorption parameter set
temperature
nanocrystal volume fraction
floating-gate thickness
photo-capture efficiency
photo-transition weights
```

The optical source should be reconstructable from the recorded parameters.

For example:

```python
from ncmemsim.optics import LightSource

light = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

The corresponding configuration should be saved together with the generated
data.

## Photo-transition reproducibility

Photo-assisted kinetics are configured separately from the optical source.

For example:

```python
from ncmemsim.photo import (
    PhotoTransitionConfig,
    PhotoTransitionWeights,
)

photo_config = PhotoTransitionConfig(
    photo_capture_efficiency=1e-7,
)

photo_weights = PhotoTransitionWeights(
    r01=1.0,
    r12=1.0,
    r10=0.0,
    r21=0.0,
)
```

A publication or benchmark using non-default photo-transition settings should
record them explicitly.

In particular, `photo_capture_efficiency` must not be omitted from the
reproducibility record when it influences the result.

## Electrical and optical configuration should be separated

A useful reproducibility structure is:

```text
device configuration
electrical simulation configuration
optical source configuration
photo-transition configuration
material provenance
```

rather than combining all parameters into an undocumented flat dictionary.

This separation mirrors the physical architecture and makes it easier to
identify which part of a simulation changed.

## Benchmark-specific parameters

A benchmark may deliberately use parameters selected for numerical comparison
rather than experimental calibration.

Such parameters must be labelled explicitly.

The Phase E6 voltage-reduction benchmark, for example, uses:

```text
photo_capture_efficiency = 1e-10
```

to place dark and illuminated programming curves in a common occupation range.

This value is benchmark-specific.

It is not the global model default and is not experimentally calibrated.

Reproducing the benchmark therefore requires preserving this value exactly.

## Spectral reproducibility

A wavelength sweep should preserve both the swept variable and the quantities
held fixed.

At minimum, record:

- wavelength grid;
- optical power density;
- material composition;
- optical parameter set;
- temperature;
- geometry;
- photo-capture efficiency;
- photo-transition weights.

At fixed optical power density, photon flux varies with wavelength.

Therefore two spectral runs are not equivalent merely because they use the
same optical power density.

## Composition-sweep reproducibility

A GeSn composition sweep should record:

- Sn fraction;
- wavelength;
- temperature;
- direct-gap model;
- indirect-gap model;
- absorption parameter set;
- spectral applicability range;
- composition applicability range.

If part of the sweep lies outside the range supported by the reference
literature or experiment, that region should be marked as extrapolation.

## Extrapolation status

Reproducibility requires preserving not only numerical values but also the
interpretation attached to those values.

A result should therefore state when it is extrapolated with respect to:

- composition;
- wavelength;
- temperature;
- strain state;
- device geometry;
- model applicability range.

An exactly reproducible extrapolation is still an extrapolation.

## Calibration status

NCMemSim distinguishes among:

```text
literature-supported
provisional
fitted
experimentally calibrated
```

These categories should be preserved in the scientific record.

For example, the v0.10.0 optical framework contains literature-supported model
structure together with provisional compact absorption amplitudes and
photo-capture coupling.

A later fitted parameter set should not silently replace the status of the
default model.

## Experimental fitting records

When parameters are fitted to measured data, preserve:

- dataset identifier;
- sample or device identifier;
- measurement conditions;
- temperature;
- wavelength range if optical;
- voltage range if electrical;
- fitted parameters;
- parameter bounds;
- objective function;
- optimization method;
- initialization;
- stopping criteria;
- uncertainty or confidence information where available;
- NCMemSim version;
- Git commit.

The fitted values should remain traceable to the dataset from which they were
obtained.

## Validation reports

The validation API returns `ValidationReport` objects containing structured
`ValidationIssue` entries.

Checks include areas such as:

- probability normalization;
- probability bounds;
- device and material consistency;
- field-profile consistency;
- internal charge conservation;
- simulation-output structure.

For optical workflows, the automated test suite additionally checks properties
such as:

- non-negative absorption;
- non-negative photon rates;
- zero photo contribution in dark simulations;
- consistent electrical/photo rate combination;
- probability normalization under electro-optical programming;
- expected spectral ordering in validated benchmark cases.

Validation is intentionally separate from execution.

A simulation can therefore be executed and then inspected for warnings or
errors through the validation layer.

## Validation is not experimental calibration

Passing validation means that the result satisfies the implemented software and
model-consistency checks.

It does not establish agreement with experimental data.

For scientific reporting, distinguish:

```text
software verification
physical consistency
numerical regression
experimental validation
```

These are complementary but different forms of evidence.

## Golden references

`build_golden_suite()` provides deterministic regression cases for the
electrical baseline.

The retained golden set includes:

- a one-FG V2 device;
- a two-FG V2 device;
- a three-FG V2 device;
- a short retention trajectory.

`compare_golden()` detects numerical drift against those stored values.

Golden references are regression anchors.

They are not experimental measurements.

## Historical golden baseline

The existing Phase D golden data remain intentionally preserved as the
electrical regression baseline.

Their historical file naming should not be interpreted as meaning that the
current software release is still v0.9.x.

NCMemSim v0.10.0 extends that retained electrical baseline with the Phase E
optical-programming test suite.

## Changing golden data

Golden data should only change after a reviewed physical or numerical
modification.

A changed result should first be classified as one of:

- intended physical-model change;
- numerical correction;
- bug fix;
- API or data-structure change;
- unintended regression.

Do not regenerate golden data simply to make a failing test pass.

The reason for an accepted golden change should be documented.

## Benchmarks

`benchmark_case()` and `run_benchmark_suite()` provide deterministic
performance-oriented measurements.

Typical benchmark quantities include:

- execution time;
- traced peak memory;
- selected physical outputs such as floating-gate charge.

Performance measurements depend on:

- Python version;
- NumPy version;
- operating system;
- hardware;
- runtime environment.

They are therefore most useful for regression monitoring.

They should not be treated as portable absolute performance guarantees across
different systems.

## Scientific benchmarks

A scientific benchmark is different from a performance benchmark.

A scientific benchmark should preserve:

- complete device definition;
- physical parameters;
- numerical settings;
- target metric;
- comparison method;
- calibration status.

The v0.10.0 SWIR voltage-reduction example is a scientific benchmark.

Its verified values demonstrate internal consistency of the compact
electro-optical model.

They should not be interpreted as experimentally calibrated device predictions.

## Raw-data preservation

For publication-oriented work, save raw numerical results before creating
plots.

A preferred workflow is:

```text
simulation
    |
    v
validation
    |
    v
raw data
    |
    v
manifest
    |
    v
figure
```

The figure should be reproducible from stored numerical data without rerunning
an undocumented simulation.

## Recommended files for a published result

A reproducibility package for a figure or table should ideally contain:

```text
input configuration
raw numerical data
reproducibility manifest
parameter provenance
calibration notes
analysis script
plotting script
software version / Git commit
```

For optical studies, also include the light-source and photo-transition
configuration.

## Recommended evidence hierarchy

A defensible scientific result should distinguish at least four levels:

1. **code correctness** — unit tests and software invariants;
2. **numerical regression** — agreement with approved deterministic baselines;
3. **physical consistency** — limiting cases, conservation, and physically
   meaningful trends;
4. **experimental validity** — comparison with appropriate measured data.

NCMemSim v0.10.0 provides extensive support for the first three.

Experimental validity remains dependent on the specific material, sample,
device, and dataset.

## v0.10.0 verification baseline

The official v0.10.0 release baseline contains:

```text
194 passed
```

The repository CI matrix covers:

```text
Python 3.11
Python 3.12
Python 3.13
```

The suite spans the original electrical framework and the Phase E optical
extension.

Phase E includes tests for:

- optical sources;
- Ge/GeSn optical-material response;
- floating-gate optical absorption;
- absorbed photon generation;
- photo-assisted transition rates;
- electrical/photo rate coupling;
- electro-optical programming;
- optical simulator diagnostics;
- optical voltage sweeps;
- optical C-V integration;
- SWIR wavelength behaviour;
- SWIR programming;
- SWIR programming-voltage reduction.

## Reproducing repository checks

The complete automated suite can be run from the repository root with:

```bash
python -m pytest -q
```

Golden and performance artifacts are maintainer operations:

```bash
python scripts/generate_golden.py
python scripts/run_benchmarks.py
```

Generated golden artifacts should be reviewed before replacing an accepted
reference.

A numerical difference is evidence of changed behaviour, not automatically
evidence of improvement.

## Documentation reproducibility

Documentation is part of the release record because it defines the intended
interpretation of the model.

The final documentation check is:

```bash
python -m mkdocs build --strict
```

For the current documentation audit, this strict build can be performed once
after the Markdown sources have been reviewed, rather than after every file
edit.

Generated files under `site/` should not be treated as source documentation.

## Reproducibility versus correctness

It is possible to reproduce an incorrect model exactly.

Therefore NCMemSim treats these as separate questions:

```text
Can the result be reproduced?
Is the numerical implementation internally consistent?
Is the physical model appropriate?
Is the model calibrated to experiment?
```

A strong scientific result should answer all applicable questions explicitly.

## Recommended reporting language

For v0.10.0 optical studies, language such as the following is appropriate:

```text
The simulation was reproduced using NCMemSim v0.10.0 with the recorded device,
material, optical-source, photo-transition, and numerical configurations.
The reported result is software verified within the implemented compact model.
Unless separately stated, the absolute optical absorption amplitudes and
photo-capture coupling are not device-specifically experimentally calibrated.
```

This wording keeps software reproducibility distinct from experimental
predictive accuracy.

## Where to go next

For related information, see:

- [Scientific workflows](workflows.md) for end-to-end study organization;
- [Validation](validation.md) for the validation framework;
- [Verification and Validation Report](Validation_Report.md) for the v0.10.0
  verification baseline;
- [Materials and provenance](materials.md) for parameter status;
- [Optical programming](optics.md) for optical-model assumptions;
- [Developer guide](developer.md) for rules governing new physical models.
