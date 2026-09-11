# Developer guide

This guide describes the development conventions for NCMemSim v0.10.0 and the
requirements for extending the simulator without losing physical traceability,
numerical reproducibility, or regression stability.

NCMemSim is research software. A new physical capability is therefore not
complete when the code merely runs: its assumptions, parameter provenance,
numerical behaviour, validation scope, and compatibility impact must also be
documented.

## Repository layout

```text
ncmemsim/          Python package
  materials/       electronic and optical material models
    optics/        Ge/GeSn optical-material models
  transport/       node/link transport engine
  optics.py        optical-source and FG absorption workflow
  photo.py         photo-assisted transition model

examples/          executable scientific examples
configs/           serialized device examples
scripts/           golden, benchmark, and reproduction utilities
tests/             unit, integration, and regression tests
validation/        validation assets and reference material
docs/              MkDocs documentation
experimental/      explicitly non-stable work
```

The principal physical implementation belongs under `ncmemsim/`.

Repository-level directories such as `examples/`, `tests/`, `validation/`, and
`docs/` support the scientific software but are not runtime package modules.

## Main package responsibilities

The package is intentionally modular.

Important areas include:

```text
device / layers / builder
        |
        v
materials
        |
        v
state
        |
        +-------------------------+
        |                         |
        v                         v
electrical physics          optical physics
        |                         |
        |                    optics.py
        |                    photo.py
        |                         |
        +------------+------------+
                     |
                     v
               occupancy kinetics
                     |
                     v
                  Simulator
```

The architecture is described in more detail in
[Software architecture](architecture.md).

## Electrical and optical separation

Electrical and optical physics should remain separable at the kernel level.

The electrical path contains quantities such as:

- electrostatic potential;
- electric field;
- WKB-type tunnelling;
- inter-FG transport;
- charge-state transition rates.

The optical path contains quantities such as:

- photon energy;
- photon flux;
- Ge/GeSn optical gaps;
- absorption coefficients;
- Beer-Lambert absorption;
- absorbed photon rate per nanocrystal;
- photo-assisted transition rates.

The two paths are combined at the transition-rate level.

Conceptually,

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}
+
r_{ij}^{\mathrm{photo}}.
\]

A new optical model should therefore not duplicate the occupancy solver.

Likewise, a new electrical transport model should not introduce an independent
charge-state representation unless a deliberate architectural change is being
made.

## Adding a new physical feature

A new physical feature should normally follow this sequence:

1. define the physical problem and intended scope;
2. document the governing equations or algorithmic definition;
3. define parameters, units, assumptions, and validity range;
4. identify parameter provenance and calibration status;
5. add or extend an explicit configuration dataclass;
6. implement the narrowest independently testable physical kernel;
7. add limiting-case and invalid-input tests;
8. integrate through the existing architecture only after the kernel is tested;
9. add end-to-end regression coverage;
10. update scientific documentation and API documentation;
11. update reproducibility metadata if new simulation inputs affect results;
12. update the changelog when the feature becomes user-visible.

Do not begin by adding logic directly to `Simulator` if the new physics can be
represented as an independently testable model.

`Simulator` should orchestrate physical models rather than become the physical
model itself.

## Physical-model requirements

Every new physical model should state:

- what quantity is calculated;
- which equations or numerical rules are used;
- which units are expected;
- which parameters are required;
- where those parameters come from;
- the physical range over which the model is intended to be used;
- known approximations;
- omitted physical effects;
- whether the model is literature-supported, provisional, fitted, or
  experimentally calibrated.

A physically plausible curve is not sufficient documentation.

The implementation must make clear what is known, assumed, fitted, or
extrapolated.

## Parameter provenance

NCMemSim distinguishes several parameter states.

### Literature-supported

A parameter or equation has an identified basis in published scientific
literature.

This does not automatically mean that it has been calibrated to the simulated
device.

### Provisional

A compact-model parameter has been selected for implementation, testing, or
benchmarking but is not yet experimentally constrained for the intended
device.

### Fitted

A parameter has been estimated against a specified reference dataset.

The fitting method and dataset should be documented.

### Experimentally calibrated

A parameter has been constrained against suitable measurements for the
intended material or device system.

These categories must not be presented as interchangeable.

## Adding or modifying a material model

A new material model should provide:

1. an unambiguous material or parameter-set identifier;
2. parameters with explicit units;
3. provenance metadata;
4. composition validity ranges where applicable;
5. temperature assumptions or validity ranges;
6. strain assumptions where relevant;
7. endpoint and representative-value tests;
8. documented extrapolation behaviour;
9. explicit calibration status.

A stable public model should be added to the appropriate registry or public
namespace only after its behaviour has been reviewed.

## Optical material development

The public optical-material API is intentionally separated under:

```python
ncmemsim.materials.optics
```

Current v0.10.0 optical-material objects include concepts such as:

- direct-Gamma gap;
- indirect-L gap;
- phonon occupation;
- direct absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption.

When adding or modifying an optical material model, document:

- direct and indirect transition definitions;
- composition dependence;
- temperature dependence;
- spectral validity range;
- literature or experimental basis;
- absorption amplitudes;
- phenomenological parameters;
- extrapolated regions;
- whether strain is represented;
- whether quantum confinement is represented;
- whether electric-field effects are represented;
- whether state filling is represented.

Do not silently interpret the electronic `NanocrystalMaterial.bandgap_eV`
parameter as the optical direct gap.

Electronic and optical band-gap quantities have different roles in the current
architecture.

## Optical-source development

Optical excitation is represented through `ncmemsim.optics`.

For example:

```python
from ncmemsim.optics import LightSource

source = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

A source model should keep source physics separate from material absorption.

Source calculations may provide quantities such as:

- wavelength;
- photon energy;
- optical power density;
- incident photon flux.

Material absorption should be evaluated by the corresponding optical-material
and floating-gate absorption models.

## Photo-assisted transition development

Photo-assisted charge-state kinetics are implemented in `ncmemsim.photo`.

For example:

```python
from ncmemsim.photo import PhotoTransitionConfig

photo = PhotoTransitionConfig(
    photo_capture_efficiency=1.0e-7,
)
```

Photo-assisted rates should be constructed from explicit optical inputs rather
than by directly modifying occupation probabilities.

The current v0.10.0 model represents photo-assisted loading through:

```text
0 -> 1
1 -> 2
```

with photo-assisted detrapping disabled by default.

A new photo-transition mechanism should specify:

- affected charge-state transitions;
- units of every rate;
- whether the contribution loads or unloads charge;
- its physical coupling parameter;
- calibration status;
- limiting behaviour when optical power is zero.

Dark-source behaviour must remain explicitly testable.

## Numerical conventions

Use the following conventions throughout the simulator:

- use NumPy arrays for vector state variables;
- preserve probability normalization to the documented tolerance;
- treat clipping as a physical or numerical decision, not as a cosmetic fix;
- keep inter-FG charge transfer conservative;
- keep units explicit;
- make timestep choices visible in configuration;
- use the effective integration timestep that exactly spans the requested dwell
  interval;
- avoid uncontrolled randomness;
- avoid numerical behaviour that depends unintentionally on dictionary
  insertion order;
- test zero-input, limiting, and boundary cases.

Numerical stabilization must not silently change the physical model.

If clipping, limiting, regularization, or approximation is required, its reason
should be documented.

## Timestep handling

For a requested dwell time, numerical subdivision must preserve the total
physical interval.

The effective timestep is

\[
\Delta t_{\mathrm{actual}}
=
\frac{t_{\mathrm{dwell}}}{N_{\mathrm{steps}}}.
\]

Do not advance every step using a nominal timestep if that would integrate for
longer than the requested dwell interval.

Changes to timestep semantics require regression review because they can alter
programming and retention results even when all other physical parameters are
unchanged.

## Multi-FG conservation

Inter-floating-gate transport must preserve internal charge conservation,
subject only to explicitly represented exchange with external reservoirs.

When adding a new transport path:

- define the source and destination nodes;
- limit transfer according to available charge-state populations;
- verify sign conventions;
- test internal conservation;
- test zero-coupling behaviour;
- test symmetry or directionality where physically applicable.

Do not repair conservation errors only in post-processing.

## Multi-FG optical behaviour

In v0.10.0, each floating gate evaluates optical absorption using the same
incident source.

The current model does not yet propagate the transmitted optical flux
sequentially through multiple floating gates.

Therefore code that assumes

```text
source -> FG0 -> attenuated flux -> FG1 -> attenuated flux -> FG2
```

would constitute a new physical feature and must not be introduced as a minor
implementation detail.

Such a change would require new:

- optical propagation logic;
- API semantics;
- tests;
- documentation;
- regression baselines.

## Extending the public API

A public class, function, or result object should:

- have a clear docstring;
- use typed arguments and returns;
- expose units explicitly where practical;
- have deterministic behaviour;
- validate invalid input where appropriate;
- be documented in `docs/api.md`;
- have direct import tests;
- have compatibility implications reviewed.

Not every public object needs to be re-exported at the package root.

The current namespace policy is intentional.

Core user-facing functionality may be available through:

```python
ncmemsim
```

while specialized optical APIs use namespaces such as:

```python
ncmemsim.optics
ncmemsim.photo
ncmemsim.materials.optics
```

In particular, optical-material classes should not automatically be added to
the top-level namespace merely for convenience.

This keeps the root API manageable and makes physical ownership clearer.

## Internal APIs

Internal modules may evolve before v1.0.

Code intended to survive minor releases should prefer:

- documented public imports;
- documented result objects;
- stable simulator entry points;
- documented configuration dataclasses.

Avoid documenting an internal helper as stable merely because it is currently
importable.

## Result dictionaries and diagnostics

When adding a new simulator diagnostic:

1. choose an unambiguous name;
2. encode units in the key where practical;
3. define scalar versus per-FG semantics;
4. define behaviour for inactive physics;
5. define behaviour for multi-FG devices;
6. test the result explicitly.

For optical diagnostics, per-FG arrays are the primary representation for
multi-FG devices.

Scalar convenience quantities must have a documented aggregation rule.

Do not silently change the meaning of an existing result key.

## Tests and regression data

Run focused tests during development and the complete suite before integrating
a feature.

Examples:

```bash
python -m pytest tests/test_phase_d4_transport.py -q
python -m pytest tests/test_phase_e3_optical_absorption.py -q
python -m pytest tests/test_phase_e5a_simulator_optics.py -q
python -m pytest tests/test_phase_e6c_swir_voltage_reduction.py -q
python -m pytest -q
```

The official v0.10.0 release baseline contains:

```text
194 passed
```

The repository CI matrix verifies Python:

```text
3.11
3.12
3.13
```

A feature is not considered integrated merely because its new tests pass.

The full suite must remain green.

## Test categories

A robust physical feature should normally include several kinds of tests.

### Unit tests

Test isolated physical kernels and input validation.

Examples include:

- photon-energy conversion;
- band-gap composition functions;
- Beer-Lambert absorption;
- transition-rate generation.

### Limiting-case tests

Test physically recognizable boundaries.

Examples include:

- zero optical power;
- disabled source;
- zero transport coupling;
- zero dwell time where supported;
- probability normalization.

### Integration tests

Test interaction among physical subsystems.

Examples include:

- optical absorption to photo-transition generation;
- electrical plus optical rate coupling;
- simulator diagnostics;
- sweep propagation.

### Regression tests

Protect already approved numerical behaviour.

A regression test should not be changed merely because a new implementation
produces different numbers.

First determine whether the new behaviour represents:

- a bug fix;
- an intended physical-model change;
- a numerical convention change;
- an unintended regression.

## Golden references

Do not regenerate golden references automatically during normal tests.

Golden generation is an explicit maintainer operation.

A golden baseline should change only after reviewing why the numerical result
changed.

Golden agreement demonstrates numerical consistency with the stored baseline;
it does not establish experimental validity.

## Scientific benchmarks

Benchmarks should state all parameters needed to reproduce the result.

A benchmark value is not automatically a calibrated prediction.

For example, the Phase E6 SWIR voltage-reduction benchmark deliberately uses a
selected photo-capture efficiency so that electrical and optical contributions
can be compared within a common occupation range.

That benchmark parameter must not silently become a new physical default.

## Experimental calibration

A parameter fitted for validation or demonstration should not replace a global
default without an explicit decision.

Calibration work should record:

- experimental dataset;
- sample or device conditions;
- temperature;
- spectral or electrical measurement conditions;
- fitted parameters;
- parameter bounds;
- objective function;
- fitting method;
- uncertainty where available;
- model version.

Device-specific calibration belongs to a distinct validation stage.

Software verification and experimental calibration are not equivalent.

## Reproducibility

Any new simulation input capable of changing a result should be considered for
inclusion in the reproducibility manifest.

Typical reproducibility information includes:

- NCMemSim version;
- device definition;
- material parameters;
- physical-model configuration;
- simulation configuration;
- optical-source configuration where applicable;
- photo-transition configuration where applicable;
- canonical hashes.

A hash identifies serialized inputs.

It does not prove that those inputs are physically correct.

## Documentation

User-facing documentation should be:

- consistent with the implemented software;
- executable where code examples are provided;
- explicit about assumptions;
- explicit about units;
- explicit about provenance;
- explicit about calibration status;
- explicit about extrapolation;
- clear about current versus planned functionality.

Do not document planned physics as though it already exists.

Do not describe a verification benchmark as experimental validation.

Build the documentation locally with:

```bash
python -m mkdocs build --strict
```

The strict build must succeed before documentation changes are considered
complete.

The Material for MkDocs warning concerning future MkDocs 2.0 compatibility is
external to the current NCMemSim documentation build and is not itself a
strict-build failure.

## Executable examples

Examples should use public or intentionally documented interfaces.

For optical v0.10.0 development, useful reference examples include:

```text
examples/e6a_swir_wavelength_sweep.py
examples/e6d_swir_voltage_reduction.py
```

Examples should be reproducible and should state when their parameters are
provisional or benchmark-specific.

Do not use an example script to hide undocumented model assumptions.

## Changelog requirements

A user-visible change should normally be reflected in `CHANGELOG.md`.

The changelog entry should distinguish among:

- new capability;
- bug fix;
- numerical correction;
- API change;
- documentation-only change;
- calibration update;
- compatibility change.

A numerical result that changes because of corrected timestep handling, model
parameters, or rate definitions should not be described merely as a refactor.

## Experimental code

Code under `experimental/` is not part of the stable API.

It may be incomplete, exploratory, or incompatible with the current release.

Promotion from `experimental/` into `ncmemsim/` requires:

- defined physical scope;
- reviewed equations or algorithms;
- typed implementation;
- tests;
- documentation;
- provenance;
- compatibility review;
- a defined public or internal API role.

Exploratory code should not be imported by stable package modules.

## Development completion checklist

Before considering a physical feature complete, verify that:

- the physical model is documented;
- assumptions and validity ranges are stated;
- units are explicit;
- parameter provenance is recorded;
- calibration status is recorded;
- limiting cases are tested;
- integration tests are present;
- regression behaviour has been reviewed;
- the full test suite passes;
- strict documentation build passes;
- user-facing API documentation is updated;
- reproducibility implications are reviewed;
- changelog impact is reviewed.

For the v0.10.0 baseline, the final repository-level checks are:

```bash
git diff --check
python -m pytest -q
python -m mkdocs build --strict
```

Generated files under `site/` are MkDocs build output and should not be edited
as substitutes for changes to the Markdown sources.

## Development principle

NCMemSim should remain easy to extend without making its scientific meaning
harder to trace.

The preferred development direction is therefore:

```text
explicit physics
    +
explicit parameters
    +
explicit provenance
    +
independent kernel tests
    +
controlled integration
    +
reproducible outputs
```

rather than increasing model complexity without corresponding scientific and
numerical traceability.
