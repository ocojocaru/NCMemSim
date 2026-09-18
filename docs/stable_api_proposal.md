# Proposed stable v1.0 API surface

Status: proposal_pending_approval. Preparation version remains 0.14.0.
This list is a proposed contract, not a declaration that v1.0 is released.

All existing documented imports plus explicit root-package exports and legacy transport exports; other aliases/helpers are not implicitly selected.

Exact signatures, declared fields and public methods are in [stable_api_proposal.json](stable_api_proposal.json).
Class call signatures include generated dataclass constructors; source records identify declared methods and fields.
Inherited/incidental methods are not automatically guaranteed. Module selection guarantees its named import path, not every attribute.
Version strings are runtime identity, not a promise to retain the literal version number.

| Import path | Definition / alias target | Kind |
|---|---|---|
| ncmemsim | ncmemsim | module |
| ncmemsim.BenchmarkRecord | ncmemsim.benchmark.BenchmarkRecord | class |
| ncmemsim.CVResult | ncmemsim.simulator.CVResult | class |
| ncmemsim.CompactCouplingModel | ncmemsim.coupling.CompactCouplingModel | class |
| ncmemsim.CouplingModel | ncmemsim.coupling.CouplingModel | class |
| ncmemsim.CouplingResult | ncmemsim.coupling.CouplingResult | class |
| ncmemsim.Device | ncmemsim.device.Device | class |
| ncmemsim.DeviceBuilder | ncmemsim.builder.DeviceBuilder | class |
| ncmemsim.DeviceState | ncmemsim.state.DeviceState | class |
| ncmemsim.ElectrostaticsEngine | ncmemsim.electrostatics.ElectrostaticsEngine | class |
| ncmemsim.ElectrostaticsResult | ncmemsim.electrostatics.ElectrostaticsResult | class |
| ncmemsim.FieldProfile | ncmemsim.fieldsolver.FieldProfile | class |
| ncmemsim.FieldSolver1D | ncmemsim.fieldsolver.FieldSolver1D | class |
| ncmemsim.FloatingGateLayer | ncmemsim.layers.FloatingGateLayer | class |
| ncmemsim.FloatingGateState | ncmemsim.state.FloatingGateState | class |
| ncmemsim.HFO2 | ncmemsim.materials.presets.HFO2 | declared_value |
| ncmemsim.KineticsConfig | ncmemsim.kinetics.KineticsConfig | class |
| ncmemsim.Layer | ncmemsim.layers.Layer | class |
| ncmemsim.LightSource | ncmemsim.optics.LightSource | class |
| ncmemsim.LinkTransportResult | ncmemsim.transport.rates.LinkTransportResult | class |
| ncmemsim.Material | ncmemsim.materials.base.Material | class |
| ncmemsim.NanocrystalMaterial | ncmemsim.materials.base.NanocrystalMaterial | class |
| ncmemsim.NodeKind | ncmemsim.transport.base.NodeKind | class |
| ncmemsim.OccupancyEngine | ncmemsim.kinetics.OccupancyEngine | class |
| ncmemsim.PhysicsModel | ncmemsim.physics.PhysicsModel | class |
| ncmemsim.RateArrays | ncmemsim.kinetics.RateArrays | class |
| ncmemsim.RetentionConfig | ncmemsim.retention.RetentionConfig | class |
| ncmemsim.RetentionResult | ncmemsim.retention.RetentionResult | class |
| ncmemsim.RetentionSolver | ncmemsim.retention.RetentionSolver | class |
| ncmemsim.SILICON | ncmemsim.materials.presets.SILICON | declared_value |
| ncmemsim.SIO2 | ncmemsim.materials.presets.SIO2 | declared_value |
| ncmemsim.SemiconductorConfig | ncmemsim.electrostatics.SemiconductorConfig | class |
| ncmemsim.SimulationConfig | ncmemsim.simulator.SimulationConfig | class |
| ncmemsim.Simulator | ncmemsim.simulator.Simulator | class |
| ncmemsim.SweepResult | ncmemsim.simulator.SweepResult | class |
| ncmemsim.TransportConfig | ncmemsim.transport.engine.TransportConfig | class |
| ncmemsim.TransportEngine | ncmemsim.transport.engine.TransportEngine | class |
| ncmemsim.TransportNode | ncmemsim.transport.base.TransportNode | class |
| ncmemsim.TransportStepResult | ncmemsim.transport.rates.TransportStepResult | class |
| ncmemsim.TunnelLink | ncmemsim.transport.link.TunnelLink | class |
| ncmemsim.TunnelNetwork | ncmemsim.transport.network.TunnelNetwork | class |
| ncmemsim.TunnelingConfig | ncmemsim.tunneling.TunnelingConfig | class |
| ncmemsim.TunnelingEngine | ncmemsim.tunneling.TunnelingEngine | class |
| ncmemsim.ValidationIssue | ncmemsim.validation.ValidationIssue | class |
| ncmemsim.ValidationReport | ncmemsim.validation.ValidationReport | class |
| ncmemsim.__version__ | ncmemsim._version.__version__ | declared_value |
| ncmemsim.benchmark_case | ncmemsim.benchmark.benchmark_case | function |
| ncmemsim.build_golden_suite | ncmemsim.golden.build_golden_suite | function |
| ncmemsim.build_reproducibility_manifest | ncmemsim.reproducibility.build_reproducibility_manifest | function |
| ncmemsim.calibration.CalibrationCriteria | ncmemsim.calibration.CalibrationCriteria | class |
| ncmemsim.calibration.CalibrationCriterionResult | ncmemsim.calibration.CalibrationCriterionResult | class |
| ncmemsim.calibration.CalibrationQualification | ncmemsim.calibration.CalibrationQualification | class |
| ncmemsim.calibration.qualify_calibration | ncmemsim.calibration.qualify_calibration | function |
| ncmemsim.compare_golden | ncmemsim.golden.compare_golden | function |
| ncmemsim.device_calibration.DeviceCalibrationContext | ncmemsim.device_calibration.DeviceCalibrationContext | class |
| ncmemsim.device_calibration.DeviceCalibrationSpec | ncmemsim.device_calibration.DeviceCalibrationSpec | class |
| ncmemsim.device_calibration.DeviceFitParameterBinding | ncmemsim.device_calibration.DeviceFitParameterBinding | class |
| ncmemsim.device_calibration.DeviceFitTarget | ncmemsim.device_calibration.DeviceFitTarget | class |
| ncmemsim.device_calibration.apply_device_calibration_parameters | ncmemsim.device_calibration.apply_device_calibration_parameters | function |
| ncmemsim.device_fit.CVCalibrationProtocol | ncmemsim.device_fit.CVCalibrationProtocol | class |
| ncmemsim.device_fit.DeviceCVFitResult | ncmemsim.device_fit.DeviceCVFitResult | class |
| ncmemsim.device_fit.fit_single_parameter_cv_dataset | ncmemsim.device_fit.fit_single_parameter_cv_dataset | function |
| ncmemsim.dtco.BindingScope | ncmemsim.dtco.spec.BindingScope | class |
| ncmemsim.dtco.ConstraintOperator | ncmemsim.dtco.metrics.ConstraintOperator | class |
| ncmemsim.dtco.DTCOReport | ncmemsim.dtco.reporting.DTCOReport | class |
| ncmemsim.dtco.DesignVariable | ncmemsim.dtco.spec.DesignVariable | class |
| ncmemsim.dtco.DesignVariableRole | ncmemsim.dtco.spec.DesignVariableRole | class |
| ncmemsim.dtco.ExperimentSpec | ncmemsim.dtco.spec.ExperimentSpec | class |
| ncmemsim.dtco.MetricAnalysisSpec | ncmemsim.dtco.metrics.MetricAnalysisSpec | class |
| ncmemsim.dtco.MetricConstraint | ncmemsim.dtco.metrics.MetricConstraint | class |
| ncmemsim.dtco.MetricDefinition | ncmemsim.dtco.metrics.MetricDefinition | class |
| ncmemsim.dtco.ObjectiveDirection | ncmemsim.dtco.metrics.ObjectiveDirection | class |
| ncmemsim.dtco.ParameterBinding | ncmemsim.dtco.spec.ParameterBinding | class |
| ncmemsim.dtco.ParetoAnalysisSpec | ncmemsim.dtco.pareto.ParetoAnalysisSpec | class |
| ncmemsim.dtco.RobustDTCOReport | ncmemsim.dtco.robust_reporting.RobustDTCOReport | class |
| ncmemsim.dtco.RobustFailurePolicy | ncmemsim.dtco.robust.RobustFailurePolicy | class |
| ncmemsim.dtco.RobustObjective | ncmemsim.dtco.robust.RobustObjective | class |
| ncmemsim.dtco.RobustParetoSpec | ncmemsim.dtco.robust.RobustParetoSpec | class |
| ncmemsim.dtco.RobustStatistic | ncmemsim.dtco.robust.RobustStatistic | class |
| ncmemsim.dtco.SampleAnalysisSpec | ncmemsim.dtco.sample_analysis.SampleAnalysisSpec | class |
| ncmemsim.dtco.SampleManifest | ncmemsim.dtco.sampling.SampleManifest | class |
| ncmemsim.dtco.SamplingSpec | ncmemsim.dtco.sampling.SamplingSpec | class |
| ncmemsim.dtco.SensitivityAnalysisSpec | ncmemsim.dtco.sensitivity.SensitivityAnalysisSpec | class |
| ncmemsim.dtco.SensitivityEligibility | ncmemsim.dtco.sensitivity.SensitivityEligibility | class |
| ncmemsim.dtco.TruncatedNormalVariation | ncmemsim.dtco.variation.TruncatedNormalVariation | class |
| ncmemsim.dtco.UniformVariation | ncmemsim.dtco.variation.UniformVariation | class |
| ncmemsim.dtco.VariationDefinition | ncmemsim.dtco.variation.VariationDefinition | class |
| ncmemsim.dtco.VariationKind | ncmemsim.dtco.variation.VariationKind | class |
| ncmemsim.dtco.VariationProvenance | ncmemsim.dtco.variation.VariationProvenance | class |
| ncmemsim.dtco.analyze_pareto | ncmemsim.dtco.pareto.analyze_pareto | function |
| ncmemsim.dtco.analyze_robust_pareto | ncmemsim.dtco.robust.analyze_robust_pareto | function |
| ncmemsim.dtco.analyze_samples | ncmemsim.dtco.sample_analysis.analyze_samples | function |
| ncmemsim.dtco.analyze_sensitivity | ncmemsim.dtco.sensitivity.analyze_sensitivity | function |
| ncmemsim.dtco.analyze_sweep | ncmemsim.dtco.metrics.analyze_sweep | function |
| ncmemsim.dtco.build_dtco_report | ncmemsim.dtco.reporting.build_dtco_report | function |
| ncmemsim.dtco.compare_nominal | ncmemsim.dtco.robust.compare_nominal | function |
| ncmemsim.dtco.evaluate_nominal | ncmemsim.dtco.robust.evaluate_nominal | function |
| ncmemsim.dtco.propagate_samples | ncmemsim.dtco.propagation.propagate_samples | function |
| ncmemsim.dtco.run_cartesian_sweep | ncmemsim.dtco.sweep.run_cartesian_sweep | function |
| ncmemsim.dtco.sample_variations | ncmemsim.dtco.sampling.sample_variations | function |
| ncmemsim.dtco.write_dtco_report | ncmemsim.dtco.reporting.write_dtco_report | function |
| ncmemsim.dtco.write_robust_dtco_report | ncmemsim.dtco.robust_reporting.write_robust_dtco_report | function |
| ncmemsim.experimental.DeviceObservableDataset | ncmemsim.experimental.DeviceObservableDataset | class |
| ncmemsim.experimental.ExperimentalCondition | ncmemsim.experimental.ExperimentalCondition | class |
| ncmemsim.experimental.ExperimentalDatasetMetadata | ncmemsim.experimental.ExperimentalDatasetMetadata | class |
| ncmemsim.experimental.OpticalAbsorptionDataset | ncmemsim.experimental.OpticalAbsorptionDataset | class |
| ncmemsim.fit_diagnostics.FitUncertaintyDiagnostics | ncmemsim.fit_diagnostics.FitUncertaintyDiagnostics | class |
| ncmemsim.fit_diagnostics.analyze_fit_uncertainty | ncmemsim.fit_diagnostics.analyze_fit_uncertainty | function |
| ncmemsim.fitting.FitParameter | ncmemsim.fitting.FitParameter | class |
| ncmemsim.fitting.FitParameterSet | ncmemsim.fitting.FitParameterSet | class |
| ncmemsim.io.load_optical_absorption_csv | ncmemsim.io.load_optical_absorption_csv | function |
| ncmemsim.make_ge | ncmemsim.materials.models.ge.make_ge | function |
| ncmemsim.make_gesn | ncmemsim.materials.models.gesn.make_gesn | function |
| ncmemsim.make_v53_reference_device | ncmemsim.reference.make_v53_reference_device | function |
| ncmemsim.materials.BarrierModel | ncmemsim.materials.band_alignment.barriers.BarrierModel | class |
| ncmemsim.materials.HFO2 | ncmemsim.materials.presets.HFO2 | declared_value |
| ncmemsim.materials.optics.CompositeGeSnAbsorptionModel | ncmemsim.materials.optics.models.CompositeGeSnAbsorptionModel | class |
| ncmemsim.materials.optics.EvaluationDomainStatus | ncmemsim.materials.optics.domain.EvaluationDomainStatus | class |
| ncmemsim.materials.optics.GESN_NEAR_EDGE_FIT_PARAMETER_NAMES | ncmemsim.materials.optics.near_edge_fit.GESN_NEAR_EDGE_FIT_PARAMETER_NAMES | declared_value |
| ncmemsim.materials.optics.GeSnNearEdgeCalibrationResult | ncmemsim.materials.optics.near_edge_calibration.GeSnNearEdgeCalibrationResult | class |
| ncmemsim.materials.optics.GeSnNearEdgeFitResult | ncmemsim.materials.optics.near_edge_fit.GeSnNearEdgeFitResult | class |
| ncmemsim.materials.optics.GeSnNearEdgeParameterSet | ncmemsim.materials.optics.near_edge.GeSnNearEdgeParameterSet | class |
| ncmemsim.materials.optics.GeSnNearEdgeReferenceModel | ncmemsim.materials.optics.near_edge.GeSnNearEdgeReferenceModel | class |
| ncmemsim.materials.optics.NearEdgeBranch | ncmemsim.materials.optics.near_edge.NearEdgeBranch | class |
| ncmemsim.materials.optics.NearEdgeOpticalPoint | ncmemsim.materials.optics.near_edge.NearEdgeOpticalPoint | class |
| ncmemsim.materials.optics.OpticalValidationDomain | ncmemsim.materials.optics.domain.OpticalValidationDomain | class |
| ncmemsim.materials.optics.TRAN_2016_NEAR_EDGE_DOMAIN | ncmemsim.materials.optics.domain.TRAN_2016_NEAR_EDGE_DOMAIN | declared_value |
| ncmemsim.materials.optics.TRAN_2016_NEAR_EDGE_PARAMETERS | ncmemsim.materials.optics.near_edge.TRAN_2016_NEAR_EDGE_PARAMETERS | declared_value |
| ncmemsim.materials.optics.fit_gesn_near_edge_absorption | ncmemsim.materials.optics.near_edge_fit.fit_gesn_near_edge_absorption | function |
| ncmemsim.materials.optics.predict_gesn_near_edge_absorption_m_inv | ncmemsim.materials.optics.near_edge_fit.predict_gesn_near_edge_absorption_m_inv | function |
| ncmemsim.materials.optics.qualify_gesn_near_edge_fit | ncmemsim.materials.optics.near_edge_calibration.qualify_gesn_near_edge_fit | function |
| ncmemsim.optics.LightSource | ncmemsim.optics.LightSource | class |
| ncmemsim.paired_pulse_protocol.PairedPulseMemoryProtocol | ncmemsim.paired_pulse_protocol.PairedPulseMemoryProtocol | class |
| ncmemsim.paired_pulse_protocol.PairedPulseMemoryResult | ncmemsim.paired_pulse_protocol.PairedPulseMemoryResult | class |
| ncmemsim.paired_pulse_protocol.PulseBranchResult | ncmemsim.paired_pulse_protocol.PulseBranchResult | class |
| ncmemsim.paired_pulse_protocol.run_paired_pulse_memory_protocol | ncmemsim.paired_pulse_protocol.run_paired_pulse_memory_protocol | function |
| ncmemsim.photo.PhotoTransitionConfig | ncmemsim.photo.PhotoTransitionConfig | class |
| ncmemsim.photo.PhotoTransitionWeights | ncmemsim.photo.PhotoTransitionWeights | class |
| ncmemsim.photo_calibration.CalibratedPhotoCaptureEfficiency | ncmemsim.photo_calibration.CalibratedPhotoCaptureEfficiency | class |
| ncmemsim.photo_calibration.DevicePhotoCalibrationResult | ncmemsim.photo_calibration.DevicePhotoCalibrationResult | class |
| ncmemsim.photo_calibration.qualify_photo_capture_efficiency_fit | ncmemsim.photo_calibration.qualify_photo_capture_efficiency_fit | function |
| ncmemsim.photo_program_fit.DevicePhotoMultiConditionFitResult | ncmemsim.photo_program_fit.DevicePhotoMultiConditionFitResult | class |
| ncmemsim.photo_program_fit.DevicePhotoProgramTimeFitResult | ncmemsim.photo_program_fit.DevicePhotoProgramTimeFitResult | class |
| ncmemsim.photo_program_fit.ElectroOpticalProgramTimeFitProtocol | ncmemsim.photo_program_fit.ElectroOpticalProgramTimeFitProtocol | class |
| ncmemsim.photo_program_fit.ElectroOpticalProgramTimePrediction | ncmemsim.photo_program_fit.ElectroOpticalProgramTimePrediction | class |
| ncmemsim.photo_program_fit.fit_single_parameter_photo_capture_efficiency_multi_condition | ncmemsim.photo_program_fit.fit_single_parameter_photo_capture_efficiency_multi_condition | function |
| ncmemsim.photo_program_fit.fit_single_parameter_photo_capture_efficiency_vs_programming_time | ncmemsim.photo_program_fit.fit_single_parameter_photo_capture_efficiency_vs_programming_time | function |
| ncmemsim.photo_program_fit.predict_electro_optical_delta_vfb_vs_programming_time | ncmemsim.photo_program_fit.predict_electro_optical_delta_vfb_vs_programming_time | function |
| ncmemsim.physics.PhysicsModel | ncmemsim.physics.PhysicsModel | class |
| ncmemsim.program_fit.DeviceProgramTimeFitResult | ncmemsim.program_fit.DeviceProgramTimeFitResult | class |
| ncmemsim.program_fit.ProgramTimeFitProtocol | ncmemsim.program_fit.ProgramTimeFitProtocol | class |
| ncmemsim.program_fit.ProgramTimePrediction | ncmemsim.program_fit.ProgramTimePrediction | class |
| ncmemsim.program_fit.fit_single_parameter_delta_vfb_vs_programming_time | ncmemsim.program_fit.fit_single_parameter_delta_vfb_vs_programming_time | function |
| ncmemsim.program_fit.predict_delta_vfb_vs_programming_time | ncmemsim.program_fit.predict_delta_vfb_vs_programming_time | function |
| ncmemsim.program_protocol.ProgramPulseReadProtocol | ncmemsim.program_protocol.ProgramPulseReadProtocol | class |
| ncmemsim.program_protocol.ProgramPulseReadResult | ncmemsim.program_protocol.ProgramPulseReadResult | class |
| ncmemsim.program_protocol.run_program_pulse_read | ncmemsim.program_protocol.run_program_pulse_read | function |
| ncmemsim.reference.make_v53_reference_device | ncmemsim.reference.make_v53_reference_device | function |
| ncmemsim.retention.RetentionConfig | ncmemsim.retention.RetentionConfig | class |
| ncmemsim.retention_fit.DeviceRetentionFractionFitResult | ncmemsim.retention_fit.DeviceRetentionFractionFitResult | class |
| ncmemsim.retention_fit.RetentionFitProtocol | ncmemsim.retention_fit.RetentionFitProtocol | class |
| ncmemsim.retention_fit.RetentionFractionPrediction | ncmemsim.retention_fit.RetentionFractionPrediction | class |
| ncmemsim.retention_fit.fit_single_parameter_retention_fraction | ncmemsim.retention_fit.fit_single_parameter_retention_fraction | function |
| ncmemsim.retention_fit.predict_retention_fraction | ncmemsim.retention_fit.predict_retention_fraction | function |
| ncmemsim.run_benchmark_suite | ncmemsim.benchmark.run_benchmark_suite | function |
| ncmemsim.simulator.SimulationConfig | ncmemsim.simulator.SimulationConfig | class |
| ncmemsim.simulator.Simulator | ncmemsim.simulator.Simulator | class |
| ncmemsim.transport.LinkTransportResult | ncmemsim.transport.rates.LinkTransportResult | class |
| ncmemsim.transport.NodeKind | ncmemsim.transport.base.NodeKind | class |
| ncmemsim.transport.TransportConfig | ncmemsim.transport.engine.TransportConfig | class |
| ncmemsim.transport.TransportEngine | ncmemsim.transport.engine.TransportEngine | class |
| ncmemsim.transport.TransportNode | ncmemsim.transport.base.TransportNode | class |
| ncmemsim.transport.TransportStepResult | ncmemsim.transport.rates.TransportStepResult | class |
| ncmemsim.transport.TunnelLink | ncmemsim.transport.link.TunnelLink | class |
| ncmemsim.transport.TunnelNetwork | ncmemsim.transport.network.TunnelNetwork | class |
| ncmemsim.transport.base | ncmemsim.transport.base | module |
| ncmemsim.transport.engine | ncmemsim.transport.engine | module |
| ncmemsim.transport.link | ncmemsim.transport.link | module |
| ncmemsim.transport.network | ncmemsim.transport.network | module |
| ncmemsim.transport.rates | ncmemsim.transport.rates | module |
| ncmemsim.validate_device_physics | ncmemsim.validation.validate_device_physics | function |
| ncmemsim.validate_field_profile | ncmemsim.validation.validate_field_profile | function |
| ncmemsim.validate_internal_charge_conservation | ncmemsim.validation.validate_internal_charge_conservation | function |
| ncmemsim.validate_probabilities | ncmemsim.validation.validate_probabilities | function |
| ncmemsim.validate_simulation | ncmemsim.validation.validate_simulation | function |
| ncmemsim.workflows.AppliedWorkflowEvidence | ncmemsim.workflows.application.AppliedWorkflowEvidence | class |
| ncmemsim.workflows.DataOrigin | ncmemsim.workflows.evidence.DataOrigin | class |
| ncmemsim.workflows.DatasetEvidence | ncmemsim.workflows.evidence.DatasetEvidence | class |
| ncmemsim.workflows.WorkflowEvaluator | ncmemsim.workflows.application.WorkflowEvaluator | class |
| ncmemsim.workflows.WorkflowEvidence | ncmemsim.workflows.evidence.WorkflowEvidence | class |
| ncmemsim.workflows.WorkflowReport | ncmemsim.workflows.reporting.WorkflowReport | class |
| ncmemsim.workflows.apply_workflow_parameters | ncmemsim.workflows.application.apply_workflow_parameters | function |
| ncmemsim.workflows.build_workflow_evidence | ncmemsim.workflows.evidence.build_workflow_evidence | function |
| ncmemsim.workflows.build_workflow_report | ncmemsim.workflows.reporting.build_workflow_report | function |
| ncmemsim.workflows.capture_dataset_evidence | ncmemsim.workflows.evidence.capture_dataset_evidence | function |
| ncmemsim.workflows.write_workflow_report | ncmemsim.workflows.reporting.write_workflow_report | function |
| ncmemsim.write_benchmark_report | ncmemsim.benchmark.write_benchmark_report | function |
| ncmemsim.write_golden_suite | ncmemsim.golden.write_golden_suite | function |

## Proposed maintenance contract

Retain these paths, accepted existing parameter names/order/kinds/defaults and declared result fields in compatible releases.
Existing positional arguments remain supported where the recorded callable signature permits them; new examples should prefer keywords.
For explicit source methods, receiver parameters are source evidence, not caller arguments.
Constructor signatures record actual current call shape; generated/inherited implementation details are not separately frozen.
Numerical behavior, applicability and ownership are governed by the reviewed result/default manuals, not by signatures alone.
Protocol/enum signatures describe Python mechanics; they do not imply that abstract protocols are intended as concrete engines.
Deprecation/removal follows [compatibility policy](api_compatibility.md). New optional APIs may be added without invalidating old calls.

## Proposed limitations to retain

Accept current empty-sweep shape and input aliasing, shallow nested state/context ownership, writable arrays in legacy frozen containers,
None/NaN/zero conventions, strict current-schema archive readers and the legacy manifest hash/copy scope as documented.
Do not silently harden or reinterpret those behaviors in this preparation. Any later incompatible change needs a migration/major-version decision.
See [core results](api_results.md), [analysis results](api_analysis_results.md), [archives](api_archives.md),
[defaults](scientific_defaults.md), and [distribution](distribution_contracts.md).

## Proposed scientific release scope

A stable compact-model simulation/fitting/DTCO software release with explicit applicability and provisional parameters.
Synthetic workflows remain synthetic FITTED evidence. Numerical success, covariance and qualification eligibility do not imply independent experimental validation.
No new physics, all-device predictive validity, manufactured yield or experimental calibration is promised by stable software status.
Literature/model/parameter attribution retains its specific scope. New measured claims require their own dataset/provenance and validation evidence.
Out-of-model effects remain outside the contract unless explicitly introduced and tested.

## Approval still required

Review the exact list and the limitations/scientific scope above. Reject or revise individual entries before freezing; do not expand it merely to match every importable name.
The readiness matrix remains pending approval; this proposal changes no gate to approved and records no final checks as passed.
Archival/DOI planning and full final-candidate tests/build/CI/documentation remain separate requirements.
Run python scripts/validate_stable_api_proposal.py to compare the retained proposal against current source/runtime declarations.
This command detects drift; it does not regenerate the baseline, grant approval or test numerical behavior.
