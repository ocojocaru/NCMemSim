# Software architecture

## Overview

NCMemSim uses a modular architecture that separates:

- device geometry;
- material definitions and provenance;
- electrical and optical material models;
- simulation state;
- electrostatics;
- tunnelling and transport;
- charge-state kinetics;
- optical absorption;
- photo-assisted kinetics;
- simulation orchestration;
- retention;
- validation;
- benchmarking;
- reproducibility.

This separation allows an individual physical model to be replaced, extended,
or calibrated without requiring the complete simulation workflow to be
rewritten.

Version 0.10.0 extends the original electrical architecture with a parallel
optical path that joins the electrical path at the occupancy-kinetics level.

## High-level architecture

The principal data flow is:

```text
                         DeviceBuilder
                              |
                              v
                            Device
                              |
                 +------------+------------+
                 |                         |
                 v                         v
          ordered Layer list       FloatingGateLayer
                                           |
                                           v
                                      DeviceState
                                           |
                              FloatingGateState(s)
                                           |
              +----------------------------+----------------------------+
              |                                                         |
              | ELECTRICAL PATH                                         | OPTICAL PATH
              |                                                         |
              v                                                         v
     ElectrostaticsEngine                                           LightSource
              |                                                         |
              v                                                         v
        FieldSolver1D                                      Ge/GeSn optical model
              |                                              materials/optics/
              v                                                         |
      TunnelingEngine                                                    v
              |                                            FG optical absorption
              v                                                   optics.py
       TransportEngine                                                   |
              |                                                         v
              |                                            photo-transition rates
              |                                                   photo.py
              |                                                         |
              +--------------------------+------------------------------+
                                         |
                                         v
                                  OccupancyEngine
                                         |
                                         v
                                      Simulator
                           +-------------+-------------+
                           |             |             |
                           v             v             v
                    relax_voltage     sweep          C-V
                           |
                           v
                    RetentionSolver
                           |
                           v
               scientific result / diagnostics
                           |
              +------------+------------+
              |            |            |
              v            v            v
          validation     golden      benchmark
              \            |            /
               \           |           /
                +----------+----------+
                           |
                           v
                reproducibility manifest
```

The electrical and optical branches are therefore not separate simulators.

Both ultimately contribute transition rates to the same nanocrystal
charge-state kinetics.

## Architectural principles

### Separation of geometry and physics

Device geometry is represented independently from the physical engines.

Physics modules consume the device definition and state rather than relying on
hard-coded assumptions about a particular stack.

This allows the same physical kernels to operate on supported one-, two-, and
three-floating-gate structures.

### Separation of electrical and optical material properties

Electronic material parameters and optical material properties are deliberately
separated.

For example, the compact electronic `bandgap_eV` associated with a
nanocrystal material is not used as a substitute for the direct-Gamma and
indirect-L optical gaps.

The optical material layer therefore has its own parameter sets, models, and
provenance.

### Separation of rates from state evolution

Electrical tunnelling and optical absorption produce transition rates.

The occupancy engine evolves the nanocrystal charge-state probabilities using
those rates.

This makes the state-evolution algorithm independent of the detailed physical
origin of a rate and allows electrical and photo-assisted contributions to be
combined consistently.

### Explicit provenance

Material and model parameters are designed to carry provenance information.

The architecture distinguishes:

- literature-supported parameters;
- provisional compact-model parameters;
- fitted parameters;
- experimentally calibrated parameters.

Reproducibility metadata should preserve enough information to identify the
physical model and parameter set used for a simulation.

### Verification at module and workflow levels

Physical kernels are tested independently before integration into
`Simulator`.

Validation then extends from unit-level behaviour to complete simulation
workflows and deterministic regression cases.

## Core package structure

The main package is organized conceptually as:

```text
ncmemsim/
|
+-- __init__.py
+-- _version.py
|
+-- device.py
+-- layers.py
+-- builder.py
+-- state.py
|
+-- materials/
|   +-- material definitions
|   +-- composition models
|   +-- band alignment
|   +-- provenance
|   +-- registry
|   |
|   +-- optics/
|       +-- Ge/GeSn optical parameter sets
|       +-- direct-gap model
|       +-- indirect-gap model
|       +-- composite absorption model
|
+-- electrostatics.py
+-- coupling.py
+-- fieldsolver.py
+-- tunneling.py
|
+-- transport/
|   +-- transport nodes
|   +-- tunnel links
|   +-- conservative transfer engine
|
+-- kinetics.py
|
+-- optics.py
+-- photo.py
|
+-- simulator.py
+-- retention.py
|
+-- validation.py
+-- golden.py
+-- benchmark.py
+-- reproducibility.py
```

The exact internal file structure may evolve before v1.0. The conceptual
separation between these responsibilities is the important architectural
contract.

## Device layer

### `device.py`, `layers.py`, and `builder.py`

`Device` owns the ordered physical stack.

A generic `Layer` represents a dielectric or semiconductor region.

`FloatingGateLayer` adds nanocrystal-specific information including quantities
such as:

- nanocrystal material;
- nanocrystal diameter;
- nanocrystal volume fraction;
- electrically active fraction;
- state-grid information.

`DeviceBuilder` provides reproducible construction of supported device
families and normalizes scalar or per-floating-gate inputs.

The ordered stack defines the one-dimensional coordinate used by the
electrostatic and transport models.

## State layer

### `state.py`

`DeviceState` contains one `FloatingGateState` for each physical floating gate.

Each floating-gate state stores the distributed probabilities

\[
P_0,\qquad P_1,\qquad P_2,
\]

together with derived and diagnostic quantities.

State objects retain identifiers linking them to the physical floating-gate
layers.

Geometry validation prevents a state from being silently reused with an
incompatible device.

The state layer is independent of whether a transition rate originated from an
electrical or optical mechanism.

## Materials layer

### `materials/`

The materials package provides:

- named material definitions;
- nanocrystal materials;
- composition-dependent material models;
- band-alignment helpers;
- material registries;
- parameter provenance.

Electrical material quantities include parameters used by electrostatics and
tunnelling.

### `materials/optics/`

Version 0.10.0 adds a dedicated optical-material namespace.

It contains the compact Ge/GeSn optical models used to evaluate:

- photon-energy-dependent material response;
- direct-Gamma gap;
- indirect-L gap;
- phonon occupation;
- direct absorption;
- indirect phonon-assisted absorption;
- Urbach-tail absorption.

The composite absorption model returns both the total absorption coefficient
and its physical components.

Keeping this layer separate from the electrical material representation avoids
silently conflating electronic and optical band-gap definitions.

## Electrical physics path

### `electrostatics.py` and `coupling.py`

The electrostatic layer maps floating-gate charge into compact electrostatic
quantities such as flat-band-shift contributions.

For multiple floating gates, the coupling model retains individual
floating-gate contributions rather than reducing the complete device to a
single undifferentiated charge sheet.

### `fieldsolver.py`

`FieldSolver1D` reconstructs a piecewise one-dimensional potential and electric
field across the ordered device stack.

Local potential and field quantities are evaluated at relevant positions,
including floating-gate centers.

These local fields provide inputs to the tunnelling and rate models.

### `tunneling.py`

`TunnelingEngine` evaluates compact WKB-type tunnelling transmission.

The engine depends on quantities such as:

- effective barrier height;
- effective mass;
- barrier thickness;
- local electric field;
- charge-state energetics.

Tunnelling remains separated from occupancy evolution so that transmission and
rate calculations can be tested independently.

## Transport layer

### `transport/`

The transport package maps the device onto explicit transport nodes and tunnel
links.

Nodes may represent:

- the substrate;
- individual floating gates;
- external reservoirs where applicable.

Links represent allowed carrier-transfer paths.

Inter-floating-gate transfer is availability limited.

For pure internal floating-gate redistribution, the implementation preserves
charge conservation within numerical tolerance.

The transport layer therefore supplies physical transfer information without
directly owning the nanocrystal probability state.

## Occupancy layer

### `kinetics.py`

`OccupancyEngine` evolves the three-state nanocrystal system:

\[
P_0 \rightleftarrows P_1 \rightleftarrows P_2.
\]

The engine consumes transition-rate arrays and advances the probability state
over a specified timestep.

For the coupled v0.10.0 model, the total rate can contain electrical and optical
contributions:

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}
+
r_{ij}^{\mathrm{photo}}.
\]

The occupancy engine does not need to know how those contributions were
generated.

This separation is central to the v0.10.0 electro-optical architecture.

## Optical physics path

### `optics.py`

The optical-source and floating-gate absorption layer handles:

- monochromatic source definitions;
- photon energy;
- incident photon flux;
- Beer-Lambert absorption;
- nanocrystal-volume-fraction effective absorption;
- absorbed photon flux;
- transmitted photon flux;
- average volumetric generation rate;
- floating-gate optical diagnostics.

The effective floating-gate absorption coefficient is represented as

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}\alpha_{\mathrm{NC}}.
\]

The optical absorption path uses nanocrystal volume fraction rather than the
electrically active fraction used by the charge-state model.

### `photo.py`

The photo-assisted kinetics layer converts optical absorption into transition
rates.

Its responsibilities include:

- nanocrystal volume calculation;
- nanocrystal number-density calculation;
- absorbed photon rate per nanocrystal;
- photo-capture efficiency;
- transition weighting;
- photo-transition-rate arrays.

The default v0.10.0 photo-loading configuration supports:

\[
0 \rightarrow 1
\]

and

\[
1 \rightarrow 2.
\]

Photo-assisted detrapping is disabled by default.

The photo-capture efficiency remains a provisional compact-model parameter
unless replaced by a calibrated value.

## Electrical-optical rate coupling

The coupling point between the electrical and optical architectures is the
transition-rate representation.

Conceptually:

```text
Electrical fields
      |
      v
Tunnelling / transport
      |
      v
Electrical transition rates --------+
                                     |
                                     v
                              Combined rates
                                     |
                                     v
                               OccupancyEngine
                                     ^
                                     |
Photo transition rates --------------+
      ^
      |
Absorbed photons
      ^
      |
Ge/GeSn absorption
      ^
      |
LightSource
```

This architecture allows optical programming to extend the existing electrical
kinetics without creating a second independent state model.

It also allows electrical-only simulations to follow the same established
path when no optical source is present.

## Simulator orchestration

### `simulator.py`

`Simulator` coordinates the physical modules.

For an electrical-only voltage relaxation, the workflow is conceptually:

```text
DeviceState
    |
    v
electrostatics
    |
    v
local fields
    |
    v
tunnelling / transport
    |
    v
electrical rates
    |
    v
occupancy update
    |
    v
new DeviceState
```

For electro-optical programming:

```text
                         DeviceState
                             |
              +--------------+--------------+
              |                             |
              v                             v
        electrical path                optical path
              |                             |
              v                             v
      electrical rates                 photo rates
              |                             |
              +--------------+--------------+
                             |
                             v
                       combined rates
                             |
                             v
                      occupancy update
                             |
                             v
                       new DeviceState
```

The optical response for a fixed source and material is evaluated independently
of the internal electrical timestep where possible, avoiding unnecessary
recalculation.

The simulator exposes high-level workflows including:

- voltage relaxation;
- voltage sweeps;
- compact C-V simulation;
- retention-related entry points.

Optical source and photo-transition configuration can be passed into supported
programming and sweep workflows.

## Optical diagnostics

The simulator propagates optical diagnostics to result objects.

Per-floating-gate diagnostics include quantities such as:

- optical absorption fraction;
- absorbed photon flux;
- absorbed photon rate per nanocrystal;
- photo-transition rate;
- nanocrystal absorption coefficient;
- effective floating-gate absorption coefficient.

Scalar convenience values are also provided where useful.

The per-floating-gate representation is the primary architecture for multi-FG
devices.

## Retention architecture

### `retention.py`

`RetentionSolver` advances a coupled device state at fixed external bias,
normally zero gate bias.

The solver can use geometrically increasing timesteps and selected output
times.

Retention remains built on the same underlying:

- device state;
- electrostatics;
- field evaluation;
- transport;
- occupancy machinery.

This avoids maintaining a separate incompatible state representation for
retention calculations.

## Multi-FG optical architecture

In v0.10.0, optical absorption is evaluated independently for each floating
gate using the same incident source.

The current architecture does not yet propagate transmitted optical flux
sequentially from one floating gate to the next.

Conceptually, the present model is:

```text
                    LightSource
                 /      |       \
                v       v        v
              FG0     FG1      FG2
                |       |        |
                v       v        v
             photo    photo    photo
             rates    rates    rates
```

rather than:

```text
LightSource -> FG0 -> transmitted flux -> FG1 -> transmitted flux -> FG2
```

Sequential multilayer optical propagation is therefore a future architectural
extension.

## Validation architecture

### `validation.py`

The validation layer checks scientific and numerical invariants such as:

- probability normalization;
- finite state values;
- physical geometry constraints;
- admissible material parameters;
- finite potential and electric-field profiles;
- internal charge conservation;
- optical-rate consistency.

Validation is intentionally separate from the physical kernels so that
consistency rules can be applied across multiple workflows.

## Golden references

### `golden.py`

Golden cases provide deterministic numerical reference results for selected
device configurations.

They protect against unintended changes to established numerical behaviour.

Golden references are not automatically regenerated during normal testing.

A change to golden data should correspond to a reviewed physical or numerical
model change.

## Benchmarking

### `benchmark.py`

Benchmark utilities measure deterministic simulation cases and provide
performance-oriented records.

Performance benchmarks are separate from scientific validation: faster
execution does not establish physical correctness.

## Reproducibility

### `reproducibility.py`

Reproducibility manifests record simulation context including quantities such
as:

- NCMemSim version;
- runtime information;
- device definition;
- material models;
- simulation configuration;
- canonical hashes.

The manifest architecture supports identification of the inputs used to
produce a numerical result.

A reproducibility hash establishes identity of serialized inputs, not physical
validity.

## Public versus internal API

Stable user-facing symbols are exposed through documented public namespaces.

Core package symbols are re-exported through `ncmemsim/__init__.py` where
appropriate.

The optical material API is intentionally available through:

```text
ncmemsim.materials.optics
```

rather than re-exporting every optical-material symbol at the package root.

This keeps the top-level namespace manageable while maintaining a documented
public optical API.

Before v1.0, internal module paths may evolve.

Scientific scripts intended to remain compatible across releases should prefer
documented public imports and documented simulator entry points.

## Dependency direction

The intended architectural dependency direction is approximately:

```text
device / layers / materials
            |
            v
           state
            |
      +-----+-----+
      |           |
      v           v
 electrical    optical
 physics       physics
      |           |
      +-----+-----+
            |
            v
         kinetics
            |
            v
        simulator
            |
            v
        workflows
            |
            v
  validation / results
            |
            v
    reproducibility
```

Lower-level physical modules should not depend on presentation, documentation,
or high-level workflow code.

This dependency direction helps prevent circular coupling between physical
models and keeps individual kernels independently testable.

## Extension points

The architecture is intended to support future additions without invalidating
the existing electrical and optical paths.

Planned extension points include:

- experimentally fitted material parameters;
- calibrated optical absorption;
- calibrated photo-capture efficiency;
- uncertainty and identifiability analysis;
- strain-dependent GeSn optical properties;
- nanocrystal quantum-confinement corrections;
- field-dependent optical response;
- state-filling effects;
- sequential optical attenuation through multi-FG stacks;
- systematic design-space exploration;
- DTCO and Pareto analysis.

New capabilities should enter through explicit model interfaces rather than by
silently modifying unrelated kernels.

## Architectural validation baseline

The official v0.10.0 release is the current architectural baseline.

It integrates:

```text
device
  -> materials
  -> state
  -> electrical physics
  -> optical physics
  -> combined kinetics
  -> simulator workflows
  -> validation
  -> reproducibility
```

The v0.10.0 test suite contains **194 tests** covering Phases A through E6.

The architecture is verified on the supported Python 3.11, 3.12, and 3.13 CI
matrix.

Changes to module boundaries, rate coupling, state semantics, or physical
workflow ordering should therefore be accompanied by explicit regression
testing and documentation.
