# API source inventory

Generated from the audited source baseline. [Compatibility preparation](api_compatibility.md)
and [result contracts](api_results.md) distinguish observed behavior from v1.0 approval.

Coverage: 88 package source modules; 433 explicit export paths; 171 distinct documented Python import paths.

Source signatures retain `self`/`cls` and unevaluated defaults. Dataclass fields below are
declared fields, not a synthesized inherited constructor. Properties are shown as methods
with their decorators. Public spelling alone does not approve an internal helper.

The [JSON inventory](api_inventory.json) includes structured parameters, field defaults,
assignment expressions and documented imports for compatibility review.

## ncmemsim

`ncmemsim/__init__.py`

Explicit exports: `__version__`, `BenchmarkRecord`, `CVResult`, `CompactCouplingModel`, `CouplingModel`, `CouplingResult`, `Device`, `DeviceBuilder`, `DeviceState`, `ElectrostaticsEngine`, `ElectrostaticsResult`, `FieldProfile`, `FieldSolver1D`, `FloatingGateLayer`, `FloatingGateState`, `HFO2`, `KineticsConfig`, `Layer`, `LightSource`, `LinkTransportResult`, `Material`, `NanocrystalMaterial`, `NodeKind`, `OccupancyEngine`, `PhysicsModel`, `RateArrays`, `RetentionConfig`, `RetentionResult`, `RetentionSolver`, `SILICON`, `SIO2`, `SemiconductorConfig`, `SimulationConfig`, `Simulator`, `SweepResult`, `TransportConfig`, `TransportEngine`, `TransportNode`, `TransportStepResult`, `TunnelLink`, `TunnelNetwork`, `TunnelingConfig`, `TunnelingEngine`, `ValidationIssue`, `ValidationReport`, `benchmark_case`, `build_golden_suite`, `build_reproducibility_manifest`, `compare_golden`, `make_ge`, `make_gesn`, `make_v53_reference_device`, `run_benchmark_suite`, `validate_device_physics`, `validate_field_profile`, `validate_internal_charge_conservation`, `validate_probabilities`, `validate_simulation`, `write_benchmark_report`, `write_golden_suite`


## ncmemsim._version

`ncmemsim/_version.py`

No explicit export list; documented entry points need individual approval.


## ncmemsim.benchmark

`ncmemsim/benchmark.py`

No explicit export list; documented entry points need individual approval.

### BenchmarkRecord

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `case: str`; required declaration.
- Field `n_fgs: int`; required declaration.
- Field `elapsed_s: float`; required declaration.
- Field `peak_memory_bytes: int`; required declaration.
- Field `qfg_C_m2: float`; required declaration.

- `benchmark_case(n_fgs: int, repeats: int=3) -> BenchmarkRecord`
- `run_benchmark_suite(repeats: int=3) -> list[BenchmarkRecord]`
- `write_benchmark_report(path: str | Path, repeats: int=3) -> Path`

## ncmemsim.builder

`ncmemsim/builder.py`

No explicit export list; documented entry points need individual approval.

- `seq(v, n, label)`
- `mats(v, n)`
### DeviceBuilder

Bases: none.

- `v1(n_fgs, nc_material=None, control_hfo2_nm=35.0, control_sio2_nm=3.0, fg_thickness_nm=15.0, inter_fg_sio2_nm=4.0, inter_fg_hfo2_nm=4.0, tunnel_hfo2_nm=10.0, tunnel_sio2_nm=2.0, nc_diameter_nm=5.0, nc_volume_fraction=0.6, active_fraction=0.22, name=None)`; `staticmethod`.
- `v2(n_fgs, nc_material=None, control_sio2_nm=20.0, fg_thickness_nm=12.0, inter_fg_sio2_nm=4.0, tunnel_sio2_nm=8.0, nc_diameter_nm=5.0, nc_volume_fraction=0.6, active_fraction=0.22, name=None)`; `staticmethod`.


## ncmemsim.calibration

`ncmemsim/calibration.py`

Explicit exports: `CalibrationCriteria`, `CalibrationCriterionResult`, `CalibrationQualification`, `qualify_calibration`

### CalibrationCriteria

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `max_validation_rmse: float | None`; default expression `None`.
- Field `max_validation_mae: float | None`; default expression `None`.
- Field `min_validation_r2: float | None`; default expression `None`.
- Field `max_scaled_condition_number: float | None`; default expression `None`.
- Field `require_distinct_validation_dataset: bool`; default expression `True`.
- Field `require_local_identifiability: bool`; default expression `True`.
- Field `require_covariance: bool`; default expression `True`.
- `to_dict(self) -> dict[str, Any]`.
- `criteria_hash(self) -> str`.

### CalibrationCriterionResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `passed: bool`; required declaration.
- Field `observed_value: float | bool | str | None`; required declaration.
- Field `comparison: str`; required declaration.
- Field `threshold: float | bool | str | None`; required declaration.
- Field `notes: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### CalibrationQualification

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `fit_dataset_hash: str`; required declaration.
- Field `validation_dataset_hash: str`; required declaration.
- Field `criteria: CalibrationCriteria`; required declaration.
- Field `validation_objective: ObjectiveEvaluation`; required declaration.
- Field `uncertainty_diagnostics: FitUncertaintyDiagnostics`; required declaration.
- Field `criterion_results: tuple[CalibrationCriterionResult, ...]`; required declaration.
- `eligible_for_calibration(self) -> bool`; `property`.
- `failed_criteria(self) -> tuple[str, ...]`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `qualification_hash(self) -> str`.

- `qualify_calibration(fit_result: DeterministicFitResult, uncertainty_diagnostics: FitUncertaintyDiagnostics, *, fit_dataset_hash: str, validation_dataset_hash: str, validation_objective: ObjectiveEvaluation, criteria: CalibrationCriteria) -> CalibrationQualification`

## ncmemsim.composition

`ncmemsim/composition.py`

No explicit export list; documented entry points need individual approval.

- `eps_r_gesn(x_sn: float, bowing: float=0.0) -> float`
- `bandgap_gesn_eV(x_sn: float, bowing: float=2.4) -> float`
- `effective_mass_gesn_m0(x_sn: float, bowing: float=0.0) -> float`
- `barrier_gesn_eV(x_sn: float, phi_ge_eV: float, phi_sn_eV: float, bowing: float=0.0) -> float`

## ncmemsim.constants

`ncmemsim/constants.py`

No explicit export list; documented entry points need individual approval.


## ncmemsim.coupling

`ncmemsim/coupling.py`

No explicit export list; documented entry points need individual approval.

### CouplingResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `qfg_by_fg_C_m2: np.ndarray`; required declaration.
- Field `sensitivity_factors: np.ndarray`; required declaration.
- Field `coefficients_m2_F: np.ndarray`; required declaration.
- Field `delta_vfb_by_fg_V: np.ndarray`; required declaration.
- Field `delta_vfb_V: float`; required declaration.
- Field `matrix_m2_F: np.ndarray`; required declaration.

### CouplingModel

Bases: none.

- `sensitivity_factors(self, device) -> np.ndarray`.
- `evaluate(self, device, qfg_by_fg_C_m2, cox_F_m2: float) -> CouplingResult`.

### CompactCouplingModel

Bases: `CouplingModel`.

Constructor: `__init__(self, *, legacy_single_fg: bool=True)`.

- `sensitivity_factors(self, device) -> np.ndarray`.
- `evaluate(self, device, qfg_by_fg_C_m2, cox_F_m2: float) -> CouplingResult`.


## ncmemsim.device

`ncmemsim/device.py`

No explicit export list; documented entry points need individual approval.

### Device

Bases: none.

Decorators: `dataclass`.

- Field `name: str`; required declaration.
- Field `architecture: str`; required declaration.
- Field `layers: list`; required declaration.
- Field `gate_work_function_eV: float`; default expression `4.8`.
- Field `substrate_doping_m3: float`; default expression `1e+21`.
- Field `temperature_K: float`; default expression `300.0`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `validate(self)`.
- `floating_gates(self)`.
- `number_of_fgs(self)`.
- `total_thickness_nm(self)`.
- `layer_positions_nm(self)`.
- `get_layer(self, name)`.
- `electrical_thickness_nm(self)`.
- `equivalent_dielectric_capacitance_F_m2(self)`.
- `to_dict(self)`.


## ncmemsim.device_calibration

`ncmemsim/device_calibration.py`

Explicit exports: `DeviceCalibrationContext`, `DeviceCalibrationSpec`, `DeviceFitParameterBinding`, `DeviceFitTarget`, `apply_device_calibration_parameters`

### DeviceFitTarget

Bases: `str`, `Enum`.

- Assignment `FG_ELECTRICALLY_ACTIVE_FRACTION = 'fg.electrically_active_fraction'`.
- Assignment `FG_NC_VOLUME_FRACTION = 'fg.nc_volume_fraction'`.
- Assignment `FG_NC_DIAMETER_NM = 'fg.nc_diameter_nm'`.
- Assignment `FG_PHI_BARRIER_PROG_EV = 'fg.phi_barrier_prog_eV'`.
- Assignment `FG_PHI_BARRIER_ERASE_EV = 'fg.phi_barrier_erase_eV'`.
- Assignment `KINETICS_NU0_HZ = 'kinetics.nu0_Hz'`.
- Assignment `KINETICS_NU1_HZ = 'kinetics.nu1_Hz'`.
- Assignment `KINETICS_NU2_HZ = 'kinetics.nu2_Hz'`.
- Assignment `KINETICS_CAPACITANCE_EPS_R = 'kinetics.capacitance_eps_r'`.
- Assignment `TUNNELING_INJECTION_ENERGY_EV = 'tunneling.injection_energy_eV'`.
- Assignment `TUNNELING_OXIDE_EFFECTIVE_MASS_M0 = 'tunneling.oxide_effective_mass_m0'`.
- Assignment `TUNNELING_FIELD_COUPLING_FACTOR = 'tunneling.field_coupling_factor'`.
- Assignment `TUNNELING_ACTIVATION_BETA_V_INV = 'tunneling.activation_beta_V_inv'`.
- Assignment `PHOTO_CAPTURE_EFFICIENCY = 'photo.photo_capture_efficiency'`.
- Assignment `SIMULATION_QFIX_C_M2 = 'simulation.qfix_C_m2'`.
- Assignment `SIMULATION_QIT_C_M2 = 'simulation.qit_C_m2'`.

### DeviceFitParameterBinding

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameter_name: str`; required declaration.
- Field `target: DeviceFitTarget`; required declaration.
- Field `fg_index: int | None`; default expression `None`.
- `canonical_unit(self) -> str | None`; `property`.
- `target_key(self) -> str`; `property`.
- `to_dict(self) -> dict`.

### DeviceCalibrationSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameter_set: FitParameterSet`; required declaration.
- Field `bindings: tuple[DeviceFitParameterBinding, ...]`; required declaration.
- Field `name: str`; default expression `'device-calibration-v1'`.
- Field `notes: str | None`; default expression `None`.
- `identifiability_warnings(self) -> tuple[str, ...]`; `property`.
- `to_dict(self) -> dict`.
- `specification_hash(self) -> str`.

### DeviceCalibrationContext

Bases: none.

Decorators: `dataclass`.

- Field `device: Device`; required declaration.
- Field `physics: PhysicsModel`; required declaration.
- Field `simulation_config: SimulationConfig`; required declaration.
- Field `specification_hash: str`; required declaration.
- Field `parameter_values: dict[str, float]`; required declaration.
- Field `identifiability_warnings: tuple[str, ...]`; required declaration.
- Field `photo_config: PhotoTransitionConfig | None`; default expression `None`.
- `parameter_application_manifest(self) -> dict`.
- `parameter_application_hash(self) -> str`.

- `apply_device_calibration_parameters(base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, spec: DeviceCalibrationSpec, values: np.ndarray | Sequence[float], *, base_photo_config: PhotoTransitionConfig | None=None) -> DeviceCalibrationContext`

## ncmemsim.device_fit

`ncmemsim/device_fit.py`

Explicit exports: `CVCalibrationProtocol`, `DeviceCVFitResult`, `fit_single_parameter_cv_dataset`

### CVCalibrationProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `vmin_V: float`; default expression `-3.0`.
- Field `vmax_V: float`; default expression `3.0`.
- Field `points: int`; default expression `121`.
- `to_dict(self) -> dict`.
- `protocol_hash(self) -> str`.

### DeviceCVFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `protocol: CVCalibrationProtocol`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `objective: DeviceObjectiveEvaluation`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `cv_result: CVResult`; required declaration.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `to_dict(self) -> dict`.

- `fit_single_parameter_cv_dataset(dataset: DeviceObservableDataset, *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, calibration_spec: DeviceCalibrationSpec, protocol: CVCalibrationProtocol, least_squares_config: LeastSquaresConfig | None=None) -> DeviceCVFitResult`

## ncmemsim.device_objectives

`ncmemsim/device_objectives.py`

Explicit exports: `DeviceObjectiveEvaluation`, `evaluate_cv_objective`, `evaluate_memory_window_vs_program_voltage_objective`, `evaluate_memory_window_vs_programming_time_objective`, `evaluate_retention_objective`, `interpolate_without_extrapolation`

### DeviceObjectiveEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `independent_variable_name: str`; required declaration.
- Field `observable_name: str`; required declaration.
- Field `predicted_values: np.ndarray`; required declaration.
- Field `objective: ObjectiveEvaluation`; required declaration.
- Field `simulation_point_count: int`; required declaration.
- Field `interpolation_used: bool`; required declaration.
- Field `unmodeled_condition_names: tuple[str, ...]`; default expression `()`.
- `to_dict(self) -> dict`.

- `interpolate_without_extrapolation(experimental_x: np.ndarray | Sequence[float], simulation_x: np.ndarray | Sequence[float], simulation_y: np.ndarray | Sequence[float]) -> tuple[np.ndarray, bool]`
- `evaluate_cv_objective(dataset: DeviceObservableDataset, result: CVResult) -> DeviceObjectiveEvaluation`
- `evaluate_memory_window_vs_program_voltage_objective(dataset: DeviceObservableDataset, *, program_voltages_V: np.ndarray | Sequence[float], cv_results: Sequence[CVResult], program_pulse_width_s: float) -> DeviceObjectiveEvaluation`
- `evaluate_memory_window_vs_programming_time_objective(dataset: DeviceObservableDataset, *, programming_times_s: np.ndarray | Sequence[float], cv_results: Sequence[CVResult], program_voltage_V: float) -> DeviceObjectiveEvaluation`
- `evaluate_retention_objective(dataset: DeviceObservableDataset, result: RetentionResult, *, retention_gate_voltage_V: float) -> DeviceObjectiveEvaluation`

## ncmemsim.dtco

`ncmemsim/dtco/__init__.py`

Explicit exports: `DTCOReport`, `build_dtco_report`, `write_dtco_report`, `SensitivityEligibility`, `SensitivityAnalysisSpec`, `SensitivityEdge`, `SensitivityAnalysisResult`, `analyze_sensitivity`, `ParetoAnalysisResult`, `ParetoAnalysisSpec`, `ParetoPointResult`, `analyze_pareto`, `ConstraintEvaluation`, `ConstraintOperator`, `MetricAnalysisResult`, `MetricAnalysisSpec`, `MetricConstraint`, `MetricDefinition`, `MetricPointResult`, `ObjectiveDirection`, `analyze_sweep`, `SweepPoint`, `SweepPointResult`, `SweepResult`, `iter_cartesian_points`, `run_cartesian_sweep`, `AppliedExperimentPoint`, `BindingApplicationError`, `BindingScope`, `DesignVariable`, `DesignVariableRole`, `ExperimentSpec`, `OperatingBindingError`, `OperatingProtocol`, `ParameterBinding`, `ScalarValue`, `apply_device_binding`, `apply_device_bindings`, `apply_experiment_design_point`, `apply_experiment_point`, `apply_operating_binding`, `apply_operating_bindings`, `VariationKind`, `VariationProvenance`, `UniformVariation`, `TruncatedNormalVariation`, `VariationDefinition`, `SamplingSpec`, `SampleManifest`, `SamplingError`, `sample_variations`, `SamplePoint`, `SamplePointResult`, `PropagationResult`, `propagate_samples`, `SampleAnalysisSpec`, `SampleMetricPointResult`, `SampleAnalysisResult`, `analyze_samples`, `NominalResult`, `NominalComparison`, `evaluate_nominal`, `compare_nominal`, `RobustStatistic`, `RobustFailurePolicy`, `RobustObjective`, `RobustParetoSpec`, `RobustParetoResult`, `analyze_robust_pareto`, `RobustDTCOReport`, `build_robust_dtco_report`, `write_robust_dtco_report`


## ncmemsim.dtco.binding

`ncmemsim/dtco/binding.py`

Explicit exports: `BindingApplicationError`, `apply_device_binding`, `apply_device_bindings`, `apply_experiment_design_point`

### BindingApplicationError

Bases: `ValueError`.


- `apply_device_binding(base_device: Device, binding: ParameterBinding, value: ScalarValue) -> Device`
- `apply_device_bindings(base_device: Device, assignments: Iterable[tuple[ParameterBinding, ScalarValue]]) -> Device`
- `apply_experiment_design_point(spec: ExperimentSpec, base_device: Device, values_by_name: Mapping[str, ScalarValue]) -> Device`

## ncmemsim.dtco.metrics

`ncmemsim/dtco/metrics.py`

Explicit exports: `ObjectiveDirection`, `ConstraintOperator`, `MetricDefinition`, `MetricConstraint`, `MetricAnalysisSpec`, `ConstraintEvaluation`, `MetricPointResult`, `MetricAnalysisResult`, `analyze_sweep`

### ObjectiveDirection

Bases: `str`, `Enum`.

- Assignment `MINIMIZE = 'minimize'`.
- Assignment `MAXIMIZE = 'maximize'`.

### ConstraintOperator

Bases: `str`, `Enum`.

- Assignment `LE = '<='`.
- Assignment `GE = '>='`.

### MetricDefinition

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `path: tuple[str | int, ...]`; required declaration.
- Field `unit: str`; required declaration.
- Field `direction: ObjectiveDirection | None`; default expression `None`.
- `extract(self, output: dict[str, Any]) -> int | float`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### MetricConstraint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `metric_name: str`; required declaration.
- Field `operator: ConstraintOperator`; required declaration.
- Field `threshold: int | float`; required declaration.
- Field `unit: str`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### MetricAnalysisSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `metrics: tuple[MetricDefinition, ...]`; required declaration.
- Field `constraints: tuple[MetricConstraint, ...]`; default expression `()`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### ConstraintEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `constraint: MetricConstraint`; required declaration.
- Field `value: int | float`; required declaration.
- `satisfied(self) -> bool`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### MetricPointResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: SweepPointResult`; required declaration.
- Field `status: str`; required declaration.
- Field `metric_values: tuple[tuple[str, int | float], ...]`; default expression `()`.
- Field `constraints: tuple[ConstraintEvaluation, ...]`; default expression `()`.
- Field `failure_stage: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- Field `error_message: str | None`; default expression `None`.
- `metrics(self) -> dict[str, int | float]`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### MetricAnalysisResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: MetricAnalysisSpec`; required declaration.
- Field `source_sweep: SweepResult`; required declaration.
- Field `points: tuple[MetricPointResult, ...]`; required declaration.
- `feasible_count(self) -> int`; `property`.
- `infeasible_count(self) -> int`; `property`.
- `failure_count(self) -> int`; `property`.
- `analysis_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `analyze_sweep(sweep: SweepResult, spec: MetricAnalysisSpec) -> MetricAnalysisResult`

## ncmemsim.dtco.operating

`ncmemsim/dtco/operating.py`

Explicit exports: `AppliedExperimentPoint`, `OperatingBindingError`, `OperatingProtocol`, `apply_experiment_point`, `apply_operating_binding`, `apply_operating_bindings`

### OperatingBindingError

Bases: `ValueError`.


### AppliedExperimentPoint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `device: Device`; required declaration.
- Field `operating_protocol: OperatingProtocol`; required declaration.
- Field `values_by_name: tuple[tuple[str, ScalarValue], ...]`; required declaration.

- `apply_operating_binding(base_protocol: OperatingProtocol, binding: ParameterBinding, value: ScalarValue) -> OperatingProtocol`
- `apply_operating_bindings(base_protocol: OperatingProtocol, assignments: Iterable[tuple[ParameterBinding, ScalarValue]]) -> OperatingProtocol`
- `apply_experiment_point(spec: ExperimentSpec, base_device: Device, base_protocol: OperatingProtocol, values_by_name: Mapping[str, ScalarValue]) -> AppliedExperimentPoint`

## ncmemsim.dtco.pareto

`ncmemsim/dtco/pareto.py`

Explicit exports: `ParetoAnalysisSpec`, `ParetoPointResult`, `ParetoAnalysisResult`, `analyze_pareto`

### ParetoAnalysisSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `objective_names: tuple[str, ...]`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### ParetoPointResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: MetricPointResult`; required declaration.
- Field `rank: int | None`; required declaration.
- Field `objective_values: tuple[tuple[str, int | float], ...]`; default expression `()`.
- `exclusion_reason(self) -> str | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### ParetoAnalysisResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: ParetoAnalysisSpec`; required declaration.
- Field `source_analysis: MetricAnalysisResult`; required declaration.
- Field `points: tuple[ParetoPointResult, ...]`; required declaration.
- Field `fronts: tuple[tuple[int, ...], ...]`; required declaration.
- `pareto_indices(self) -> tuple[int, ...]`; `property`.
- `ranked_count(self) -> int`; `property`.
- `excluded_count(self) -> int`; `property`.
- `analysis_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `analyze_pareto(analysis: MetricAnalysisResult, spec: ParetoAnalysisSpec | None=None) -> ParetoAnalysisResult`

## ncmemsim.dtco.propagation

`ncmemsim/dtco/propagation.py`

Explicit exports: `SamplePoint`, `SamplePointResult`, `PropagationResult`, `propagate_samples`

### SamplePoint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `manifest_hash: str`; required declaration.
- Field `index: int`; required declaration.
- Field `values_by_name: tuple[tuple[str, ScalarValue], ...]`; required declaration.
- `assignments(self) -> dict[str, ScalarValue]`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `point_hash(self) -> str`; `property`.

### SamplePointResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `point: SamplePoint`; required declaration.
- Field `status: str`; required declaration.
- Field `output_json: str | None`; default expression `None`.
- Field `failure_stage: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- Field `error_message: str | None`; default expression `None`.
- `output(self) -> dict[str, Any] | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

### PropagationResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `manifest: SampleManifest`; required declaration.
- Field `study_json: str`; required declaration.
- Field `points: tuple[SamplePointResult, ...]`; required declaration.
- `nominal_hash(self) -> str`; `property`.
- `study_hash(self) -> str`; `property`.
- `success_count(self) -> int`; `property`.
- `failure_count(self) -> int`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `propagate_samples(manifest: SampleManifest, base_device: Device, evaluator: SampleEvaluator, *, evaluation_id: str, evaluation_parameters: dict[str, Any] | None=None, base_protocol: OperatingProtocol | None=None) -> PropagationResult`

## ncmemsim.dtco.reporting

`ncmemsim/dtco/reporting.py`

Explicit exports: `DTCOReport`, `build_dtco_report`, `write_dtco_report`

### DTCOReport

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `report_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `from_json(cls, value: str) -> DTCOReport`; `classmethod`.
- `points_csv(self) -> str`.
- `sensitivity_csv(self) -> str`.
- `to_markdown(self) -> str`.

- `build_dtco_report(analysis: MetricAnalysisResult, *, name: str='DTCO report', pareto: ParetoAnalysisResult | None=None, sensitivity: SensitivityAnalysisResult | None=None, metadata: dict[str, Any] | None=None) -> DTCOReport`
- `write_dtco_report(report: DTCOReport, output_dir: str | Path) -> tuple[Path, ...]`

## ncmemsim.dtco.robust

`ncmemsim/dtco/robust.py`

Explicit exports: `NominalResult`, `NominalComparison`, `evaluate_nominal`, `compare_nominal`, `RobustStatistic`, `RobustFailurePolicy`, `RobustObjective`, `RobustParetoSpec`, `RobustParetoResult`, `analyze_robust_pareto`

### NominalResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `nominal_json: str`; required declaration.
- Field `evaluation_json: str`; required declaration.
- Field `status: str`; required declaration.
- Field `output_json: str | None`; default expression `None`.
- Field `failure_stage: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- Field `error_message: str | None`; default expression `None`.
- Field `runtime_json: str`; default expression `field(init=False, repr=False)`.
- `nominal_hash(self) -> str`; `property`.
- `output(self) -> dict[str, Any] | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

- `evaluate_nominal(base_device: Device, evaluator: Callable, *, evaluation_id: str, evaluation_parameters: dict[str, Any] | None=None, base_protocol: OperatingProtocol | None=None) -> NominalResult`
### NominalComparison

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: SampleAnalysisResult`; required declaration.
- Field `nominal: NominalResult`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `compare_nominal(source: SampleAnalysisResult, nominal: NominalResult) -> NominalComparison`
### RobustStatistic

Bases: `str`, `Enum`.

- Assignment `MEAN = 'mean'`.
- Assignment `MINIMUM = 'minimum'`.
- Assignment `MAXIMUM = 'maximum'`.
- Assignment `STANDARD_DEVIATION = 'standard_deviation'`.
- Assignment `QUANTILE = 'quantile'`.

### RobustFailurePolicy

Bases: `str`, `Enum`.

- Assignment `REQUIRE_NO_FAILURES = 'require_no_failures'`.
- Assignment `ALLOW_ASSESSED_WITH_FAILURES = 'allow_assessed_with_failures'`.

### RobustObjective

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `metric_name: str`; required declaration.
- Field `unit: str`; required declaration.
- Field `direction: ObjectiveDirection`; required declaration.
- Field `statistic: RobustStatistic`; required declaration.
- Field `quantile: float | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### RobustParetoSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `objectives: tuple[RobustObjective, ...]`; required declaration.
- Field `failure_policy: RobustFailurePolicy`; required declaration.
- Field `minimum_assessed_count: int`; required declaration.
- Field `minimum_observed_feasible_fraction: float`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### RobustParetoResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: RobustParetoSpec`; required declaration.
- Field `sources: tuple[SampleAnalysisResult, ...]`; required declaration.
- `fronts(self) -> tuple[tuple[int, ...], ...]`; `property`.
- `pareto_indices(self) -> tuple[int, ...]`; `property`.
- `analysis_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `analyze_robust_pareto(sources, spec: RobustParetoSpec) -> RobustParetoResult`

## ncmemsim.dtco.robust_reporting

`ncmemsim/dtco/robust_reporting.py`

Explicit exports: `RobustDTCOReport`, `build_robust_dtco_report`, `write_robust_dtco_report`

### RobustDTCOReport

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `report_hash(self)`; `property`.
- `to_dict(self)`.
- `to_json(self)`.
- `from_json(cls, value)`; `classmethod`.
- `samples_csv(self)`.
- `statistics_csv(self)`.
- `nominal_csv(self)`.
- `robust_csv(self)`.
- `to_markdown(self)`.

- `build_robust_dtco_report(analyses, *, name, nominal_comparisons=None, robust_pareto=None, metadata=None)`
- `write_robust_dtco_report(report, output_dir)`

## ncmemsim.dtco.sample_analysis

`ncmemsim/dtco/sample_analysis.py`

Explicit exports: `SampleAnalysisSpec`, `SampleMetricPointResult`, `SampleAnalysisResult`, `analyze_samples`

### SampleMetricPointResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: SamplePointResult`; required declaration.
- Field `status: str`; required declaration.
- Field `metric_values: tuple[tuple[str, int | float], ...]`; default expression `()`.
- Field `constraints: tuple[ConstraintEvaluation, ...]`; default expression `()`.
- Field `failure_stage: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- Field `error_message: str | None`; default expression `None`.
- `metrics(self) -> dict[str, int | float]`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### SampleAnalysisSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `metrics: MetricAnalysisSpec`; required declaration.
- Field `quantiles: tuple[float, ...]`; default expression `(0.05, 0.5, 0.95)`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### SampleAnalysisResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: SampleAnalysisSpec`; required declaration.
- Field `source: PropagationResult`; required declaration.
- Field `points: tuple[SampleMetricPointResult, ...]`; required declaration.
- Field `runtime_json: str`; default expression `field(init=False, repr=False)`.
- `total_count(self) -> int`; `property`.
- `assessed_count(self) -> int`; `property`.
- `feasible_count(self) -> int`; `property`.
- `infeasible_count(self) -> int`; `property`.
- `failure_count(self) -> int`; `property`.
- `observed_feasible_fraction_all_attempted(self) -> float`; `property`.
- `conditional_feasible_fraction_assessed(self) -> float | None`; `property`.
- `failure_fraction_all_attempted(self) -> float`; `property`.
- `metric_statistics(self) -> tuple[dict[str, Any], ...]`; `property`.
- `analysis_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `analyze_samples(source: PropagationResult, spec: SampleAnalysisSpec) -> SampleAnalysisResult`

## ncmemsim.dtco.sampling

`ncmemsim/dtco/sampling.py`

No explicit export list; documented entry points need individual approval.

### SamplingSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `variations: tuple[VariationDefinition, ...]`; required declaration.
- Field `seed: int`; required declaration.
- Field `sample_count: int`; required declaration.
- Field `max_draws_per_value: int`; default expression `10000`.
- `to_dict(self) -> dict[str, Any]`.
- `spec_hash(self) -> str`; `property`.

### SamplingError

Bases: `ValueError`.

Constructor: `__init__(self, sample_index: int, variation_name: str, attempts: int)`.


### SampleManifest

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: SamplingSpec`; required declaration.
- Field `values: tuple[tuple[float, ...], ...]`; required declaration.
- Field `runtime: tuple[tuple[str, str], ...]`; required declaration.
- `manifest_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `from_json(cls, text: str) -> SampleManifest`; `classmethod`.

- `sample_variations(spec: SamplingSpec) -> SampleManifest`

## ncmemsim.dtco.sensitivity

`ncmemsim/dtco/sensitivity.py`

Explicit exports: `SensitivityEligibility`, `SensitivityAnalysisSpec`, `SensitivityEdge`, `SensitivityAnalysisResult`, `analyze_sensitivity`

### SensitivityEligibility

Bases: `str`, `Enum`.

- Assignment `ASSESSED = 'assessed'`.
- Assignment `FEASIBLE_ONLY = 'feasible_only'`.

### SensitivityAnalysisSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `axis_names: tuple[str, ...]`; required declaration.
- Field `metric_names: tuple[str, ...]`; required declaration.
- Field `eligibility: SensitivityEligibility`; default expression `SensitivityEligibility.ASSESSED`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### SensitivityEdge

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `axis_name: str`; required declaration.
- Field `metric_name: str`; required declaration.
- Field `left_index: int`; required declaration.
- Field `right_index: int`; required declaration.
- Field `left_value: int | float`; required declaration.
- Field `right_value: int | float`; required declaration.
- Field `status: str`; required declaration.
- Field `slope: float | None`; default expression `None`.
- Field `reason: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### SensitivityAnalysisResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `spec: SensitivityAnalysisSpec`; required declaration.
- Field `source_analysis: MetricAnalysisResult`; required declaration.
- Field `edges: tuple[SensitivityEdge, ...]`; required declaration.
- `summaries(self) -> tuple[dict[str, Any], ...]`; `property`.
- `analysis_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `analyze_sensitivity(analysis: MetricAnalysisResult, spec: SensitivityAnalysisSpec | None=None) -> SensitivityAnalysisResult`

## ncmemsim.dtco.spec

`ncmemsim/dtco/spec.py`

Explicit exports: `BindingScope`, `DesignVariable`, `DesignVariableRole`, `ExperimentSpec`, `ParameterBinding`, `ScalarValue`

### BindingScope

Bases: `str`, `Enum`.

- Assignment `DEVICE = 'device'`.
- Assignment `OPERATING = 'operating'`.
- Assignment `MODEL = 'model'`.

### DesignVariableRole

Bases: `str`, `Enum`.

- Assignment `GEOMETRY = 'geometry'`.
- Assignment `MATERIAL = 'material'`.
- Assignment `ELECTRICAL = 'electrical'`.
- Assignment `OPTICAL = 'optical'`.
- Assignment `MODEL = 'model'`.

### ParameterBinding

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `scope: BindingScope`; required declaration.
- Field `path: tuple[str, ...]`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `binding_id(self) -> str`; `property`.

### DesignVariable

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `binding: ParameterBinding`; required declaration.
- Field `values: tuple[ScalarValue, ...]`; required declaration.
- Field `role: DesignVariableRole`; required declaration.
- Field `unit: str | None`; default expression `None`.
- Field `provenance: ParameterProvenance | None`; default expression `None`.
- `is_numeric(self) -> bool`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.

### ExperimentSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `base_device_hash: str`; required declaration.
- Field `variables: tuple[DesignVariable, ...]`; required declaration.
- Field `base_device_name: str | None`; default expression `None`.
- Field `description: str | None`; default expression `None`.
- Field `schema_version: str`; default expression `'dtco-experiment-v1'`.
- Field `base_operating_hash: str | None`; default expression `None`.
- Field `base_operating_kind: str | None`; default expression `None`.
- `from_device(cls, *, name: str, device: 'Device', variables: Iterable[DesignVariable], description: str | None=None, operating_protocol: Any | None=None) -> 'ExperimentSpec'`; `classmethod`.
- `to_dict(self) -> dict[str, Any]`.
- `experiment_hash(self) -> str`; `property`.
- `design_point_count(self) -> int`; `property`.
- `matches_device(self, device: 'Device') -> bool`.
- `require_matching_device(self, device: 'Device') -> None`.
- `matches_operating(self, operating_protocol: Any) -> bool`.
- `require_matching_operating(self, operating_protocol: Any) -> None`.


## ncmemsim.dtco.sweep

`ncmemsim/dtco/sweep.py`

Explicit exports: `SweepPoint`, `SweepPointResult`, `SweepResult`, `iter_cartesian_points`, `run_cartesian_sweep`

### SweepPoint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `experiment_hash: str`; required declaration.
- Field `index: int`; required declaration.
- Field `values_by_name: tuple[tuple[str, ScalarValue], ...]`; required declaration.
- `assignments(self) -> dict[str, ScalarValue]`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `point_hash(self) -> str`; `property`.

- `iter_cartesian_points(spec: ExperimentSpec) -> Iterator[SweepPoint]`
### SweepPointResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `point: SweepPoint`; required declaration.
- Field `status: str`; required declaration.
- Field `output_json: str | None`; default expression `None`.
- Field `failure_stage: str | None`; default expression `None`.
- Field `error_type: str | None`; default expression `None`.
- Field `error_message: str | None`; default expression `None`.
- `output(self) -> dict[str, Any] | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

### SweepResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `experiment_json: str`; required declaration.
- Field `evaluation_json: str`; required declaration.
- Field `points: tuple[SweepPointResult, ...]`; required declaration.
- `experiment_hash(self) -> str`; `property`.
- `success_count(self) -> int`; `property`.
- `failure_count(self) -> int`; `property`.
- `sweep_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `to_json(self) -> str`.
- `result_hash(self) -> str`; `property`.

- `run_cartesian_sweep(spec: ExperimentSpec, base_device: Device, evaluator: Evaluator, *, evaluation_id: str, evaluation_parameters: dict[str, Any] | None=None, base_protocol: OperatingProtocol | None=None) -> SweepResult`

## ncmemsim.dtco.variation

`ncmemsim/dtco/variation.py`

No explicit export list; documented entry points need individual approval.

### VariationKind

Bases: `str`, `Enum`.

- Assignment `FABRICATION = 'fabrication'`.
- Assignment `PARAMETER_ESTIMATION = 'parameter_estimation'`.

### UniformVariation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `lower: float`; required declaration.
- Field `upper: float`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

### TruncatedNormalVariation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `lower: float`; required declaration.
- Field `upper: float`; required declaration.
- Field `mean: float`; required declaration.
- Field `standard_deviation: float`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

### VariationProvenance

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: str`; required declaration.
- Field `applicability: str`; required declaration.
- Field `notes: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### VariationDefinition

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `binding: ParameterBinding`; required declaration.
- Field `distribution: UniformVariation | TruncatedNormalVariation`; required declaration.
- Field `unit: str`; required declaration.
- Field `kind: VariationKind`; required declaration.
- Field `provenance: VariationProvenance`; required declaration.
- `validate_context(self, device: Device, protocol: OperatingProtocol | None=None) -> None`.
- `to_dict(self) -> dict[str, Any]`.
- `definition_hash(self) -> str`; `property`.


## ncmemsim.electro_optical_program_protocol

`ncmemsim/electro_optical_program_protocol.py`

Explicit exports: `ElectroOpticalProgramPulseReadProtocol`, `ElectroOpticalProgramPulseReadResult`, `run_electro_optical_program_pulse_read`

### ElectroOpticalProgramPulseReadProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `electrical_protocol: ProgramPulseReadProtocol`; required declaration.
- Field `light_source: LightSource`; required declaration.
- Field `photo_weights: PhotoTransitionWeights`; required declaration.
- Field `occupancy_integrator: str`; default expression `'explicit_euler'`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### ElectroOpticalProgramPulseReadResult

Bases: none.

Decorators: `dataclass`.

- Field `protocol: ElectroOpticalProgramPulseReadProtocol`; required declaration.
- Field `photo_config: PhotoTransitionConfig`; required declaration.
- Field `initial_state: DeviceState`; required declaration.
- Field `programmed_state: DeviceState`; required declaration.
- Field `read_state: DeviceState`; required declaration.
- Field `delta_vfb_V: float`; required declaration.
- Field `delta_vfb_by_fg_V: np.ndarray`; required declaration.
- Field `qfg_C_m2: float`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray`; required declaration.
- Field `mean_occupation: float`; required declaration.
- Field `mean_occupation_by_fg: np.ndarray`; required declaration.
- Field `absorbed_photon_flux_m2_s: float`; required declaration.
- Field `absorbed_photon_flux_by_fg_m2_s: np.ndarray`; required declaration.
- Field `photo_transition_rate_s: float`; required declaration.
- Field `photo_transition_rate_by_fg_s: np.ndarray`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

- `run_electro_optical_program_pulse_read(simulator: Simulator, protocol: ElectroOpticalProgramPulseReadProtocol, *, photo_config: PhotoTransitionConfig, initial_state: DeviceState | None=None) -> ElectroOpticalProgramPulseReadResult`

## ncmemsim.electrostatics

`ncmemsim/electrostatics.py`

No explicit export list; documented entry points need individual approval.

### SemiconductorConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `silicon_eps_r: float`; default expression `11.7`.
- Field `intrinsic_density_m3: float`; default expression `1e+16`.
- Field `electron_affinity_eV: float`; default expression `4.05`.
- Field `bandgap_eV: float`; default expression `1.12`.
- Field `psi_max_V: float`; default expression `0.9`.
- Field `transition_voltage_V: float`; default expression `0.65`.
- Field `transition_width_V: float`; default expression `0.22`.
- Field `accumulation_factor: float`; default expression `40.0`.

### ElectrostaticsResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `cox_F_m2: float`; required declaration.
- Field `vfb0_V: float`; required declaration.
- Field `qfg_C_m2: float`; required declaration.
- Field `vfb_V: float`; required declaration.
- Field `veff_V: float`; required declaration.
- Field `capacitance_F_m2: float`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray | None`; default expression `None`.
- Field `coupling: CouplingResult | None`; default expression `None`.
- Field `local_fields_by_fg_V_m: np.ndarray | None`; default expression `None`.
- Field `local_potentials_by_fg_V: np.ndarray | None`; default expression `None`.
- Field `field_profile: FieldProfile | None`; default expression `None`.
- `delta_vfb_V(self) -> float`; `property`.
- `delta_vfb_by_fg_V(self) -> np.ndarray`; `property`.

### ElectrostaticsEngine

Bases: none.

Constructor: `__init__(self, semiconductor: SemiconductorConfig | None=None, coupling_model: CouplingModel | None=None, field_solver: FieldSolver1D | None=None)`.

- `equivalent_capacitance(self, device) -> float`.
- `fermi_potential(self, device) -> float`.
- `flatband_zero(self, device, qfix_C_m2: float=0.0, qit_C_m2: float=0.0) -> float`.
- `dynamic_flatband(vfb0_V: float, qfg_C_m2: float, cox_F_m2: float) -> float`; `staticmethod`.
- `surface_potential_proxy(self, veff_V)`.
- `semiconductor_capacitance(self, veff_V, cox_F_m2: float, substrate_doping_m3: float)`.
- `mos_capacitance(self, veff_V, device)`.
- `evaluate(self, device, gate_voltage_V: float, qfg_C_m2, qfix_C_m2: float=0.0, qit_C_m2: float=0.0) -> ElectrostaticsResult`.
- `voltage_drops(self, device, applied_voltage_V: float) -> dict[str, float]`.
- `local_fields_V_m(self, device, applied_voltage_V: float) -> dict[str, float]`.
- `field_profile(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> FieldProfile`.
- `local_fields_at_fgs_V_m(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> np.ndarray`.


## ncmemsim.experimental

`ncmemsim/experimental.py`

Explicit exports: `ConditionValue`, `DeviceObservableDataset`, `ExperimentalCondition`, `ExperimentalDatasetMetadata`, `OpticalAbsorptionDataset`

### ExperimentalDatasetMetadata

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `dataset_id: str`; required declaration.
- Field `source: str`; required declaration.
- Field `doi: str | None`; default expression `None`.
- Field `sample_id: str | None`; default expression `None`.
- Field `temperature_K: float | None`; default expression `None`.
- Field `temperature_description: str | None`; default expression `None`.
- Field `notes: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### OpticalAbsorptionDataset

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `wavelength_nm: np.ndarray`; required declaration.
- Field `absorption_coefficient_m_inv: np.ndarray`; required declaration.
- Field `sn_fraction: float`; required declaration.
- Field `metadata: ExperimentalDatasetMetadata`; required declaration.
- Field `absorption_uncertainty_m_inv: np.ndarray | None`; default expression `None`.
- `n_points(self) -> int`; `property`.
- `has_uncertainty(self) -> bool`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `dataset_hash(self) -> str`.

### ExperimentalCondition

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `value: ConditionValue`; required declaration.
- Field `unit: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### DeviceObservableDataset

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `independent_variable_name: str`; required declaration.
- Field `independent_variable_unit: str | None`; required declaration.
- Field `independent_values: np.ndarray`; required declaration.
- Field `observable_name: str`; required declaration.
- Field `observable_unit: str | None`; required declaration.
- Field `observed_values: np.ndarray`; required declaration.
- Field `metadata: ExperimentalDatasetMetadata`; required declaration.
- Field `observed_uncertainty: np.ndarray | None`; default expression `None`.
- Field `conditions: tuple[ExperimentalCondition, ...]`; default expression `()`.
- `n_points(self) -> int`; `property`.
- `has_uncertainty(self) -> bool`; `property`.
- `condition_dict(self) -> dict[str, ConditionValue]`; `property`.
- `to_dict(self) -> dict[str, Any]`.
- `dataset_hash(self) -> str`.


## ncmemsim.fieldsolver

`ncmemsim/fieldsolver.py`

No explicit export list; documented entry points need individual approval.

### FieldProfile

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `z_nm: np.ndarray`; required declaration.
- Field `potential_V: np.ndarray`; required declaration.
- Field `electric_field_V_m: np.ndarray`; required declaration.
- Field `segment_layer_names: tuple[str, ...]`; required declaration.
- Field `local_fields_by_fg_V_m: np.ndarray`; required declaration.
- Field `local_potentials_by_fg_V: np.ndarray`; required declaration.
- Field `gate_side_displacement_C_m2: float`; required declaration.
- `total_voltage_V(self) -> float`; `property`.
- `field_at_nm(self, z_nm: float) -> float`.
- `potential_at_nm(self, z_nm: float) -> float`.

### FieldSolver1D

Bases: none.

- `solve(self, device, applied_voltage_V: float, qfg_by_fg_C_m2=None) -> FieldProfile`.


## ncmemsim.fit_diagnostics

`ncmemsim/fit_diagnostics.py`

Explicit exports: `FitUncertaintyDiagnostics`, `analyze_fit_uncertainty`

### FitUncertaintyDiagnostics

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameter_names: tuple[str, ...]`; required declaration.
- Field `n_observations: int`; required declaration.
- Field `n_parameters: int`; required declaration.
- Field `degrees_of_freedom: int`; required declaration.
- Field `jacobian_rank: int`; required declaration.
- Field `active_bound_count: int`; required declaration.
- Field `scaled_singular_values: np.ndarray`; required declaration.
- Field `scaled_condition_number: float`; required declaration.
- Field `residual_variance: float | None`; required declaration.
- Field `covariance_matrix: np.ndarray | None`; required declaration.
- Field `standard_errors: np.ndarray | None`; required declaration.
- Field `correlation_matrix: np.ndarray | None`; required declaration.
- `jacobian_full_rank(self) -> bool`; `property`.
- `locally_identifiable(self) -> bool`; `property`.
- `bound_constrained(self) -> bool`; `property`.
- `covariance_available(self) -> bool`; `property`.
- `parameter_standard_errors(self) -> dict[str, float] | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `analyze_fit_uncertainty(result: DeterministicFitResult) -> FitUncertaintyDiagnostics`

## ncmemsim.fitting

`ncmemsim/fitting.py`

Explicit exports: `DeterministicFitResult`, `FitParameter`, `FitParameterSet`, `LeastSquaresConfig`, `ObjectiveEvaluation`, `evaluate_least_squares_objective`, `least_squares_residuals`, `run_least_squares_fit`

### FitParameter

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `initial_value: float`; required declaration.
- Field `lower_bound: float`; required declaration.
- Field `upper_bound: float`; required declaration.
- Field `unit: str | None`; default expression `None`.
- Field `description: str | None`; default expression `None`.
- `contains(self, value: float) -> bool`.
- `to_dict(self) -> dict[str, Any]`.

### FitParameterSet

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameters: tuple[FitParameter, ...]`; required declaration.
- `n_parameters(self) -> int`; `property`.
- `names(self) -> tuple[str, ...]`; `property`.
- `initial_values(self) -> np.ndarray`; `property`.
- `lower_bounds(self) -> np.ndarray`; `property`.
- `upper_bounds(self) -> np.ndarray`; `property`.
- `validate_values(self, values: np.ndarray | Sequence[float]) -> np.ndarray`.
- `values_to_dict(self, values: np.ndarray | Sequence[float]) -> dict[str, float]`.
- `to_dict(self) -> dict[str, Any]`.
- `specification_hash(self) -> str`.

### LeastSquaresConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `ftol: float`; default expression `1e-08`.
- Field `xtol: float`; default expression `1e-08`.
- Field `gtol: float`; default expression `1e-08`.
- Field `max_nfev: int`; default expression `1000`.
- `to_dict(self) -> dict[str, Any]`.
- `configuration_hash(self) -> str`.

### DeterministicFitResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameter_set: FitParameterSet`; required declaration.
- Field `config: LeastSquaresConfig`; required declaration.
- Field `initial_values: np.ndarray`; required declaration.
- Field `fitted_values: np.ndarray`; required declaration.
- Field `objective_residuals: np.ndarray`; required declaration.
- Field `success: bool`; required declaration.
- Field `status: int`; required declaration.
- Field `message: str`; required declaration.
- Field `nfev: int`; required declaration.
- Field `njev: int | None`; required declaration.
- Field `optimality: float`; required declaration.
- Field `active_mask: np.ndarray`; required declaration.
- Field `scipy_version: str`; required declaration.
- Field `jacobian: np.ndarray | None`; default expression `None`.
- `objective_sum_squares(self) -> float`; `property`.
- `cost(self) -> float`; `property`.
- `parameter_specification_hash(self) -> str`; `property`.
- `solver_configuration_hash(self) -> str`; `property`.
- `initial_parameters(self) -> dict[str, float]`; `property`.
- `fitted_parameters(self) -> dict[str, float]`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### ObjectiveEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `residuals: np.ndarray`; required declaration.
- Field `objective_residuals: np.ndarray`; required declaration.
- Field `weighted: bool`; required declaration.
- Field `residual_sum_squares: float`; required declaration.
- Field `objective_sum_squares: float`; required declaration.
- Field `root_mean_square_error: float`; required declaration.
- Field `mean_absolute_error: float`; required declaration.
- Field `coefficient_of_determination: float | None`; required declaration.
- `n_points(self) -> int`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `least_squares_residuals(observed: np.ndarray | Sequence[float], predicted: np.ndarray | Sequence[float], *, uncertainty: np.ndarray | Sequence[float] | None=None) -> np.ndarray`
- `evaluate_least_squares_objective(observed: np.ndarray | Sequence[float], predicted: np.ndarray | Sequence[float], *, uncertainty: np.ndarray | Sequence[float] | None=None) -> ObjectiveEvaluation`
- `run_least_squares_fit(parameter_set: FitParameterSet, residual_function: ResidualFunction, *, config: LeastSquaresConfig | None=None) -> DeterministicFitResult`

## ncmemsim.golden

`ncmemsim/golden.py`

No explicit export list; documented entry points need individual approval.

- `reference_case(n_fgs: int) -> dict[str, Any]`
- `retention_reference_case() -> dict[str, Any]`
- `build_golden_suite() -> dict[str, Any]`
- `write_golden_suite(path: str | Path) -> Path`
- `compare_golden(actual: dict[str, Any], expected: dict[str, Any], rtol: float=1e-10, atol: float=1e-13) -> list[str]`

## ncmemsim.hashing

`ncmemsim/hashing.py`

Explicit exports: `canonical_hash`

- `canonical_hash(value: Any) -> str`

## ncmemsim.io

`ncmemsim/io.py`

Explicit exports: `load_cv_csv`, `load_memory_window_vs_program_voltage_csv`, `load_memory_window_vs_programming_time_csv`, `load_optical_absorption_csv`, `load_retention_charge_fraction_csv`, `load_retention_delta_vfb_csv`

- `load_optical_absorption_csv(path: str | Path, *, sn_fraction: float, metadata: ExperimentalDatasetMetadata) -> OpticalAbsorptionDataset`
- `load_cv_csv(path: str | Path, *, metadata: ExperimentalDatasetMetadata, sweep_direction: str, measurement_frequency_Hz: float | None=None) -> DeviceObservableDataset`
- `load_memory_window_vs_program_voltage_csv(path: str | Path, *, metadata: ExperimentalDatasetMetadata, program_pulse_width_s: float, measurement_frequency_Hz: float | None=None) -> DeviceObservableDataset`
- `load_memory_window_vs_programming_time_csv(path: str | Path, *, metadata: ExperimentalDatasetMetadata, program_voltage_V: float, measurement_frequency_Hz: float | None=None) -> DeviceObservableDataset`
- `load_retention_delta_vfb_csv(path: str | Path, *, metadata: ExperimentalDatasetMetadata, retention_gate_voltage_V: float, measurement_frequency_Hz: float | None=None) -> DeviceObservableDataset`
- `load_retention_charge_fraction_csv(path: str | Path, *, metadata: ExperimentalDatasetMetadata, retention_gate_voltage_V: float, measurement_frequency_Hz: float | None=None) -> DeviceObservableDataset`

## ncmemsim.kinetics

`ncmemsim/kinetics.py`

No explicit export list; documented entry points need individual approval.

### KineticsConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `nu0_Hz: float`; default expression `1000000000000.0`.
- Field `nu1_Hz: float`; default expression `10000000000.0`.
- Field `nu2_Hz: float`; default expression `3000000000.0`.
- Field `capacitance_eps_r: float`; default expression `8.0`.
- Field `density_profile: str`; default expression `'front_loaded'`.

### RateArrays

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `r01: np.ndarray`; required declaration.
- Field `r12: np.ndarray`; required declaration.
- Field `r21: np.ndarray`; required declaration.
- Field `r10: np.ndarray`; required declaration.
- Field `tprog: np.ndarray`; required declaration.
- Field `terase: np.ndarray`; required declaration.
- Field `field_V_m: np.ndarray`; required declaration.

### OccupancyEngine

Bases: none.

Constructor: `__init__(self, tunneling_engine, config: KineticsConfig | None=None)`.

- `nanocrystal_volume(diameter_m)`; `staticmethod`.
- `nanocrystal_density(self, diameter_m, volume_fraction)`.
- `effective_density(self, diameter_m, volume_fraction, active_fraction)`.
- `nc_capacitance(self, diameter_m)`.
- `charging_energy_J(self, diameter_m)`.
- `gamma_c(self, diameter_m, temperature_K)`.
- `grid(fg)`; `staticmethod`.
- `density_profile(self, fg, x_m)`.
- `rates(self, fg, x_m, veff_V: float, tunnel_base_distance_m: float, temperature_K: float, field_V_m: float | None=None) -> RateArrays`.
- `step(state: FloatingGateState, rates: RateArrays, dt_s: float) -> FloatingGateState`; `staticmethod`.
- `step_backward_euler(state: FloatingGateState, rates: RateArrays, dt_s: float) -> FloatingGateState`; `staticmethod`.
- `charge_density_C_m3(state, density_m3)`; `staticmethod`.
- `total_charge_C_m2(rho_C_m3, dx_m)`; `staticmethod`.
- `combine_rates(electrical: RateArrays, photo) -> RateArrays`; `staticmethod`.


## ncmemsim.layers

`ncmemsim/layers.py`

No explicit export list; documented entry points need individual approval.

### Layer

Bases: none.

Decorators: `dataclass`.

- Field `name: str`; required declaration.
- Field `material: Material`; required declaration.
- Field `thickness_nm: float`; required declaration.
- Field `role: str`; required declaration.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `validate(self)`.
- `eps_r(self)`; `property`.
- `to_dict(self)`.

### FloatingGateLayer

Bases: none.

Decorators: `dataclass`.

- Field `name: str`; required declaration.
- Field `matrix_material: Material`; required declaration.
- Field `thickness_nm: float`; required declaration.
- Field `nc_material: NanocrystalMaterial`; required declaration.
- Field `nc_diameter_nm: float`; required declaration.
- Field `nc_volume_fraction: float`; required declaration.
- Field `electrically_active_fraction: float`; required declaration.
- Field `spatial_profile: str`; default expression `'uniform'`.
- Field `grid_points: int`; default expression `31`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `validate(self)`.
- `eps_r(self)`; `property`.
- `role(self)`; `property`.
- `to_dict(self)`.


## ncmemsim.materials

`ncmemsim/materials/__init__.py`

Explicit exports: `Material`, `NanocrystalMaterial`, `HFO2`, `SIO2`, `SILICON`, `make_ge`, `make_gesn`, `GeSnModel`, `GeSnParameterSet`, `MaterialProperty`, `ParameterProvenance`, `ParameterStatus`, `registry`, `MaterialRegistry`, `BarrierModel`, `BandAlignmentResult`, `CompactOpticalMaterialModel`, `OpticalPoint`


## ncmemsim.materials.band_alignment

`ncmemsim/materials/band_alignment/__init__.py`

Explicit exports: `BarrierModel`, `BandAlignmentResult`


## ncmemsim.materials.band_alignment.barriers

`ncmemsim/materials/band_alignment/barriers.py`

No explicit export list; documented entry points need individual approval.

### BandAlignmentResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `conduction_barrier_eV: float`; required declaration.
- Field `valence_barrier_eV: float | None`; required declaration.
- Field `model: str`; required declaration.

### BarrierModel

Bases: none.

- `affinity_rule(nc: NanocrystalMaterial, oxide: Material) -> BandAlignmentResult`; `staticmethod`.
- `calibrated(conduction_barrier_eV: float, valence_barrier_eV: float | None=None) -> BandAlignmentResult`; `staticmethod`.


## ncmemsim.materials.base

`ncmemsim/materials/base.py`

No explicit export list; documented entry points need individual approval.

### Material

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `eps_r: float`; required declaration.
- Field `electron_affinity_eV: float | None`; default expression `None`.
- Field `bandgap_eV: float | None`; default expression `None`.
- Field `electron_effective_mass_m0: float | None`; default expression `None`.
- Field `hole_effective_mass_m0: float | None`; default expression `None`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- Field `properties: Mapping[str, MaterialProperty]`; default expression `field(default_factory=dict)`.
- `property_manifest(self) -> dict[str, Any]`.
- `to_dict(self) -> dict[str, Any]`.

### NanocrystalMaterial

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `sn_fraction: float`; required declaration.
- Field `eps_r_nc: float`; required declaration.
- Field `effective_mass_m0: float`; required declaration.
- Field `phi_barrier_prog_eV: float`; required declaration.
- Field `phi_barrier_erase_eV: float`; required declaration.
- Field `bandgap_eV: float | None`; default expression `None`.
- Field `electron_affinity_eV: float | None`; default expression `None`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- Field `properties: Mapping[str, MaterialProperty]`; default expression `field(default_factory=dict)`.
- Field `model_name: str`; default expression `'NanocrystalMaterial'`.
- Field `model_version: str`; default expression `'default-v1'`.
- `property_manifest(self) -> dict[str, Any]`.
- `to_dict(self) -> dict[str, Any]`.


## ncmemsim.materials.database

`ncmemsim/materials/database.py`

No explicit export list; documented entry points need individual approval.

- `get_base_property(material: str, property_name: str) -> MaterialProperty`

## ncmemsim.materials.interpolation

`ncmemsim/materials/interpolation.py`

No explicit export list; documented entry points need individual approval.

- `validate_fraction(x: float) -> float`
- `linear(x: float, a: float, b: float) -> float`
- `bowing(x: float, a: float, b: float, bowing_parameter: float=0.0) -> float`
- `vegard(x: float, a: float, b: float, bowing_parameter: float=0.0) -> float`

## ncmemsim.materials.models

`ncmemsim/materials/models/__init__.py`

Explicit exports: `make_ge`, `make_gesn`, `GeSnModel`, `GeSnParameterSet`


## ncmemsim.materials.models.ge

`ncmemsim/materials/models/ge.py`

No explicit export list; documented entry points need individual approval.

- `make_ge(*, phi_barrier_prog_eV: float=2.8, phi_barrier_erase_eV: float=2.8, parameter_set: str='default-v1') -> NanocrystalMaterial`

## ncmemsim.materials.models.gesn

`ncmemsim/materials/models/gesn.py`

No explicit export list; documented entry points need individual approval.

### GeSnParameterSet

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; default expression `'default-v1'`.
- Field `eps_bowing: float`; default expression `0.0`.
- Field `bandgap_bowing_eV: float`; default expression `2.4`.
- Field `affinity_bowing_eV: float`; default expression `0.0`.
- Field `mass_bowing_m0: float`; default expression `0.0`.
- Field `barrier_bowing_eV: float`; default expression `0.0`.
- Field `phi_ge_prog_eV: float`; default expression `2.8`.
- Field `phi_sn_prog_eV: float`; default expression `2.0`.
- Field `phi_ge_erase_eV: float`; default expression `2.8`.
- Field `phi_sn_erase_eV: float`; default expression `2.0`.

### GeSnModel

Bases: none.

Constructor: `__init__(self, composition: float, parameter_set: GeSnParameterSet | None=None)`.

- `build(self) -> NanocrystalMaterial`.

- `make_gesn(sn_fraction: float, **kwargs) -> NanocrystalMaterial`

## ncmemsim.materials.optics

`ncmemsim/materials/optics/__init__.py`

Explicit exports: `CompactOpticalMaterialModel`, `CompositeGeSnAbsorptionModel`, `EvaluationDomainStatus`, `GESN_NEAR_EDGE_FIT_PARAMETER_NAMES`, `GeSnAbsorptionParameterSet`, `GeSnNearEdgeCalibrationResult`, `GeSnNearEdgeFitResult`, `GeSnNearEdgeParameterSet`, `GeSnNearEdgeReferenceModel`, `GeSnOpticalParameterSet`, `NearEdgeBranch`, `NearEdgeOpticalPoint`, `OpticalPoint`, `OpticalValidationDomain`, `TRAN_2016_NEAR_EDGE_DOMAIN`, `TRAN_2016_NEAR_EDGE_PARAMETERS`, `direct_gap_gesn_eV`, `fit_gesn_near_edge_absorption`, `indirect_gap_gesn_eV`, `photon_energy_eV`, `phonon_occupation`, `predict_gesn_near_edge_absorption_m_inv`, `qualify_gesn_near_edge_fit`


## ncmemsim.materials.optics.domain

`ncmemsim/materials/optics/domain.py`

No explicit export list; documented entry points need individual approval.

### EvaluationDomainStatus

Bases: `str`, `Enum`.

- Assignment `WITHIN_VALIDATION_DOMAIN = 'within_validation_domain'`.
- Assignment `EXTRAPOLATED = 'extrapolated'`.

### OpticalValidationDomain

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `sn_fraction_min: float`; required declaration.
- Field `sn_fraction_max: float`; required declaration.
- Field `wavelength_min_nm: float`; required declaration.
- Field `wavelength_max_nm: float`; required declaration.
- Field `temperature_note: str | None`; default expression `None`.
- Field `doi: str | None`; default expression `None`.
- `classify(self, *, sn_fraction: float, wavelength_nm: float) -> EvaluationDomainStatus`.
- `contains(self, *, sn_fraction: float, wavelength_nm: float) -> bool`.
- `to_dict(self) -> dict[str, Any]`.


## ncmemsim.materials.optics.models

`ncmemsim/materials/optics/models.py`

No explicit export list; documented entry points need individual approval.

### OpticalPoint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `wavelength_nm: float`; required declaration.
- Field `photon_energy_eV: float`; required declaration.
- Field `absorption_coefficient_m_inv: float`; required declaration.
- Field `direct_gap_eV: float | None`; default expression `None`.
- Field `indirect_gap_eV: float | None`; default expression `None`.
- Field `alpha_direct_m_inv: float | None`; default expression `None`.
- Field `alpha_indirect_m_inv: float | None`; default expression `None`.
- Field `alpha_urbach_m_inv: float | None`; default expression `None`.
- Field `refractive_index: float | None`; default expression `None`.
- Field `extinction_coefficient: float | None`; default expression `None`.
- Field `provenance: Mapping[str, ParameterProvenance] | None`; default expression `None`.

### GeSnOpticalParameterSet

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; default expression `'gesn-optical-300K-v1'`.
- Field `temperature_K: float`; default expression `300.0`.
- Field `ge_direct_gap_eV: float`; default expression `0.7985`.
- Field `alpha_sn_direct_gap_eV: float`; default expression `-0.413`.
- Field `direct_gap_bowing_eV: float`; default expression `2.89`.
- Field `ge_indirect_gap_eV: float`; default expression `0.664`.
- Field `alpha_sn_indirect_gap_eV: float`; default expression `0.092`.
- Field `indirect_gap_bowing_eV: float`; default expression `0.89`.
- Field `absorption_prefactor_m_inv_eV_sqrt: float`; default expression `10000000.0`.
- Field `broadening_eV: float`; default expression `0.0`.

- `photon_energy_eV(wavelength_nm: float) -> float`
- `direct_gap_gesn_eV(sn_fraction: float, parameters: GeSnOpticalParameterSet | None=None) -> float`
- `indirect_gap_gesn_eV(sn_fraction: float, parameters: GeSnOpticalParameterSet | None=None) -> float`
### CompactOpticalMaterialModel

Bases: none.

Constructor: `__init__(self, parameters: GeSnOpticalParameterSet | None=None)`.

- `direct_gap_property(self, material: NanocrystalMaterial) -> MaterialProperty`.
- `indirect_gap_property(self, material: NanocrystalMaterial) -> MaterialProperty`.
- `evaluate(self, material: NanocrystalMaterial, wavelength_nm: float) -> OpticalPoint`.

### GeSnAbsorptionParameterSet

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; default expression `'gesn-absorption-compact-v1'`.
- Field `direct_prefactor_A: float`; default expression `10000000.0`.
- Field `indirect_prefactor_A: float`; default expression `1000000.0`.
- Field `phonon_energy_eV: float`; default expression `0.027`.
- Field `urbach_energy_eV: float`; default expression `0.012`.
- Field `urbach_edge_alpha_m_inv: float`; default expression `100000.0`.
- Field `temperature_K: float`; default expression `300.0`.

- `urbach_absorption_m_inv(photon_energy_eV: float, direct_gap_eV: float, parameters: GeSnAbsorptionParameterSet) -> float`
- `indirect_absorption_m_inv(photon_energy_eV: float, indirect_gap_eV: float, parameters: GeSnAbsorptionParameterSet) -> float`
- `direct_absorption_m_inv(photon_energy_eV: float, direct_gap_eV: float, parameters: GeSnAbsorptionParameterSet) -> float`
### CompositeGeSnAbsorptionModel

Bases: none.

Constructor: `__init__(self, optical_parameters: GeSnOpticalParameterSet | None=None, absorption_parameters: GeSnAbsorptionParameterSet | None=None)`.

- `evaluate(self, material: NanocrystalMaterial, wavelength_nm: float) -> OpticalPoint`.

- `phonon_occupation(phonon_energy_eV: float, temperature_K: float) -> float`

## ncmemsim.materials.optics.near_edge

`ncmemsim/materials/optics/near_edge.py`

No explicit export list; documented entry points need individual approval.

### GeSnNearEdgeParameterSet

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; default expression `TRAN_2016_PARAMETER_SET_NAME`.
- Field `direct_prefactor_A: float`; default expression `3680000.0`.
- Field `urbach_energy_eV: float`; default expression `0.01058`.
- Field `temperature_K: float`; default expression `300.0`.
- Field `provenance: Mapping[str, ParameterProvenance] | None`; default expression `None`.

### NearEdgeConnection

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `direct_gap_eV: float`; required declaration.
- Field `connection_offset_eV: float`; required declaration.
- Field `connection_energy_eV: float`; required declaration.
- Field `urbach_prefactor_m_inv: float`; required declaration.

- `derive_near_edge_connection(direct_gap_eV: float, parameters: GeSnNearEdgeParameterSet | None=None) -> NearEdgeConnection`
- `near_edge_direct_absorption_m_inv(photon_energy_eV: float, direct_gap_eV: float, parameters: GeSnNearEdgeParameterSet | None=None) -> float`
- `near_edge_urbach_absorption_m_inv(photon_energy_eV: float, direct_gap_eV: float, parameters: GeSnNearEdgeParameterSet | None=None) -> float`
### NearEdgeBranch

Bases: `str`, `Enum`.

- Assignment `URBACH = 'urbach'`.
- Assignment `DIRECT = 'direct'`.

### NearEdgeOpticalPoint

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `wavelength_nm: float`; required declaration.
- Field `photon_energy_eV: float`; required declaration.
- Field `absorption_coefficient_m_inv: float`; required declaration.
- Field `direct_gap_eV: float`; required declaration.
- Field `connection_energy_eV: float`; required declaration.
- Field `branch: NearEdgeBranch`; required declaration.
- Field `domain_status: EvaluationDomainStatus`; required declaration.
- Field `provenance: Mapping[str, ParameterProvenance]`; required declaration.

### GeSnNearEdgeReferenceModel

Bases: none.

Constructor: `__init__(self, parameters: GeSnNearEdgeParameterSet | None=None, validation_domain: OpticalValidationDomain | None=None) -> None`.

- `evaluate(self, material: NanocrystalMaterial, wavelength_nm: float) -> NearEdgeOpticalPoint`.


## ncmemsim.materials.optics.near_edge_calibration

`ncmemsim/materials/optics/near_edge_calibration.py`

Explicit exports: `GeSnNearEdgeCalibrationResult`, `qualify_gesn_near_edge_fit`

### GeSnNearEdgeCalibrationResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `fitted_parameter_set_name: str`; required declaration.
- Field `validation_dataset_id: str`; required declaration.
- Field `validation_dataset_hash: str`; required declaration.
- Field `qualification: CalibrationQualification`; required declaration.
- Field `predicted_absorption_m_inv: np.ndarray`; required declaration.
- Field `calibrated_parameter_set: GeSnNearEdgeParameterSet | None`; default expression `None`.
- `calibrated(self) -> bool`; `property`.
- `failed_criteria(self) -> tuple[str, ...]`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `qualify_gesn_near_edge_fit(fit_result: GeSnNearEdgeFitResult, validation_dataset: OpticalAbsorptionDataset, *, criteria: CalibrationCriteria, calibrated_parameter_set_name: str) -> GeSnNearEdgeCalibrationResult`

## ncmemsim.materials.optics.near_edge_fit

`ncmemsim/materials/optics/near_edge_fit.py`

Explicit exports: `GESN_NEAR_EDGE_FIT_PARAMETER_NAMES`, `GeSnNearEdgeFitResult`, `fit_gesn_near_edge_absorption`, `predict_gesn_near_edge_absorption_m_inv`

- `predict_gesn_near_edge_absorption_m_inv(wavelength_nm: np.ndarray | Sequence[float], *, sn_fraction: float, parameters: GeSnNearEdgeParameterSet) -> np.ndarray`
### GeSnNearEdgeFitResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `fitted_parameter_set: GeSnNearEdgeParameterSet`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `objective: ObjectiveEvaluation`; required declaration.
- Field `uncertainty_diagnostics: FitUncertaintyDiagnostics`; required declaration.
- Field `predicted_absorption_m_inv: np.ndarray`; required declaration.
- `weighted(self) -> bool`; `property`.
- `fitted_parameters(self) -> dict[str, float]`; `property`.
- `parameter_standard_errors(self) -> dict[str, float] | None`; `property`.
- `parameter_correlation(self) -> dict[str, dict[str, float]] | None`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `fit_gesn_near_edge_absorption(dataset: OpticalAbsorptionDataset, parameter_set: FitParameterSet, *, fitted_parameter_set_name: str, config: LeastSquaresConfig | None=None, model_temperature_K: float | None=None) -> GeSnNearEdgeFitResult`

## ncmemsim.materials.presets

`ncmemsim/materials/presets.py`

No explicit export list; documented entry points need individual approval.


## ncmemsim.materials.provenance

`ncmemsim/materials/provenance.py`

No explicit export list; documented entry points need individual approval.

### ParameterStatus

Bases: `str`, `Enum`.

- Assignment `LITERATURE = 'literature'`.
- Assignment `LITERATURE_FITTED = 'literature_fitted'`.
- Assignment `CALIBRATED = 'calibrated'`.
- Assignment `ASSUMED = 'assumed'`.
- Assignment `ESTIMATED = 'estimated'`.
- Assignment `FITTED = 'fitted'`.
- Assignment `DERIVED = 'derived'`.

### ParameterProvenance

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source: str`; required declaration.
- Field `status: ParameterStatus`; required declaration.
- Field `doi: str | None`; default expression `None`.
- Field `notes: str | None`; default expression `None`.
- Field `parameter_set: str`; default expression `'default-v1'`.
- Field `reported_uncertainty: float | None`; default expression `None`.
- Field `uncertainty_unit: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### MaterialProperty

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `value: float`; required declaration.
- Field `unit: str`; required declaration.
- Field `provenance: ParameterProvenance`; required declaration.
- Field `symbol: str | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.


## ncmemsim.materials.registry

`ncmemsim/materials/registry.py`

No explicit export list; documented entry points need individual approval.

### MaterialRegistry

Bases: none.

Constructor: `__init__(self) -> None`.

- `register(self, name: str, factory: Callable[..., Any], *, replace: bool=False) -> None`.
- `create(self, name: str, **kwargs: Any) -> Any`.
- `available(self) -> tuple[str, ...]`.


## ncmemsim.optics

`ncmemsim/optics.py`

No explicit export list; documented entry points need individual approval.

### LightSource

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `source_type: str`; required declaration.
- Field `power_density_W_m2: float`; required declaration.
- Field `enabled: bool`; default expression `True`.
- Field `spectrum_mode: str`; default expression `'compact'`.
- Field `temperature_K: float | None`; default expression `None`.
- Field `wavelength_nm: float | None`; default expression `None`.
- Field `wavelength_min_nm: float | None`; default expression `None`.
- Field `wavelength_max_nm: float | None`; default expression `None`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `is_monochromatic(self) -> bool`; `property`.
- `photon_energy_J(self) -> float`; `property`.
- `photon_energy_eV(self) -> float`; `property`.
- `photon_flux_m2_s(self) -> float`; `property`.
- `incandescent(cls, power_density_W_m2: float, temperature_K: float=2800.0, wavelength_min_nm: float=350.0, wavelength_max_nm: float=2500.0, name: str='Incandescent lamp', spectrum_mode: str='compact') -> LightSource`; `classmethod`.
- `led(cls, wavelength_nm: float, power_density_W_m2: float, name: str | None=None) -> LightSource`; `classmethod`.
- `laser(cls, wavelength_nm: float, power_density_W_m2: float, name: str | None=None) -> LightSource`; `classmethod`.
- `to_dict(self) -> dict[str, Any]`.

### AbsorbedPhotonFlux

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `incident_flux_m2_s: float`; required declaration.
- Field `absorbed_flux_m2_s: float`; required declaration.
- Field `transmitted_flux_m2_s: float`; required declaration.
- Field `absorption_fraction: float`; required declaration.
- Field `transmission_fraction: float`; required declaration.
- Field `absorption_coefficient_m_inv: float`; required declaration.
- Field `thickness_m: float`; required declaration.
- `average_generation_rate_m3_s(self) -> float`; `property`.

- `beer_lambert_absorption_fraction(absorption_coefficient_m_inv: float, thickness_m: float) -> float`
- `absorbed_photon_flux(incident_flux_m2_s: float, absorption_coefficient_m_inv: float, thickness_m: float) -> AbsorbedPhotonFlux`
- `effective_nc_absorption_coefficient(nc_absorption_coefficient_m_inv: float, nc_volume_fraction: float) -> float`
- `floating_gate_absorbed_photon_flux(incident_flux_m2_s: float, nc_absorption_coefficient_m_inv: float, layer) -> AbsorbedPhotonFlux`
### FloatingGateOpticalResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `source_name: str`; required declaration.
- Field `wavelength_nm: float`; required declaration.
- Field `photon_energy_eV: float`; required declaration.
- Field `incident_power_density_W_m2: float`; required declaration.
- Field `incident_photon_flux_m2_s: float`; required declaration.
- Field `average_generation_rate_m3_s: float`; required declaration.
- Field `nc_absorption_coefficient_m_inv: float`; required declaration.
- Field `effective_absorption_coefficient_m_inv: float`; required declaration.
- Field `absorption_fraction: float`; required declaration.
- Field `absorbed_photon_flux_m2_s: float`; required declaration.
- Field `transmitted_photon_flux_m2_s: float`; required declaration.
- Field `alpha_direct_m_inv: float | None`; default expression `None`.
- Field `alpha_indirect_m_inv: float | None`; default expression `None`.
- Field `alpha_urbach_m_inv: float | None`; default expression `None`.
- Field `direct_gap_eV: float | None`; default expression `None`.
- Field `indirect_gap_eV: float | None`; default expression `None`.
- Field `provenance: Any`; default expression `None`.

- `evaluate_floating_gate_optical_absorption(source: LightSource, layer, optical_model: CompositeGeSnAbsorptionModel | None=None) -> FloatingGateOpticalResult`

## ncmemsim.paired_pulse_protocol

`ncmemsim/paired_pulse_protocol.py`

Explicit exports: `PairedPulseMemoryProtocol`, `PairedPulseMemoryResult`, `PulseBranchResult`, `run_paired_pulse_memory_protocol`

### PairedPulseMemoryProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `program_voltage_V: float`; required declaration.
- Field `program_time_s: float`; required declaration.
- Field `erase_voltage_V: float`; required declaration.
- Field `erase_time_s: float`; required declaration.
- Field `read_voltage_V: float`; default expression `0.0`.
- Field `pulse_internal_dt_s: float | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### PulseBranchResult

Bases: none.

Decorators: `dataclass`.

- Field `role: PulseRole`; required declaration.
- Field `pulse_voltage_V: float`; required declaration.
- Field `pulse_time_s: float`; required declaration.
- Field `initial_state: DeviceState`; required declaration.
- Field `pulsed_state: DeviceState`; required declaration.
- Field `read_state: DeviceState`; required declaration.
- Field `delta_vfb_V: float`; required declaration.
- Field `delta_vfb_by_fg_V: np.ndarray`; required declaration.
- Field `qfg_C_m2: float`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray`; required declaration.
- Field `mean_occupation: float`; required declaration.
- Field `mean_occupation_by_fg: np.ndarray`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

### PairedPulseMemoryResult

Bases: none.

Decorators: `dataclass`.

- Field `protocol: PairedPulseMemoryProtocol`; required declaration.
- Field `reference_state: DeviceState`; required declaration.
- Field `program: PulseBranchResult`; required declaration.
- Field `erase: PulseBranchResult`; required declaration.
- `memory_window_V(self) -> float`; `property`.
- `memory_window_magnitude_V(self) -> float`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `run_paired_pulse_memory_protocol(simulator: Simulator, protocol: PairedPulseMemoryProtocol, *, reference_state: DeviceState | None=None) -> PairedPulseMemoryResult`

## ncmemsim.photo

`ncmemsim/photo.py`

No explicit export list; documented entry points need individual approval.

- `nanocrystal_volume_m3(nc_diameter_nm: float) -> float`
- `nanocrystal_number_density_m3(nc_diameter_nm: float, nc_volume_fraction: float) -> float`
- `absorbed_photon_rate_per_nc_s(average_generation_rate_m3_s: float, nc_diameter_nm: float, nc_volume_fraction: float) -> float`
### PhotoTransitionConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `photo_capture_efficiency: float`; default expression `0.001`.

- `photo_transition_rate_s(absorbed_photon_rate_per_nc_s: float, config: PhotoTransitionConfig | None=None) -> float`
### PhotoTransitionWeights

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `r01: float`; default expression `1.0`.
- Field `r12: float`; default expression `1.0`.
- Field `r10: float`; default expression `0.0`.
- Field `r21: float`; default expression `0.0`.

### PhotoTransitionRates

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `r01: np.ndarray`; required declaration.
- Field `r12: np.ndarray`; required declaration.
- Field `r21: np.ndarray`; required declaration.
- Field `r10: np.ndarray`; required declaration.

### PhotoTransitionEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `rates: PhotoTransitionRates`; required declaration.
- Field `absorbed_photon_rate_per_nc_s: float`; required declaration.
- Field `base_photo_transition_rate_s: float`; required declaration.
- Field `photo_capture_efficiency: float`; required declaration.

- `evaluate_photo_transition_rates(optical_result, layer, config: PhotoTransitionConfig | None=None, weights: PhotoTransitionWeights | None=None) -> PhotoTransitionEvaluation`
- `photo_transition_rate_arrays(base_photo_rate_s: float, grid_size: int, weights: PhotoTransitionWeights | None=None) -> PhotoTransitionRates`
- `photo_transition_rates_from_optical_result(optical_result, layer, config: PhotoTransitionConfig | None=None, weights: PhotoTransitionWeights | None=None) -> PhotoTransitionRates`

## ncmemsim.photo_calibration

`ncmemsim/photo_calibration.py`

Explicit exports: `CalibratedPhotoCaptureEfficiency`, `DevicePhotoCalibrationResult`, `qualify_photo_capture_efficiency_fit`

### CalibratedPhotoCaptureEfficiency

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `parameter_name: str`; required declaration.
- Field `value: float`; required declaration.
- Field `source: str`; required declaration.
- Field `training_dataset_collection_hash: str`; required declaration.
- Field `validation_dataset_hash: str`; required declaration.
- Field `validation_protocol_hash: str`; required declaration.
- Field `qualification_hash: str`; required declaration.
- Field `status: str`; default expression `'CALIBRATED'`.
- `target(self) -> DeviceFitTarget`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### DevicePhotoCalibrationResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `training_dataset_ids: tuple[str, ...]`; required declaration.
- Field `training_dataset_hashes: tuple[str, ...]`; required declaration.
- Field `training_dataset_collection_hash: str`; required declaration.
- Field `validation_dataset_id: str`; required declaration.
- Field `validation_dataset_hash: str`; required declaration.
- Field `validation_protocol: ElectroOpticalProgramTimeFitProtocol`; required declaration.
- Field `qualification: CalibrationQualification`; required declaration.
- Field `prediction: ElectroOpticalProgramTimePrediction`; required declaration.
- Field `calibrated_parameter: CalibratedPhotoCaptureEfficiency | None`; default expression `None`.
- Field `calibrated_photo_config: PhotoTransitionConfig | None`; default expression `None`.
- `calibrated(self) -> bool`; `property`.
- `scientific_status(self) -> str`; `property`.
- `failed_criteria(self) -> tuple[str, ...]`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `qualify_photo_capture_efficiency_fit(fit_result: DevicePhotoMultiConditionFitResult, validation_dataset: DeviceObservableDataset, validation_protocol: ElectroOpticalProgramTimeFitProtocol, *, criteria: CalibrationCriteria) -> DevicePhotoCalibrationResult`

## ncmemsim.photo_program_fit

`ncmemsim/photo_program_fit.py`

Explicit exports: `DevicePhotoMultiConditionFitResult`, `DevicePhotoProgramTimeFitResult`, `ElectroOpticalProgramTimeFitProtocol`, `ElectroOpticalProgramTimePrediction`, `fit_single_parameter_photo_capture_efficiency_multi_condition`, `fit_single_parameter_photo_capture_efficiency_vs_programming_time`, `predict_electro_optical_delta_vfb_vs_programming_time`

### ElectroOpticalProgramTimeFitProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `program_voltage_V: float`; required declaration.
- Field `light_source: LightSource`; required declaration.
- Field `photo_weights: PhotoTransitionWeights`; required declaration.
- Field `read_voltage_V: float`; default expression `0.0`.
- Field `program_internal_dt_s: float | None`; default expression `None`.
- Field `occupancy_integrator: str`; default expression `'explicit_euler'`.
- `pulse_protocol(self, programming_time_s: float) -> ElectroOpticalProgramPulseReadProtocol`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### ElectroOpticalProgramTimePrediction

Bases: none.

Decorators: `dataclass`.

- Field `programming_times_s: np.ndarray`; required declaration.
- Field `predicted_delta_vfb_V: np.ndarray`; required declaration.
- Field `pulse_results: tuple[ElectroOpticalProgramPulseReadResult, ...]`; required declaration.

- `predict_electro_optical_delta_vfb_vs_programming_time(simulator: Simulator, programming_times_s: Sequence[float] | np.ndarray, protocol: ElectroOpticalProgramTimeFitProtocol, *, photo_config: PhotoTransitionConfig, initial_state: DeviceState | None=None) -> ElectroOpticalProgramTimePrediction`
### DevicePhotoProgramTimeFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `protocol: ElectroOpticalProgramTimeFitProtocol`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `objective: ObjectiveEvaluation`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `prediction: ElectroOpticalProgramTimePrediction`; required declaration.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `fit_single_parameter_photo_capture_efficiency_vs_programming_time(dataset: DeviceObservableDataset, *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, base_photo_config: PhotoTransitionConfig, calibration_spec: DeviceCalibrationSpec, protocol: ElectroOpticalProgramTimeFitProtocol, least_squares_config: LeastSquaresConfig | None=None) -> DevicePhotoProgramTimeFitResult`
### DevicePhotoMultiConditionFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_ids: tuple[str, ...]`; required declaration.
- Field `dataset_hashes: tuple[str, ...]`; required declaration.
- Field `protocols: tuple[ElectroOpticalProgramTimeFitProtocol, ...]`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `uncertainty_diagnostics: FitUncertaintyDiagnostics`; required declaration.
- Field `objectives: tuple[ObjectiveEvaluation, ...]`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `predictions: tuple[ElectroOpticalProgramTimePrediction, ...]`; required declaration.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `locally_identifiable(self) -> bool`; `property`.
- `parameter_standard_errors(self) -> dict[str, float] | None`; `property`.
- `condition_scaled_jacobian_l2_norms(self) -> tuple[float, ...]`; `property`.
- `n_conditions(self) -> int`; `property`.
- `n_observations(self) -> int`; `property`.
- `weighted(self) -> bool`; `property`.
- `joint_objective_residuals(self) -> np.ndarray`; `property`.
- `joint_raw_residuals_V(self) -> np.ndarray`; `property`.
- `joint_objective_sum_squares(self) -> float`; `property`.
- `joint_root_mean_square_error_V(self) -> float`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `fit_single_parameter_photo_capture_efficiency_multi_condition(datasets: Sequence[DeviceObservableDataset], protocols: Sequence[ElectroOpticalProgramTimeFitProtocol], *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, base_photo_config: PhotoTransitionConfig, calibration_spec: DeviceCalibrationSpec, least_squares_config: LeastSquaresConfig | None=None) -> DevicePhotoMultiConditionFitResult`

## ncmemsim.physics

`ncmemsim/physics.py`

No explicit export list; documented entry points need individual approval.

### PhysicsModel

Bases: none.

Decorators: `dataclass`.

- Field `electrostatics: ElectrostaticsEngine`; required declaration.
- Field `tunneling: TunnelingEngine`; required declaration.
- Field `occupancy: OccupancyEngine`; required declaration.
- Field `transport: TransportEngine`; required declaration.
- `default(cls)`; `classmethod`.


## ncmemsim.plotting

`ncmemsim/plotting.py`

No explicit export list; documented entry points need individual approval.


## ncmemsim.program_fit

`ncmemsim/program_fit.py`

Explicit exports: `DeviceProgramTimeFitResult`, `ProgramTimeFitProtocol`, `ProgramTimePrediction`, `fit_single_parameter_delta_vfb_vs_programming_time`, `predict_delta_vfb_vs_programming_time`

### ProgramTimeFitProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `program_voltage_V: float`; required declaration.
- Field `read_voltage_V: float`; default expression `0.0`.
- Field `program_internal_dt_s: float | None`; default expression `None`.
- `pulse_protocol(self, programming_time_s: float) -> ProgramPulseReadProtocol`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### ProgramTimePrediction

Bases: none.

Decorators: `dataclass`.

- Field `programming_times_s: np.ndarray`; required declaration.
- Field `predicted_delta_vfb_V: np.ndarray`; required declaration.
- Field `pulse_results: tuple[ProgramPulseReadResult, ...]`; required declaration.

### DeviceProgramTimeFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `protocol: ProgramTimeFitProtocol`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `objective: ObjectiveEvaluation`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `prediction: ProgramTimePrediction`; required declaration.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `predict_delta_vfb_vs_programming_time(simulator: Simulator, programming_times_s: Sequence[float] | np.ndarray, protocol: ProgramTimeFitProtocol, *, initial_state: DeviceState | None=None) -> ProgramTimePrediction`
- `fit_single_parameter_delta_vfb_vs_programming_time(dataset: DeviceObservableDataset, *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, calibration_spec: DeviceCalibrationSpec, protocol: ProgramTimeFitProtocol, least_squares_config: LeastSquaresConfig | None=None) -> DeviceProgramTimeFitResult`

## ncmemsim.program_protocol

`ncmemsim/program_protocol.py`

Explicit exports: `ProgramPulseReadProtocol`, `ProgramPulseReadResult`, `run_program_pulse_read`

### ProgramPulseReadProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `program_voltage_V: float`; required declaration.
- Field `programming_time_s: float`; required declaration.
- Field `read_voltage_V: float`; default expression `0.0`.
- Field `program_internal_dt_s: float | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### ProgramPulseReadResult

Bases: none.

Decorators: `dataclass`.

- Field `protocol: ProgramPulseReadProtocol`; required declaration.
- Field `initial_state: DeviceState`; required declaration.
- Field `programmed_state: DeviceState`; required declaration.
- Field `read_state: DeviceState`; required declaration.
- Field `delta_vfb_V: float`; required declaration.
- Field `delta_vfb_by_fg_V: np.ndarray`; required declaration.
- Field `qfg_C_m2: float`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray`; required declaration.
- Field `mean_occupation: float`; required declaration.
- Field `mean_occupation_by_fg: np.ndarray`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

- `run_program_pulse_read(simulator: Simulator, protocol: ProgramPulseReadProtocol, *, initial_state: DeviceState | None=None) -> ProgramPulseReadResult`

## ncmemsim.pulse_memory_fit

`ncmemsim/pulse_memory_fit.py`

Explicit exports: `DevicePulseMemoryTimeFitResult`, `PULSE_BRANCH_SEMANTICS`, `PULSE_MEMORY_WINDOW_DEFINITION`, `PULSE_READ_SEMANTICS`, `PulseMemoryTimeFitProtocol`, `PulseMemoryTimePrediction`, `fit_single_parameter_pulse_memory_window_vs_programming_time`, `predict_pulse_memory_window_vs_programming_time`

### PulseMemoryTimeFitProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `program_voltage_V: float`; required declaration.
- Field `erase_voltage_V: float`; required declaration.
- Field `erase_time_s: float`; required declaration.
- Field `read_voltage_V: float`; default expression `0.0`.
- Field `pulse_internal_dt_s: float | None`; default expression `None`.
- `paired_protocol(self, programming_time_s: float) -> PairedPulseMemoryProtocol`.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### PulseMemoryTimePrediction

Bases: none.

Decorators: `dataclass`.

- Field `programming_times_s: np.ndarray`; required declaration.
- Field `predicted_memory_window_V: np.ndarray`; required declaration.
- Field `pulse_results: tuple[PairedPulseMemoryResult, ...]`; required declaration.
- Field `reference_state_manifest: dict[str, Any]`; required declaration.
- `reference_state_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### DevicePulseMemoryTimeFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `protocol: PulseMemoryTimeFitProtocol`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `objective: ObjectiveEvaluation`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `prediction: PulseMemoryTimePrediction`; required declaration.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `predict_pulse_memory_window_vs_programming_time(simulator: Simulator, programming_times_s: Sequence[float] | np.ndarray, protocol: PulseMemoryTimeFitProtocol, *, reference_state: DeviceState | None=None) -> PulseMemoryTimePrediction`
- `fit_single_parameter_pulse_memory_window_vs_programming_time(dataset: DeviceObservableDataset, *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, calibration_spec: DeviceCalibrationSpec, protocol: PulseMemoryTimeFitProtocol, reference_state: DeviceState | None=None, least_squares_config: LeastSquaresConfig | None=None) -> DevicePulseMemoryTimeFitResult`

## ncmemsim.reference

`ncmemsim/reference.py`

No explicit export list; documented entry points need individual approval.

- `make_v53_reference_device(grid_points=31, nc_diameter_nm=3.0, active_fraction=0.22)`

## ncmemsim.reproducibility

`ncmemsim/reproducibility.py`

Explicit exports: `build_reproducibility_manifest`, `canonical_hash`, `git_commit`, `software_version`

- `software_version() -> str`
- `git_commit(cwd: str | Path | None=None) -> str | None`
- `build_reproducibility_manifest(device: Device, *, physics_model: str='PhaseD6', simulation_config: dict[str, Any] | None=None, random_seed: int | None=None, extra: dict[str, Any] | None=None) -> dict[str, Any]`

## ncmemsim.retention

`ncmemsim/retention.py`

No explicit export list; documented entry points need individual approval.

### RetentionConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `gate_voltage_V: float`; default expression `0.0`.
- Field `total_time_s: float`; default expression `10000.0`.
- Field `initial_dt_s: float`; default expression `1e-09`.
- Field `maximum_dt_s: float`; default expression `1000.0`.
- Field `growth_factor: float`; default expression `2.0`.
- Field `output_points: int`; default expression `121`.
- Field `quasi_equilibrium_tolerance_C_m2_s: float`; default expression `1e-18`.
- Field `quasi_equilibrium_steps: int`; default expression `4`.
- Field `stop_at_quasi_equilibrium: bool`; default expression `False`.
- Field `occupancy_integrator: str`; default expression `'backward_euler'`.
- `validate(self) -> None`.

### RetentionResult

Bases: none.

Decorators: `dataclass`.

- Field `time_s: np.ndarray`; required declaration.
- Field `qfg_C_m2: np.ndarray`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray`; required declaration.
- Field `mean_occupation_by_fg: np.ndarray`; required declaration.
- Field `delta_vfb_V: np.ndarray`; required declaration.
- Field `delta_vfb_by_fg_V: np.ndarray`; required declaration.
- Field `local_field_by_fg_V_m: np.ndarray`; required declaration.
- Field `local_potential_by_fg_V: np.ndarray`; required declaration.
- Field `inter_fg_flux_by_link_m2_s: np.ndarray`; required declaration.
- Field `transport_transmission_by_link: np.ndarray`; required declaration.
- Field `transport_link_ids: tuple[str, ...]`; required declaration.
- Field `charge_rate_C_m2_s: np.ndarray`; required declaration.
- Field `final_state: DeviceState`; required declaration.
- Field `quasi_equilibrium_reached: bool`; required declaration.
- Field `quasi_equilibrium_time_s: float | None`; required declaration.
- `total_charge_retention_fraction(self) -> np.ndarray`; `property`.
- `charge_loss_fraction(self) -> np.ndarray`; `property`.

### RetentionSolver

Bases: none.

Constructor: `__init__(self, simulator: 'Simulator', config: RetentionConfig | None=None)`.

- `run(self, initial_state: DeviceState | None=None) -> RetentionResult`.


## ncmemsim.retention_fit

`ncmemsim/retention_fit.py`

Explicit exports: `DeviceRetentionFractionFitResult`, `RETENTION_FRACTION_OBSERVABLE`, `RETENTION_INITIAL_STATE_SEMANTICS`, `RETENTION_INTERPOLATION_SEMANTICS`, `RETENTION_TRAJECTORY_SEMANTICS`, `RetentionFitProtocol`, `RetentionFractionPrediction`, `fit_single_parameter_retention_fraction`, `predict_retention_fraction`

### RetentionFitProtocol

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `retention_config: RetentionConfig`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `protocol_hash(self) -> str`.

### RetentionFractionPrediction

Bases: none.

Decorators: `dataclass`.

- Field `time_s: np.ndarray`; required declaration.
- Field `predicted_retention_fraction: np.ndarray`; required declaration.
- Field `retention_result: RetentionResult`; required declaration.
- Field `initial_state_manifest: dict[str, Any]`; required declaration.
- `initial_state_hash(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### DeviceRetentionFractionFitResult

Bases: none.

Decorators: `dataclass`.

- Field `dataset_id: str`; required declaration.
- Field `dataset_hash: str`; required declaration.
- Field `calibration_specification_hash: str`; required declaration.
- Field `protocol: RetentionFitProtocol`; required declaration.
- Field `numerical_result: DeterministicFitResult`; required declaration.
- Field `device_objective: DeviceObjectiveEvaluation`; required declaration.
- Field `fitted_context: DeviceCalibrationContext`; required declaration.
- Field `prediction: RetentionFractionPrediction`; required declaration.
- `objective(self) -> ObjectiveEvaluation`; `property`.
- `fitted_parameter_values(self) -> dict[str, float]`; `property`.
- `scientific_status(self) -> str`; `property`.
- `to_dict(self) -> dict[str, Any]`.

- `predict_retention_fraction(simulator: Simulator, protocol: RetentionFitProtocol, *, initial_state: DeviceState) -> RetentionFractionPrediction`
- `fit_single_parameter_retention_fraction(dataset: DeviceObservableDataset, *, base_device: Device, base_physics: PhysicsModel, base_simulation_config: SimulationConfig, calibration_spec: DeviceCalibrationSpec, protocol: RetentionFitProtocol, initial_state: DeviceState, least_squares_config: LeastSquaresConfig | None=None) -> DeviceRetentionFractionFitResult`

## ncmemsim.simulator

`ncmemsim/simulator.py`

No explicit export list; documented entry points need individual approval.

### SimulationConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `dwell_time_s: float`; default expression `0.005`.
- Field `internal_dt_s: float`; default expression `1e-05`.
- Field `qfix_C_m2: float`; default expression `0.0`.
- Field `qit_C_m2: float`; default expression `0.0`.

### SweepResult

Bases: none.

Decorators: `dataclass`.

- Field `voltages_V: np.ndarray`; required declaration.
- Field `capacitance_F_m2: np.ndarray`; required declaration.
- Field `qfg_C_m2: np.ndarray`; required declaration.
- Field `vfb_V: np.ndarray`; required declaration.
- Field `veff_V: np.ndarray`; required declaration.
- Field `mean_occupation: np.ndarray`; required declaration.
- Field `field_mean_V_m: np.ndarray`; required declaration.
- Field `tprog_mean: np.ndarray`; required declaration.
- Field `terase_mean: np.ndarray`; required declaration.
- Field `final_state: DeviceState`; required declaration.
- Field `qfg_by_fg_C_m2: np.ndarray | None`; default expression `None`.
- Field `mean_occupation_by_fg: np.ndarray | None`; default expression `None`.
- Field `field_mean_by_fg_V_m: np.ndarray | None`; default expression `None`.
- Field `tprog_mean_by_fg: np.ndarray | None`; default expression `None`.
- Field `terase_mean_by_fg: np.ndarray | None`; default expression `None`.
- Field `delta_vfb_V: np.ndarray | None`; default expression `None`.
- Field `delta_vfb_by_fg_V: np.ndarray | None`; default expression `None`.
- Field `coupling_sensitivity_factors: np.ndarray | None`; default expression `None`.
- Field `coupling_coefficients_m2_F: np.ndarray | None`; default expression `None`.
- Field `electrostatic_local_field_by_fg_V_m: np.ndarray | None`; default expression `None`.
- Field `electrostatic_local_potential_by_fg_V: np.ndarray | None`; default expression `None`.
- Field `field_profiles: list | None`; default expression `None`.
- Field `inter_fg_flux_by_link_m2_s: np.ndarray | None`; default expression `None`.
- Field `transport_transmission_by_link: np.ndarray | None`; default expression `None`.
- Field `transport_link_ids: tuple[str, ...] | None`; default expression `None`.
- Field `optical_absorption_fraction: np.ndarray | None`; default expression `None`.
- Field `absorbed_photon_flux_m2_s: np.ndarray | None`; default expression `None`.
- Field `photo_transition_rate_s: np.ndarray | None`; default expression `None`.
- Field `optical_absorption_fraction_by_fg: np.ndarray | None`; default expression `None`.
- Field `absorbed_photon_flux_by_fg_m2_s: np.ndarray | None`; default expression `None`.
- Field `absorbed_photon_rate_per_nc_by_fg_s: np.ndarray | None`; default expression `None`.
- Field `photo_transition_rate_by_fg_s: np.ndarray | None`; default expression `None`.
- Field `optical_alpha_nc_by_fg_m_inv: np.ndarray | None`; default expression `None`.
- Field `optical_alpha_eff_by_fg_m_inv: np.ndarray | None`; default expression `None`.

### CVResult

Bases: none.

Decorators: `dataclass`.

- Field `forward: SweepResult`; required declaration.
- Field `backward: SweepResult`; required declaration.
- Field `memory_window_V: float`; required declaration.
- Field `vmid_forward_V: float`; required declaration.
- Field `vmid_backward_V: float`; required declaration.

### Simulator

Bases: none.

Constructor: `__init__(self, device, physics: PhysicsModel | None=None, config: SimulationConfig | None=None)`.

- `relax_voltage(self, state: DeviceState, gate_voltage_V: float, dwell_time_s: float | None=None, internal_dt_s: float | None=None, light_source: LightSource | None=None, photo_config: PhotoTransitionConfig | None=None, photo_weights: PhotoTransitionWeights | None=None, occupancy_integrator: str='explicit_euler')`.
- `run_sweep(self, voltages_V, state: DeviceState | None=None, light_source: LightSource | None=None, photo_config: PhotoTransitionConfig | None=None, photo_weights: PhotoTransitionWeights | None=None)`.
- `simulate_retention(self, state: DeviceState | None=None, config=None)`.
- `voltage_at_capacitance(voltage, capacitance, reference)`; `staticmethod`.
- `simulate_cv(self, vmin_V=-3.0, vmax_V=3.0, points=241, light_source: LightSource | None=None, photo_config: PhotoTransitionConfig | None=None, photo_weights: PhotoTransitionWeights | None=None)`.


## ncmemsim.state

`ncmemsim/state.py`

No explicit export list; documented entry points need individual approval.

### FloatingGateState

Bases: none.

Decorators: `dataclass`.

- Field `P0: np.ndarray`; required declaration.
- Field `P1: np.ndarray`; required declaration.
- Field `P2: np.ndarray`; required declaration.
- Field `fg_id: int | None`; default expression `None`.
- Field `layer_name: str | None`; default expression `None`.
- Field `z_center_nm: float | None`; default expression `None`.
- Field `local_field_V_m: float | None`; default expression `None`.
- Field `local_potential_V: float | None`; default expression `None`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `empty(cls, grid_points: int, *, fg_id: int | None=None, layer_name: str | None=None, z_center_nm: float | None=None) -> 'FloatingGateState'`; `classmethod`.
- `copy(self) -> 'FloatingGateState'`.
- `validate(self, atol: float=1e-12) -> None`.
- `occupation(self) -> np.ndarray`; `property`.
- `mean_normalized_occupation(self) -> float`; `property`.

### DeviceState

Bases: none.

Decorators: `dataclass`.

- Field `floating_gates: list[FloatingGateState]`; required declaration.
- Field `time_s: float`; default expression `0.0`.
- Field `metadata: dict[str, Any]`; default expression `field(default_factory=dict)`.
- `empty_for_device(cls, device) -> 'DeviceState'`; `classmethod`.
- `copy(self) -> 'DeviceState'`.
- `validate(self, device=None) -> None`.
- `for_layer(self, layer_name: str) -> FloatingGateState`.
- `mean_normalized_occupations(self) -> np.ndarray`; `property`.


## ncmemsim.transport

`ncmemsim/transport/__init__.py`

Explicit exports: `base`, `NodeKind`, `TransportNode`, `link`, `TunnelLink`, `network`, `TunnelNetwork`, `rates`, `LinkTransportResult`, `TransportStepResult`, `engine`, `TransportConfig`, `TransportEngine`, `TrapAssistedModel`, `TrapAssistedTransportSpec`, `TrapCarrier`, `TrapEnergyReference`, `TrapParameterStatus`, `TrapSpecies`, `TATBarrierProfile`, `TATRateBatch`, `TATRateComponent`, `TATRateEvaluation`, `TATRateStatus`, `build_tat_barrier_profile`, `evaluate_tat_species`, `evaluate_trap_assisted_transport`, `evaluate_trap_assisted_transport_array`, `linear_wkb_transmission`, `BarrierCorrectionStatus`, `BarrierHeightCorrection`, `CorrectedTATBarrierProfile`, `CorrectedTATRateComponent`, `CorrectedTATRateEvaluation`, `ImageForceBarrierSpec`, `apply_image_force_barrier_correction`, `build_corrected_tat_barrier_profile`, `evaluate_tat_species_with_barrier_correction`, `evaluate_trap_assisted_transport_with_barrier_correction`, `image_force_barrier_lowering_J`, `AdvancedTransportEngine`, `AdvancedTransportSpec`, `IntegratedLinkTransportResult`, `IntegratedTransportStepResult`, `MechanismContribution`, `MechanismEvaluationStatus`, `MechanismFailure`, `TATLinkAttachment`, `TransportMechanism`


## ncmemsim.transport.barrier_corrections

`ncmemsim/transport/barrier_corrections.py`

Explicit exports: `BarrierCorrectionStatus`, `ImageForceBarrierSpec`, `BarrierHeightCorrection`, `CorrectedTATBarrierProfile`, `CorrectedTATRateComponent`, `CorrectedTATRateEvaluation`, `image_force_barrier_lowering_J`, `apply_image_force_barrier_correction`, `build_corrected_tat_barrier_profile`, `evaluate_tat_species_with_barrier_correction`, `evaluate_trap_assisted_transport_with_barrier_correction`

### BarrierCorrectionStatus

Bases: `str`, `Enum`.

- Assignment `DISABLED = 'disabled'`.
- Assignment `ZERO_FIELD = 'zero_field'`.
- Assignment `APPLIED = 'applied'`.
- Assignment `BARRIER_SUPPRESSED = 'barrier_suppressed'`.

### ImageForceBarrierSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `enabled: bool`; default expression `False`.
- Field `relative_permittivity: float`; default expression `1.0`.
- Field `parameter_status: TrapParameterStatus`; default expression `TrapParameterStatus.ASSUMED`.
- Field `source: str`; default expression `''`.
- Field `applicability: str`; default expression `''`.
- `to_dict(self) -> dict[str, Any]`.
- `configuration_hash(self) -> str`; `property`.

### BarrierHeightCorrection

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `unmodified_barrier_J: float`; required declaration.
- Field `lowering_J: float`; required declaration.
- Field `corrected_barrier_J: float`; required declaration.
- Field `status: BarrierCorrectionStatus`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

### CorrectedTATBarrierProfile

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `unmodified_profile: TATBarrierProfile`; required declaration.
- Field `correction_configuration_hash: str`; required declaration.
- Field `source_interface: BarrierHeightCorrection`; required declaration.
- Field `destination_interface: BarrierHeightCorrection`; required declaration.
- `corrected_profile(self) -> TATBarrierProfile`; `property`.
- `to_dict(self) -> dict[str, Any]`.

### CorrectedTATRateComponent

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `species_name: str`; required declaration.
- Field `species_hash: str`; required declaration.
- Field `barrier_diagnostics: CorrectedTATBarrierProfile`; required declaration.
- Field `entry_wkb_exponent: float`; required declaration.
- Field `exit_wkb_exponent: float`; required declaration.
- Field `entry_transmission: float`; required declaration.
- Field `exit_transmission: float`; required declaration.
- Field `entry_rate_Hz: float`; required declaration.
- Field `exit_rate_Hz: float`; required declaration.
- Field `active_probability: float`; required declaration.
- Field `rate_Hz: float`; required declaration.
- Field `status: TATRateStatus`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

### CorrectedTATRateEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `enabled: bool`; required declaration.
- Field `tat_configuration_hash: str`; required declaration.
- Field `correction_configuration_hash: str`; required declaration.
- Field `components: tuple[CorrectedTATRateComponent, ...]`; required declaration.
- Field `total_rate_Hz: float`; required declaration.
- Field `status: TATRateStatus`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

- `image_force_barrier_lowering_J(electric_field_V_m: float, relative_permittivity: float) -> float`
- `apply_image_force_barrier_correction(unmodified_barrier_J: float, *, electric_field_V_m: float, specification: ImageForceBarrierSpec) -> BarrierHeightCorrection`
- `build_corrected_tat_barrier_profile(species: TrapSpecies, correction: ImageForceBarrierSpec, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> CorrectedTATBarrierProfile`
- `evaluate_tat_species_with_barrier_correction(species: TrapSpecies, correction: ImageForceBarrierSpec, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> CorrectedTATRateComponent`
- `evaluate_trap_assisted_transport_with_barrier_correction(specification: TrapAssistedTransportSpec, correction: ImageForceBarrierSpec, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> CorrectedTATRateEvaluation`

## ncmemsim.transport.base

`ncmemsim/transport/base.py`

No explicit export list; documented entry points need individual approval.

### NodeKind

Bases: `str`, `Enum`.

- Assignment `SUBSTRATE = 'substrate'`.
- Assignment `FLOATING_GATE = 'floating_gate'`.
- Assignment `GATE = 'gate'`.

### TransportNode

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `node_id: str`; required declaration.
- Field `kind: NodeKind`; required declaration.
- Field `z_nm: float`; required declaration.
- Field `fg_index: int | None`; default expression `None`.


## ncmemsim.transport.engine

`ncmemsim/transport/engine.py`

No explicit export list; documented entry points need individual approval.

### TransportConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `enabled: bool`; default expression `True`.
- Field `attempt_frequency_Hz: float`; default expression `1000000000.0`.
- Field `default_barrier_eV: float`; default expression `1.78`.
- Field `effective_mass_m0: float`; default expression `0.15`.
- Field `direction_beta_V_inv: float`; default expression `8.0`.
- Field `max_transfer_fraction_per_step: float`; default expression `0.1`.
- Field `include_substrate_diagnostics: bool`; default expression `True`.

### TransportEngine

Bases: none.

Constructor: `__init__(self, tunneling_engine, config: TransportConfig | None=None)`.

- `build_network(self, device) -> TunnelNetwork`.
- `evaluate(self, device, state, field_profile, occupancy_engine) -> TransportStepResult`.
- `step(self, device, state, field_profile, occupancy_engine, dt_s: float)`.


## ncmemsim.transport.integration

`ncmemsim/transport/integration.py`

Explicit exports: `TransportMechanism`, `MechanismEvaluationStatus`, `MechanismFailure`, `TATLinkAttachment`, `AdvancedTransportSpec`, `MechanismContribution`, `IntegratedLinkTransportResult`, `IntegratedTransportStepResult`, `AdvancedTransportEngine`

### TransportMechanism

Bases: `str`, `Enum`.

- Assignment `DIRECT_TUNNELLING = 'direct_tunnelling'`.
- Assignment `TRAP_ASSISTED = 'trap_assisted'`.

### MechanismEvaluationStatus

Bases: `str`, `Enum`.

- Assignment `EVALUATED = 'evaluated'`.
- Assignment `NOT_ATTACHED = 'not_attached'`.
- Assignment `DISABLED = 'disabled'`.
- Assignment `DIAGNOSTIC_ONLY = 'diagnostic_only'`.
- Assignment `FAILED = 'failed'`.

### MechanismFailure

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `exception_type: str`; required declaration.
- Field `message: str`; required declaration.
- `to_dict(self) -> dict[str, str]`.

### TATLinkAttachment

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `link_id: str`; required declaration.
- Field `specification: TrapAssistedTransportSpec`; required declaration.
- Field `barrier_correction: ImageForceBarrierSpec`; default expression `ImageForceBarrierSpec()`.
- `to_dict(self) -> dict[str, Any]`.

### AdvancedTransportSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `attachments: tuple[TATLinkAttachment, ...]`; default expression `()`.
- `to_dict(self) -> dict[str, Any]`.
- `configuration_hash(self) -> str`; `property`.

### MechanismContribution

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `mechanism: TransportMechanism`; required declaration.
- Field `status: MechanismEvaluationStatus`; required declaration.
- Field `forward_rate_Hz: float`; required declaration.
- Field `backward_rate_Hz: float`; required declaration.
- Field `net_electron_flux_m2_s: float`; required declaration.
- Field `evaluation: CorrectedTATRateEvaluation | None`; default expression `None`.
- Field `failure: MechanismFailure | None`; default expression `None`.
- `to_dict(self) -> dict[str, Any]`.

### IntegratedLinkTransportResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `baseline: LinkTransportResult`; required declaration.
- Field `contributions: tuple[MechanismContribution, ...]`; required declaration.
- Field `total_forward_rate_Hz: float`; required declaration.
- Field `total_backward_rate_Hz: float`; required declaration.
- Field `total_net_electron_flux_m2_s: float`; required declaration.
- `link_id(self) -> str`; `property`.
- `kind(self) -> str`; `property`.
- `field_V_m(self) -> float`; `property`.
- `potential_difference_V(self) -> float`; `property`.
- `transmission(self) -> float`; `property`.
- `forward_rate_Hz(self) -> float`; `property`.
- `backward_rate_Hz(self) -> float`; `property`.
- `net_electron_flux_m2_s(self) -> float`; `property`.
- `left_fg_index(self) -> int | None`; `property`.
- `right_fg_index(self) -> int | None`; `property`.
- `contribution(self, mechanism: TransportMechanism) -> MechanismContribution`.

### IntegratedTransportStepResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `baseline: TransportStepResult`; required declaration.
- Field `links: tuple[IntegratedLinkTransportResult, ...]`; required declaration.
- Field `net_electron_flux_by_fg_m2_s: np.ndarray`; required declaration.
- `inter_fg_fluxes_m2_s(self) -> np.ndarray`; `property`.

### AdvancedTransportEngine

Bases: none.

Constructor: `__init__(self, baseline: TransportEngine, specification: AdvancedTransportSpec | None=None)`.

- `tunneling(self)`; `property`.
- `config(self)`; `property`.
- `build_network(self, device)`.
- `evaluate(self, device, state, field_profile, occupancy_engine) -> IntegratedTransportStepResult`.
- `step(self, device, state, field_profile, occupancy_engine, dt_s: float)`.


## ncmemsim.transport.link

`ncmemsim/transport/link.py`

No explicit export list; documented entry points need individual approval.

### TunnelLink

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `link_id: str`; required declaration.
- Field `left_node_id: str`; required declaration.
- Field `right_node_id: str`; required declaration.
- Field `length_m: float`; required declaration.
- Field `barrier_eV: float`; required declaration.
- Field `effective_mass_m0: float`; required declaration.
- Field `dielectric_layers: tuple[str, ...]`; required declaration.
- Field `kind: str`; required declaration.
- Field `left_fg_index: int | None`; default expression `None`.
- Field `right_fg_index: int | None`; default expression `None`.
- `validate(self) -> None`.


## ncmemsim.transport.network

`ncmemsim/transport/network.py`

No explicit export list; documented entry points need individual approval.

### TunnelNetwork

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `nodes: tuple[TransportNode, ...]`; required declaration.
- Field `links: tuple[TunnelLink, ...]`; required declaration.
- `validate(self) -> None`.
- `from_device(cls, device, *, barrier_eV: float=1.78, effective_mass_m0: float=0.15, include_substrate_link: bool=True) -> 'TunnelNetwork'`; `classmethod`.


## ncmemsim.transport.rates

`ncmemsim/transport/rates.py`

No explicit export list; documented entry points need individual approval.

### LinkTransportResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `link_id: str`; required declaration.
- Field `kind: str`; required declaration.
- Field `field_V_m: float`; required declaration.
- Field `potential_difference_V: float`; required declaration.
- Field `transmission: float`; required declaration.
- Field `forward_rate_Hz: float`; required declaration.
- Field `backward_rate_Hz: float`; required declaration.
- Field `net_electron_flux_m2_s: float`; required declaration.
- Field `left_fg_index: int | None`; required declaration.
- Field `right_fg_index: int | None`; required declaration.

### TransportStepResult

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `links: tuple[LinkTransportResult, ...]`; required declaration.
- Field `net_electron_flux_by_fg_m2_s: np.ndarray`; required declaration.
- `inter_fg_fluxes_m2_s(self) -> np.ndarray`; `property`.


## ncmemsim.transport.tat

`ncmemsim/transport/tat.py`

Explicit exports: `TATRateStatus`, `TATBarrierProfile`, `TATRateComponent`, `TATRateEvaluation`, `TATRateBatch`, `linear_wkb_transmission`, `build_tat_barrier_profile`, `evaluate_tat_species`, `evaluate_trap_assisted_transport`, `evaluate_trap_assisted_transport_array`

### TATRateStatus

Bases: `str`, `Enum`.

- Assignment `DISABLED = 'disabled'`.
- Assignment `ZERO_DENSITY = 'zero_density'`.
- Assignment `EVALUATED = 'evaluated'`.
- Assignment `TRANSMISSION_UNDERFLOW = 'transmission_underflow'`.

- `linear_wkb_transmission(length_m: float, start_barrier_J: float, end_barrier_J: float, effective_mass_m0: float) -> tuple[float, float]`
### TATBarrierProfile

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `link_length_m: float`; required declaration.
- Field `trap_position_m: float`; required declaration.
- Field `electric_field_V_m: float`; required declaration.
- Field `effective_mass_m0: float`; required declaration.
- Field `entry_start_barrier_J: float`; required declaration.
- Field `trap_barrier_J: float`; required declaration.
- Field `exit_end_barrier_J: float`; required declaration.
- `to_dict(self) -> dict[str, Any]`.

### TATRateComponent

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `species_name: str`; required declaration.
- Field `species_hash: str`; required declaration.
- Field `barrier_profile: TATBarrierProfile`; required declaration.
- Field `entry_wkb_exponent: float`; required declaration.
- Field `exit_wkb_exponent: float`; required declaration.
- Field `entry_transmission: float`; required declaration.
- Field `exit_transmission: float`; required declaration.
- Field `entry_rate_Hz: float`; required declaration.
- Field `exit_rate_Hz: float`; required declaration.
- Field `active_probability: float`; required declaration.
- Field `rate_Hz: float`; required declaration.
- Field `status: TATRateStatus`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

### TATRateEvaluation

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `enabled: bool`; required declaration.
- Field `configuration_hash: str`; required declaration.
- Field `components: tuple[TATRateComponent, ...]`; required declaration.
- Field `total_rate_Hz: float`; required declaration.
- Field `status: TATRateStatus`; required declaration.
- `to_dict(self) -> dict[str, Any]`.
- `result_hash(self) -> str`; `property`.

### TATRateBatch

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `shape: tuple[int, ...]`; required declaration.
- Field `evaluations: tuple[TATRateEvaluation, ...]`; required declaration.
- `total_rates_Hz(self) -> np.ndarray`; `property`.

- `build_tat_barrier_profile(species: TrapSpecies, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> TATBarrierProfile`
- `evaluate_tat_species(species: TrapSpecies, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> TATRateComponent`
- `evaluate_trap_assisted_transport(specification: TrapAssistedTransportSpec, *, link_length_m: float, electric_field_V_m: float, effective_mass_m0: float) -> TATRateEvaluation`
- `evaluate_trap_assisted_transport_array(specification: TrapAssistedTransportSpec, *, link_length_m, electric_field_V_m, effective_mass_m0) -> TATRateBatch`

## ncmemsim.transport.traps

`ncmemsim/transport/traps.py`

Explicit exports: `TrapCarrier`, `TrapEnergyReference`, `TrapParameterStatus`, `TrapAssistedModel`, `TrapSpecies`, `TrapAssistedTransportSpec`

### TrapCarrier

Bases: `str`, `Enum`.

- Assignment `ELECTRON = 'electron'`.

### TrapEnergyReference

Bases: `str`, `Enum`.

- Assignment `CONDUCTION_BAND_DEPTH = 'conduction_band_depth'`.

### TrapParameterStatus

Bases: `str`, `Enum`.

- Assignment `ASSUMED = 'assumed'`.
- Assignment `LITERATURE = 'literature'`.
- Assignment `FITTED = 'fitted'`.
- Assignment `CALIBRATED = 'calibrated'`.

### TrapAssistedModel

Bases: `str`, `Enum`.

- Assignment `SEQUENTIAL_TWO_STEP_WKB = 'sequential_two_step_wkb'`.

### TrapSpecies

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `name: str`; required declaration.
- Field `energy_depth_J: float`; required declaration.
- Field `position_fraction: float`; required declaration.
- Field `density_m3: float`; required declaration.
- Field `capture_cross_section_m2: float`; required declaration.
- Field `attempt_frequency_Hz: float`; required declaration.
- Field `parameter_status: TrapParameterStatus`; required declaration.
- Field `source: str`; required declaration.
- Field `applicability: str`; required declaration.
- Field `carrier: TrapCarrier`; default expression `TrapCarrier.ELECTRON`.
- Field `energy_reference: TrapEnergyReference`; default expression `TrapEnergyReference.CONDUCTION_BAND_DEPTH`.
- `to_dict(self) -> dict[str, Any]`.
- `from_dict(cls, value: dict[str, Any]) -> 'TrapSpecies'`; `classmethod`.
- `species_hash(self) -> str`; `property`.

### TrapAssistedTransportSpec

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `enabled: bool`; default expression `False`.
- Field `species: tuple[TrapSpecies, ...]`; default expression `()`.
- Field `model: TrapAssistedModel`; default expression `TrapAssistedModel.SEQUENTIAL_TWO_STEP_WKB`.
- `to_dict(self) -> dict[str, Any]`.
- `from_dict(cls, value: dict[str, Any]) -> 'TrapAssistedTransportSpec'`; `classmethod`.
- `configuration_hash(self) -> str`; `property`.
- `to_json(self) -> str`.
- `from_json(cls, value: str) -> 'TrapAssistedTransportSpec'`; `classmethod`.


## ncmemsim.tunneling

`ncmemsim/tunneling.py`

No explicit export list; documented entry points need individual approval.

### TunnelingConfig

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `injection_energy_eV: float`; default expression `0.1`.
- Field `oxide_effective_mass_m0: float`; default expression `0.15`.
- Field `integration_points: int`; default expression `160`.
- Field `field_coupling_factor: float`; default expression `0.8`.
- Field `activation_beta_V_inv: float`; default expression `0.8`.

### TunnelingEngine

Bases: none.

Constructor: `__init__(self, config: TunnelingConfig | None=None)`.

- `field_from_effective_voltage(self, veff_V: float, path_length_m: float) -> float`.
- `trapezoidal_wkb(self, length_m: float, field_V_m: float, barrier_eV: float, injection_energy_eV: float | None=None, effective_mass_m0: float | None=None) -> float`.
- `positive_activation(self, veff_V: float) -> float`.
- `negative_activation(self, veff_V: float) -> float`.


## ncmemsim.validation

`ncmemsim/validation.py`

No explicit export list; documented entry points need individual approval.

### ValidationIssue

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `code: str`; required declaration.
- Field `message: str`; required declaration.
- Field `severity: str`; default expression `'error'`.

### ValidationReport

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `issues: tuple[ValidationIssue, ...]`; required declaration.
- `passed(self) -> bool`; `property`.
- `raise_for_errors(self) -> None`.

- `validate_probabilities(state: DeviceState, atol: float=1e-10) -> list[ValidationIssue]`
- `validate_device_physics(device: Device) -> list[ValidationIssue]`
- `validate_field_profile(profile, applied_voltage_V: float, atol_V: float=1e-09) -> list[ValidationIssue]`
- `validate_internal_charge_conservation(before_C_m2: Iterable[float], after_C_m2: Iterable[float], atol: float=1e-15) -> list[ValidationIssue]`
- `validate_simulation(device: Device, state: DeviceState, output: dict | None=None) -> ValidationReport`

## ncmemsim.workflows

`ncmemsim/workflows/__init__.py`

Explicit exports: `DataOrigin`, `DatasetEvidence`, `WorkflowEvidence`, `capture_dataset_evidence`, `build_workflow_evidence`, `AppliedWorkflowEvidence`, `WorkflowEvaluator`, `apply_workflow_parameters`, `WorkflowReport`, `build_workflow_report`, `write_workflow_report`


## ncmemsim.workflows.application

`ncmemsim/workflows/application.py`

No explicit export list; documented entry points need individual approval.

### AppliedWorkflowEvidence

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `evidence_hash(self)`; `property`.
- `context_hash(self)`; `property`.
- `scientific_status(self)`; `property`.
- `to_dict(self)`.
- `to_json(self)`.
- `from_json(cls, value)`; `classmethod`.

### WorkflowEvaluator

Bases: none.

Constructor: `__init__(self, evidence, device, protocol)`.

- `evidence(self)`; `property`.
- `base_device(self)`; `property`.
- `base_protocol(self)`; `property`.
- `evaluation_id(self)`; `property`.
- `evaluation_parameters(self)`; `property`.
- `fresh_simulator(self, device=None)`.
- `evaluate(self, device, protocol, point=None)`.

- `apply_workflow_parameters(workflow_evidence, *, calibration_spec, base_device, base_physics, base_simulation_config, base_protocol, evaluation_id, base_photo_config=None)`

## ncmemsim.workflows.evidence

`ncmemsim/workflows/evidence.py`

No explicit export list; documented entry points need individual approval.

### DataOrigin

Bases: `str`, `Enum`.

- Assignment `SYNTHETIC = 'synthetic'`.
- Assignment `MEASURED = 'measured'`.

### DatasetEvidence

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `dataset_hash(self)`; `property`.
- `evidence_hash(self)`; `property`.
- `origin(self)`; `property`.
- `to_dict(self)`.
- `to_json(self)`.
- `from_json(cls, value)`; `classmethod`.

- `capture_dataset_evidence(dataset, *, origin: DataOrigin, source: str, applicability: str) -> DatasetEvidence`
### WorkflowEvidence

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `evidence_hash(self)`; `property`.
- `scientific_status(self)`; `property`.
- `qualification_eligible(self)`; `property`.
- `to_dict(self)`.
- `to_json(self)`.
- `from_json(cls, value)`; `classmethod`.

- `build_workflow_evidence(*, name: str, fit_dataset: DatasetEvidence, fit_result, calibration_spec: DeviceCalibrationSpec, diagnostics: FitUncertaintyDiagnostics | None=None, validation_dataset: DatasetEvidence | None=None, qualification: CalibrationQualification | None=None, metadata: dict | None=None) -> WorkflowEvidence`

## ncmemsim.workflows.reporting

`ncmemsim/workflows/reporting.py`

Explicit exports: `WorkflowReport`, `build_workflow_report`, `write_workflow_report`

### WorkflowReport

Bases: none.

Decorators: `dataclass(frozen=True)`.

- Field `payload_json: str`; required declaration.
- `report_hash(self)`; `property`.
- `to_dict(self)`.
- `to_json(self)`.
- `from_json(cls, value)`; `classmethod`.
- `samples_csv(self)`.
- `statistics_csv(self)`.
- `nominal_csv(self)`.
- `robust_csv(self)`.
- `to_markdown(self)`.

- `build_workflow_report(workflow_evidence, applied_workflow_evidence, robust_report, *, name, device_variants, metadata=None)`
- `write_workflow_report(report, output_dir)`

## Simulator diagnostic dictionary keys

Reviewed shapes and units are in [result contracts](api_results.md).

- `state`
- `rho_C_m3`
- `rho_by_fg_C_m3`
- `qfg_C_m2`
- `qfg_by_fg_C_m2`
- `vfb_V`
- `veff_V`
- `capacitance_F_m2`
- `mean_occupation`
- `mean_occupation_by_fg`
- `field_mean_V_m`
- `field_mean_by_fg_V_m`
- `tprog_mean`
- `tprog_mean_by_fg`
- `terase_mean`
- `terase_mean_by_fg`
- `delta_vfb_V`
- `delta_vfb_by_fg_V`
- `coupling_sensitivity_factors`
- `coupling_coefficients_m2_F`
- `coupling_matrix_m2_F`
- `electrostatic_local_field_by_fg_V_m`
- `electrostatic_local_potential_by_fg_V`
- `field_profile`
- `potential_profile`
- `transport_network`
- `transport_link_results`
- `transport_link_ids`
- `inter_fg_flux_by_link_m2_s`
- `transport_transmission_by_link`
- `transport_net_flux_by_fg_m2_s`
- `optical_absorption_fraction_by_fg`
- `absorbed_photon_flux_by_fg_m2_s`
- `absorbed_photon_rate_per_nc_by_fg_s`
- `photo_transition_rate_by_fg_s`
- `optical_alpha_nc_by_fg_m_inv`
- `optical_alpha_eff_by_fg_m_inv`
- `optical_absorption_fraction`
- `absorbed_photon_flux_m2_s`
- `photo_transition_rate_s`
