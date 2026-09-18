"""Synthetic electrical fitting/qualification -> isolated nominal/Robust DTCO.

Software verification, not experimental calibration or manufacturing yield.
Requires the existing optional fit extra. No files are written without --output-dir.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys
import numpy as np

if (Path(__file__).resolve().parents[1] / 'ncmemsim').is_dir():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncmemsim.reference import make_v53_reference_device
from ncmemsim.physics import PhysicsModel
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.device_calibration import DeviceCalibrationSpec, DeviceFitParameterBinding, DeviceFitTarget
from ncmemsim.fitting import FitParameter, FitParameterSet, LeastSquaresConfig, evaluate_least_squares_objective
from ncmemsim.fit_diagnostics import analyze_fit_uncertainty
from ncmemsim.calibration import CalibrationCriteria, qualify_calibration
from ncmemsim.experimental import DeviceObservableDataset, ExperimentalDatasetMetadata, ExperimentalCondition
from ncmemsim.program_fit import (ProgramTimeFitProtocol, fit_single_parameter_delta_vfb_vs_programming_time,
    predict_delta_vfb_vs_programming_time)
from ncmemsim.workflows import (DataOrigin, capture_dataset_evidence, build_workflow_evidence,
    apply_workflow_parameters)
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation, VariationDefinition,
    VariationKind, VariationProvenance, SamplingSpec, sample_variations, propagate_samples,
    apply_device_binding,
    MetricDefinition, MetricAnalysisSpec, MetricConstraint, ConstraintOperator, SampleAnalysisSpec,
    analyze_samples, evaluate_nominal, compare_nominal, ObjectiveDirection, RobustStatistic,
    RobustFailurePolicy, RobustObjective, RobustParetoSpec, analyze_robust_pareto,
    build_robust_dtco_report, write_robust_dtco_report, RobustDTCOReport)


TRUE_NU0_HZ = 2.0e12
NOISE_SCALE_V = 1.0e-11
SYNTHETIC_WEIGHT_SCALE_V = 1.0e-10
MAX_VALIDATION_RMSE_V = 1.0e-8


def _baseline():
    return (make_v53_reference_device(grid_points=7), PhysicsModel.default(),
        SimulationConfig(internal_dt_s=1e-5))


def _dataset(times, identifier, noise):
    device, physics, config = _baseline()
    physics.occupancy.config = replace(physics.occupancy.config, nu0_Hz=TRUE_NU0_HZ)
    protocol = ProgramTimeFitProtocol(3.0, program_internal_dt_s=1e-5)
    prediction = predict_delta_vfb_vs_programming_time(Simulator(device, physics, config), times, protocol)
    return DeviceObservableDataset('programming_time', 's', times, 'delta_vfb', 'V',
        prediction.predicted_delta_vfb_V + NOISE_SCALE_V * np.asarray(noise),
        ExperimentalDatasetMetadata(identifier, 'Deterministic synthetic simulator fixture; not measurements',
            temperature_K=300.0, notes='Declared weighting scale is a software fixture, not measured uncertainty'),
        observed_uncertainty=np.full(len(times), SYNTHETIC_WEIGHT_SCALE_V),
        conditions=(ExperimentalCondition('program_voltage', 3.0, 'V'),
                    ExperimentalCondition('read_voltage', 0.0, 'V')))


def build_workflow_sources():
    """Real fit and held-out synthetic qualification; source objects stay separate."""
    training = _dataset([1e-4, 3e-4, 6e-4, 1e-3], 'i3-synthetic-training', [1, -1, 1, -1])
    validation = _dataset([1.5e-4, 4e-4, 7e-4, 9e-4], 'i3-synthetic-held-out', [.5, -.5, 1, -1])
    device, physics, config = _baseline()
    spec = DeviceCalibrationSpec(FitParameterSet((FitParameter('nu0_Hz', 5e11, 1e11, 5e12, unit='Hz'),)),
        (DeviceFitParameterBinding('nu0_Hz', DeviceFitTarget.KINETICS_NU0_HZ),), name='i3-nu0-electrical-fit')
    protocol = ProgramTimeFitProtocol(3.0, program_internal_dt_s=1e-5)
    fit = fit_single_parameter_delta_vfb_vs_programming_time(training, base_device=device,
        base_physics=physics, base_simulation_config=config, calibration_spec=spec, protocol=protocol,
        least_squares_config=LeastSquaresConfig(ftol=1e-12, xtol=1e-12, gtol=1e-12))
    diagnostic = analyze_fit_uncertainty(fit.numerical_result)
    context = fit.fitted_context
    predicted = predict_delta_vfb_vs_programming_time(Simulator(context.device, context.physics,
        context.simulation_config), validation.independent_values, protocol)
    objective = evaluate_least_squares_objective(validation.observed_values, predicted.predicted_delta_vfb_V,
        uncertainty=validation.observed_uncertainty)
    qualification = qualify_calibration(fit.numerical_result, diagnostic, fit_dataset_hash=training.dataset_hash(),
        validation_dataset_hash=validation.dataset_hash(), validation_objective=objective,
        criteria=CalibrationCriteria(max_validation_rmse=MAX_VALIDATION_RMSE_V))
    def capture(dataset):
        return capture_dataset_evidence(dataset, origin=DataOrigin.SYNTHETIC,
            source='I3 simulator-generated electrical fixture',
            applicability='Software integration only; shared generator, no independent experimental validation')
    evidence = build_workflow_evidence(name='I3 synthetic electrical sources', fit_dataset=capture(training),
        validation_dataset=capture(validation), fit_result=fit, calibration_spec=spec,
        diagnostics=diagnostic, qualification=qualification,
        metadata={'generator_nu0_Hz': TRUE_NU0_HZ, 'deterministic_noise_scale_V': NOISE_SCALE_V,
            'synthetic_weight_scale_V': SYNTHETIC_WEIGHT_SCALE_V,
            'validation_threshold_unit': 'V', 'max_validation_rmse_V': MAX_VALIDATION_RMSE_V,
            'held_out_semantics': 'Distinct times/identity, same synthetic generator; not independent measurements'})
    return evidence, spec


def build_reference_report(*, include_failures: bool = False) -> RobustDTCOReport:
    """Two DEVICE design variants reuse one fitted context and exact manifest."""
    if type(include_failures) is not bool:
        raise TypeError('include_failures must be boolean')
    evidence, spec = build_workflow_sources()
    device, physics, config = _baseline()
    adapter = apply_workflow_parameters(evidence, calibration_spec=spec, base_device=device,
        base_physics=physics, base_simulation_config=config, base_protocol=protocol_for_study(),
        evaluation_id='i3-electrical-workflow-v1')
    provenance = VariationProvenance('Assumed exploratory intervals, not inferred from fit covariance',
        'Synthetic electrical software reference only; not fabrication statistics')
    variations = (
        VariationDefinition('duration', ParameterBinding(BindingScope.OPERATING, ('program', 'time_s')),
            UniformVariation(1e-4, 3e-4), 's', VariationKind.PARAMETER_ESTIMATION, provenance),
        VariationDefinition('work_function', ParameterBinding(BindingScope.DEVICE, ('gate_work_function_eV',)),
            UniformVariation(4.7, 4.9), 'eV', VariationKind.PARAMETER_ESTIMATION, provenance))
    manifest = sample_variations(SamplingSpec(variations, seed=2026, sample_count=4))
    metrics = SampleAnalysisSpec(MetricAnalysisSpec('i3-electrical-responses', (
        MetricDefinition('signed_shift', ('delta_vfb_V',), 'V'),
        MetricDefinition('shift_magnitude', ('shift_magnitude_V',), 'V'),
        MetricDefinition('duration', ('duration_s',), 's'),
        MetricDefinition('occupation', ('mean_occupation',), '1')),
        (MetricConstraint('occupation_min', 'occupation', ConstraintOperator.GE, 0, '1'),
         MetricConstraint('occupation_max', 'occupation', ConstraintOperator.LE, 1, '1'))))
    analyses, comparisons = [], []
    for temperature in (300.0, 325.0):
        candidate = apply_device_binding(adapter.base_device,
            ParameterBinding(BindingScope.DEVICE, ('temperature_K',)), temperature)
        parameters = {**adapter.evaluation_parameters, 'reference_execution': {
            'response_transform': 'retain signed delta_vfb; magnitude=abs(delta_vfb); duration from protocol',
            'failure_demo': include_failures,
            'injection': 'index 1 evaluation; index 2 missing metrics; index 3 non-JSON output' if include_failures else 'none'}}
        def response(candidate, protocol):
            output = adapter.evaluate(candidate, protocol)
            return {**output, 'shift_magnitude_V': abs(output['delta_vfb_V']), 'duration_s': protocol.programming_time_s}
        def sampled(candidate, protocol, point):
            if include_failures:
                if point.index == 1: raise RuntimeError('Deliberate I3 software evaluation failure')
                if point.index == 2: return {}
                if point.index == 3: return {'unsupported': np.asarray([1.0])}
            return response(candidate, protocol)
        common = dict(evaluation_id=adapter.evaluation_id, evaluation_parameters=parameters,
            base_protocol=adapter.base_protocol)
        nominal = evaluate_nominal(candidate, response, **common)
        source = propagate_samples(manifest, candidate, sampled, **common)
        analysis = analyze_samples(source, metrics)
        analyses.append(analysis)
        comparisons.append(compare_nominal(analysis, nominal))
    pareto = analyze_robust_pareto(analyses, RobustParetoSpec('i3-explicit-robust-policy', (
        RobustObjective('lower_shift_magnitude', 'shift_magnitude', 'V', ObjectiveDirection.MAXIMIZE,
            RobustStatistic.QUANTILE, .05),
        RobustObjective('mean_duration', 'duration', 's', ObjectiveDirection.MINIMIZE, RobustStatistic.MEAN)),
        RobustFailurePolicy.ALLOW_ASSESSED_WITH_FAILURES if include_failures else RobustFailurePolicy.REQUIRE_NO_FAILURES,
        minimum_assessed_count=1 if include_failures else 4,
        minimum_observed_feasible_fraction=0.0 if include_failures else 1.0))
    return build_robust_dtco_report(analyses, name='I3 synthetic electrical workflow reference',
        nominal_comparisons=comparisons, robust_pareto=pareto, metadata={
            'workflow': 'phase-i3-electrical-workflow-v1', 'source_workflow_evidence': evidence.to_dict(),
            'applied_workflow_evidence_hash': adapter.evidence.evidence_hash, 'failure_demo': include_failures,
            'design_temperatures_K': [300.0, 325.0],
            'design_variant_semantics': 'Explicit DEVICE temperature variants after one fitted application; common physics/config/protocol',
            'same_exact_manifest_reused': manifest.manifest_hash,
            'scientific_status': 'FITTED', 'data_origin': 'synthetic',
            'scope': 'Software verification only; no experimental calibration or manufacturing yield',
            'constraints_applicability': 'Occupation bounds only; not a performance acceptance specification',
            'report_contract': 'Existing Phase H report; new linked workflow report schema remains I6'} )


def protocol_for_study():
    from ncmemsim.program_protocol import ProgramPulseReadProtocol
    return ProgramPulseReadProtocol(3.0, 2e-4, program_internal_dt_s=1e-5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-failures', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    report = build_reference_report(include_failures=args.include_failures)
    evidence = report.to_dict()['metadata']['source_workflow_evidence']
    print('Data origin: synthetic; scientific status: FITTED; software verification only')
    print('Synthetic qualification eligible:', evidence['qualification']['data']['eligible_for_calibration'])
    print('Report hash:', report.report_hash)
    if args.output_dir:
        for path in write_robust_dtco_report(report, args.output_dir): print(path)


if __name__ == '__main__':
    main()
