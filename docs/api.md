# Public API overview

The stable import surface for the v0.9 series is defined in `ncmemsim/__init__.py`. The following groups summarize the principal public objects.

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

## Optical foundation

- `LightSource`

`LightSource` is available for source description, but the coupled optical-programming engine is a planned Phase E feature.

## Compatibility note

Before v1.0, internal module paths and some result-dictionary details may evolve. Code intended to survive minor releases should prefer the top-level public imports and documented result objects.
