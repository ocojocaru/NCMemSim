# Public API overview

The stable import surface for NCMemSim v0.10.0 is defined primarily in
`ncmemsim/__init__.py`, with optical material models exposed from
`ncmemsim.materials.optics`.

The following groups summarize the principal public objects.

## Version

- `__version__`

## Device and materials

- `Device`
- `DeviceBuilder`
- `Layer`
- `FloatingGateLayer`
- `Material`
- `NanocrystalMaterial`
- `SILICON`, `SIO2`, `HFO2`
- `make_ge`, `make_gesn`
- `make_v53_reference_device`

## State

- `DeviceState`
- `FloatingGateState`

## Simulation

- `Simulator`
- `SimulationConfig`
- `SweepResult`
- `CVResult`
- `PhysicsModel`

`Simulator.relax_voltage()` supports dark, optical, and electro-optical
programming through the optional arguments:

- `light_source`
- `photo_config`
- `photo_weights`

The same optical configuration can be propagated through voltage sweeps
and compact C-V simulations.

## Electrostatics and fields

- `ElectrostaticsEngine`
- `ElectrostaticsResult`
- `SemiconductorConfig`
- `CouplingModel`
- `CompactCouplingModel`
- `CouplingResult`
- `FieldSolver1D`
- `FieldProfile`

## Kinetics and tunnelling

- `KineticsConfig`
- `OccupancyEngine`
- `RateArrays`
- `TunnelingConfig`
- `TunnelingEngine`

Electrical and optical transition-rate arrays are combined additively by
the occupancy engine.

## Optical sources

- `LightSource`

`LightSource` represents monochromatic LED and laser sources and provides
derived photon quantities including:

- photon energy in joules;
- photon energy in electron-volts;
- incident photon flux.

Example:

```python
from ncmemsim.optics import LightSource

source = LightSource.laser(
    wavelength_nm=1550.0,
    power_density_W_m2=1000.0,
)
```

## Optical material models

The public optical material API is available from
`ncmemsim.materials.optics`.

Principal objects include:

- `OpticalPoint`
- `GeSnOpticalParameterSet`
- `GeSnAbsorptionParameterSet`
- `CompactOpticalMaterialModel`
- `CompositeGeSnAbsorptionModel`
- `photon_energy_eV`
- `direct_gap_gesn_eV`
- `indirect_gap_gesn_eV`
- `phonon_occupation`

The compact Ge/GeSn optical model provides separate direct-Gamma,
indirect phonon-assisted, and Urbach-tail absorption contributions.

Example:

```python
from ncmemsim.materials.optics import CompositeGeSnAbsorptionModel

model = CompositeGeSnAbsorptionModel()
point = model.evaluate(material, wavelength_nm=1550.0)
```

## Optical absorption

The optical layer model provides:

- Beer-Lambert absorption;
- nanocrystal-volume-fraction effective absorption;
- absorbed photon flux;
- transmitted photon flux;
- average volumetric generation rate;
- floating-gate optical diagnostics.

The principal floating-gate evaluation path is exposed through:

- `evaluate_floating_gate_optical_absorption`

A floating-gate optical result includes quantities such as:

- incident photon flux;
- absorbed photon flux;
- transmitted photon flux;
- nanocrystal absorption coefficient;
- effective absorption coefficient;
- direct, indirect, and Urbach contributions;
- direct and indirect optical gaps.

## Photo-assisted transitions

Photo-assisted charge-state kinetics are configured with:

- `PhotoTransitionConfig`
- `PhotoTransitionWeights`
- `PhotoTransitionRates`
- `PhotoTransitionEvaluation`

The default compact photo-loading model supports:

- 0 -> 1
- 1 -> 2

Photo-assisted detrapping is disabled by default.

Example:

```python
from ncmemsim.photo import PhotoTransitionConfig

photo = PhotoTransitionConfig(
    photo_capture_efficiency=1.0e-7,
)
```

The default photo-capture efficiency is a provisional compact-model
parameter and should not be treated as experimentally calibrated unless
explicitly replaced by a calibrated value.

## Optical simulator diagnostics

When optical programming is enabled, `Simulator.relax_voltage()` exposes
diagnostics including:

- `optical_absorption_fraction`
- `absorbed_photon_flux_m2_s`
- `photo_transition_rate_s`
- `optical_absorption_fraction_by_fg`
- `absorbed_photon_flux_by_fg_m2_s`
- `absorbed_photon_rate_per_nc_by_fg_s`
- `photo_transition_rate_by_fg_s`
- `optical_alpha_nc_by_fg_m_inv`
- `optical_alpha_eff_by_fg_m_inv`

For dark simulations, optical flux and photo-transition rates are zero.

For disabled optical sources, photon flux and photo-transition rates are
zero while wavelength-dependent material properties can remain defined.

## Transport

- `NodeKind`
- `TransportNode`
- `TunnelLink`
- `TunnelNetwork`
- `TransportConfig`
- `TransportEngine`
- `LinkTransportResult`
- `TransportStepResult`

## Retention

- `RetentionConfig`
- `RetentionSolver`
- `RetentionResult`

## Validation and reproducibility

- `ValidationIssue`
- `ValidationReport`
- `validate_probabilities`
- `validate_device_physics`
- `validate_field_profile`
- `validate_internal_charge_conservation`
- `validate_simulation`
- `build_reproducibility_manifest`

## Golden references and benchmarks

- `build_golden_suite`
- `compare_golden`
- `write_golden_suite`
- `BenchmarkRecord`
- `benchmark_case`
- `run_benchmark_suite`
- `write_benchmark_report`

## Compatibility note

Before v1.0, internal module paths and some result-dictionary details may
evolve.

Code intended to survive minor releases should prefer the documented
public imports, documented result objects, and stable simulator entry
points.
