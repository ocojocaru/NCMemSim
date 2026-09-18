"""Actual fitted application, full context identity and fresh execution state."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import subprocess
import sys
import pytest
from test_phase_i1_workflow_evidence import sources, build
from ncmemsim.workflows import (AppliedWorkflowEvidence, WorkflowEvaluator,
    apply_workflow_parameters, build_workflow_evidence, capture_dataset_evidence, DataOrigin)
from ncmemsim.workflows.application import _context_payload
from ncmemsim.device_calibration import DeviceFitParameterBinding, DeviceFitTarget, DeviceCalibrationSpec
from ncmemsim.fitting import FitParameterSet, FitParameter
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.physics import PhysicsModel
from ncmemsim.simulator import SimulationConfig
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.electro_optical_program_protocol import ElectroOpticalProgramPulseReadProtocol, run_electro_optical_program_pulse_read
from ncmemsim.photo import PhotoTransitionConfig, PhotoTransitionWeights
from ncmemsim.optics import LightSource
from ncmemsim.hashing import canonical_hash


def adapter(sources, **overrides):
    args = dict(calibration_spec=sources[3], base_device=make_v53_reference_device(grid_points=7),
        base_physics=PhysicsModel.default(), base_simulation_config=SimulationConfig(dwell_time_s=0.0),
        base_protocol=ProgramPulseReadProtocol(3.0, 1e-7, program_internal_dt_s=1e-7),
        evaluation_id='i2-electrical-delta-vfb')
    args.update(overrides)
    return apply_workflow_parameters(build(sources), **args)


def test_actual_fit_applied_exactly_and_archive_linked(sources):
    result = adapter(sources)
    raw = result.evidence.to_dict()
    fitted = sources[2].numerical_result.fitted_parameters['qfix']
    assert raw['applied_context']['simulation_config']['qfix_C_m2'] == fitted
    assert raw['baseline_context']['simulation_config']['qfix_C_m2'] == 0.0
    assert raw['workflow_evidence']['evidence_hash'] == build(sources).evidence_hash
    assert raw['parameter_application'] == sources[2].fitted_context.parameter_application_manifest()
    assert AppliedWorkflowEvidence.from_json(result.evidence.to_json()).to_dict() == raw
    assert raw['workflow_evidence']['fit_dataset']['origin'] == 'synthetic'
    assert result.evidence.scientific_status == 'FITTED'


def test_baselines_and_each_exposed_object_are_isolated(sources):
    device, physics, config = make_v53_reference_device(grid_points=7), PhysicsModel.default(), SimulationConfig()
    before = deepcopy(_context_payload(device, physics, config, None))
    result = adapter(sources, base_device=device, base_physics=physics, base_simulation_config=config)
    assert _context_payload(device, physics, config, None) == before
    device.temperature_K = 450
    physics.tunneling.config = replace(physics.tunneling.config, field_coupling_factor=0.1)
    exposed = result.base_device
    exposed.temperature_K = 500
    result.evaluation_parameters.clear()
    assert result.base_device.temperature_K == 300
    a, b = result.fresh_simulator(), result.fresh_simulator()
    assert a.device is not b.device and a.physics is not b.physics
    assert a.physics.tunneling is a.physics.occupancy.tunneling is a.physics.transport.tunneling
    assert a.physics.tunneling is not b.physics.tunneling
    a.physics.tunneling.config = replace(a.physics.tunneling.config, field_coupling_factor=0.1)
    assert b.physics.tunneling.config.field_coupling_factor == 0.8
    with pytest.raises(FrozenInstanceError):
        result.evidence.payload_json = '{}'


@pytest.mark.parametrize('change', ['material', 'semiconductor', 'coupling', 'tunneling', 'kinetics', 'transport', 'config', 'photo', 'layer_metadata'])
def test_full_context_identity_is_stronger_than_application_hash(sources, change):
    baseline = adapter(sources).evidence.to_dict()
    device, physics, config, photo = make_v53_reference_device(grid_points=7), PhysicsModel.default(), SimulationConfig(dwell_time_s=0.0), None
    if change == 'material':
        fg = device.floating_gates()[0]
        fg.nc_material = replace(fg.nc_material, effective_mass_m0=0.2)
    elif change == 'semiconductor':
        physics.electrostatics.semiconductor = replace(physics.electrostatics.semiconductor, transition_width_V=0.3)
    elif change == 'coupling':
        physics.electrostatics.coupling_model.legacy_single_fg = False
    elif change in ('tunneling', 'kinetics', 'transport'):
        engine = getattr(physics, 'occupancy' if change == 'kinetics' else change)
        field, value = {'tunneling': ('injection_energy_eV', 0.2), 'kinetics': ('nu0_Hz', 2e12), 'transport': ('attempt_frequency_Hz', 2e9)}[change]
        engine.config = replace(engine.config, **{field: value})
    elif change == 'config':
        config = replace(config, internal_dt_s=1e-6)
    elif change == 'photo':
        photo = PhotoTransitionConfig(0.02)
    else:
        device.layers[0].metadata['source'] = 'Declared layer provenance'
    changed = adapter(sources, base_device=device, base_physics=physics, base_simulation_config=config, base_photo_config=photo).evidence.to_dict()
    assert baseline['parameter_application_hash'] == changed['parameter_application_hash']
    assert baseline['context_hash'] != changed['context_hash']
    assert baseline['evidence_hash'] != changed['evidence_hash']


def test_operating_context_changes_envelope_identity(sources):
    a = adapter(sources).evidence.to_dict()
    b = adapter(sources, base_protocol=ProgramPulseReadProtocol(4, 2e-7)).evidence.to_dict()
    assert a['context_hash'] == b['context_hash']
    assert a['evidence_hash'] != b['evidence_hash']


def test_adapter_predictions_use_applied_config_and_independent_state(sources):
    result = adapter(sources)
    device, protocol = result.base_device, result.base_protocol
    before = deepcopy(device.to_dict())
    expected = run_program_pulse_read(result.fresh_simulator(), protocol)
    first = result.evaluate(device, protocol)
    assert first['delta_vfb_V'] == expected.delta_vfb_V
    assert result.evaluate(device, protocol, object()) == first
    assert device.to_dict() == before
    changed = replace(protocol, programming_time_s=2e-7)
    assert result.evaluate(device, changed)['mean_occupation'] != first['mean_occupation']


def test_private_template_drift_fails_before_physics(sources, monkeypatch):
    result = adapter(sources)
    result._device.temperature_K = 420
    import ncmemsim.workflows.application as module
    monkeypatch.setattr(module, 'Simulator', lambda *a: pytest.fail('simulator called'))
    with pytest.raises(ValueError, match='template identity'):
        result.evaluate(make_v53_reference_device(), result._protocol)


def test_spec_mismatch_and_existing_canonical_unit_checks(sources):
    with pytest.raises(ValueError, match='specification identity'):
        adapter(sources, calibration_spec=replace(sources[3], name='Other declaration'))
    bad = DeviceCalibrationSpec(FitParameterSet((FitParameter('qfix', 0, -.005, .005, unit='V'),)),
        (DeviceFitParameterBinding('qfix', DeviceFitTarget.SIMULATION_QFIX_C_M2),))
    with pytest.raises(ValueError, match='canonical unit'):
        adapter(sources, calibration_spec=bad)


@pytest.mark.parametrize('change', ['custom_engine', 'extra_state', 'unshared', 'nonfinite'])
def test_unsupported_or_incomplete_physics_is_rejected(sources, change):
    physics = PhysicsModel.default()
    if change == 'custom_engine':
        class Custom(type(physics.tunneling)): pass
        t = Custom()
        physics.tunneling = physics.occupancy.tunneling = physics.transport.tunneling = t
    elif change == 'extra_state':
        physics.tunneling.custom_multiplier = 2
    elif change == 'unshared':
        physics.occupancy.tunneling = deepcopy(physics.tunneling)
    else:
        physics.tunneling.config = replace(physics.tunneling.config, injection_energy_eV=float('inf'))
    with pytest.raises((TypeError, ValueError)):
        adapter(sources, base_physics=physics)


@pytest.mark.parametrize('change', ['context_hash', 'application_hash', 'target', 'materials', 'protocol', 'source'])
def test_restore_rejects_tampering_and_rehashed_semantic_mismatches(sources, change):
    raw = adapter(sources).evidence.to_dict()
    if change == 'context_hash': raw['context_hash'] = '0'*64
    elif change == 'application_hash': raw['parameter_application_hash'] = '0'*64
    elif change == 'target':
        raw['applied_context']['simulation_config']['qfix_C_m2'] += 0.001
        raw['context_hash'] = canonical_hash(raw['applied_context'])
    elif change == 'materials':
        raw['applied_context']['device']['layer_material_definitions'].pop()
        raw['context_hash'] = canonical_hash(raw['applied_context'])
    elif change == 'protocol': raw['operating']['protocol']['read_dwell_time_s'] = 1.0
    else: raw['workflow_evidence']['name'] = 'Tampered source'
    raw.pop('evidence_hash')
    raw['evidence_hash'] = canonical_hash(raw)
    with pytest.raises(ValueError):
        AppliedWorkflowEvidence.from_json(json.dumps(raw))


def test_restore_runs_no_application_fit_or_simulator(sources, monkeypatch):
    source = adapter(sources).evidence
    import ncmemsim.workflows.application as module
    def forbidden(*args, **kwargs): pytest.fail('execution during archive restoration')
    monkeypatch.setattr(module, 'apply_device_calibration_parameters', forbidden)
    monkeypatch.setattr(module, 'Simulator', forbidden)
    restored = AppliedWorkflowEvidence.from_json(source.to_json())
    assert restored.to_dict() == source.to_dict()


@pytest.fixture(scope='module')
def photo_adapter():
    from test_phase_f4i_photo_capture_fit import _base_objects, _synthetic_dataset, _run_fit, _eta_spec
    dataset = _synthetic_dataset()
    fit, _ = _run_fit(dataset)
    captured = capture_dataset_evidence(dataset, origin=DataOrigin.SYNTHETIC,
        source='Generated photo recovery fixture', applicability='Software verification only')
    workflow = build_workflow_evidence(name='I2 synthetic photo application', fit_dataset=captured,
        fit_result=fit, calibration_spec=_eta_spec())
    device, physics, config, photo = _base_objects()
    protocol = ElectroOpticalProgramPulseReadProtocol(ProgramPulseReadProtocol(2, 1e-4, program_internal_dt_s=1e-5),
        LightSource.laser(1550, 1000), PhotoTransitionWeights())
    result = apply_workflow_parameters(workflow, calibration_spec=_eta_spec(), base_device=device,
        base_physics=physics, base_simulation_config=config, base_photo_config=photo,
        base_protocol=protocol, evaluation_id='i2-photo-delta-vfb')
    return result, fit, photo


def test_actual_photo_fit_is_applied_at_execution(photo_adapter):
    result, fit, baseline = photo_adapter
    eta = fit.fitted_context.photo_config.photo_capture_efficiency
    assert result.evidence.to_dict()['applied_context']['photo_config']['photo_capture_efficiency'] == eta
    protocol = result.base_protocol
    direct = run_electro_optical_program_pulse_read(result.fresh_simulator(), protocol,
        photo_config=PhotoTransitionConfig(eta))
    actual = result.evaluate(result.base_device, protocol)
    assert actual['delta_vfb_V'] == direct.delta_vfb_V
    other = run_electro_optical_program_pulse_read(result.fresh_simulator(), protocol, photo_config=baseline)
    assert abs(actual['delta_vfb_V'] - other.delta_vfb_V) > 1e-9
    assert result.evaluate(result.base_device, protocol) == actual


@pytest.mark.parametrize('change', ['family', 'integrator', 'weights', 'source'])
def test_optical_fixed_model_mismatches_are_rejected(photo_adapter, change):
    result = photo_adapter[0]
    protocol = result.base_protocol
    if change == 'family': protocol = protocol.electrical_protocol
    elif change == 'integrator': protocol = replace(protocol, occupancy_integrator='backward_euler')
    elif change == 'weights': protocol = replace(protocol, photo_weights=PhotoTransitionWeights(r01=2))
    else: protocol = replace(protocol, light_source=replace(protocol.light_source, source_type='led'))
    with pytest.raises(ValueError): result.evaluate(result.base_device, protocol)


def test_optical_operating_bindings_remain_supported(photo_adapter):
    from ncmemsim.dtco import ParameterBinding, BindingScope, apply_operating_binding
    result = photo_adapter[0]
    protocol = apply_operating_binding(result.base_protocol,
        ParameterBinding(BindingScope.OPERATING, ('optical', 'power_density_W_m2')), 500.0)
    assert result.evaluate(result.base_device, protocol)['delta_vfb_V'] != result.evaluate(result.base_device, result.base_protocol)['delta_vfb_V']


def test_public_imports_do_not_load_optional_scipy():
    subprocess.run([sys.executable, '-c', 'import sys; from ncmemsim.workflows import AppliedWorkflowEvidence, WorkflowEvaluator, apply_workflow_parameters; assert "scipy" not in sys.modules'], check=True)


@pytest.mark.parametrize('target', [t for t in DeviceFitTarget if t is not DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY])
def test_each_supported_nonphoto_target_uses_existing_application_api(sources, target):
    # Zero-dwell C-V does not identify every target. These real fits exercise
    # application compatibility, not parameter recovery or qualification.
    from ncmemsim.device_fit import CVCalibrationProtocol, fit_single_parameter_cv_dataset
    from ncmemsim.device_calibration import apply_device_calibration_parameters
    values = {'fg.electrically_active_fraction': .2, 'fg.nc_volume_fraction': .1,
        'fg.nc_diameter_nm': 5., 'fg.phi_barrier_prog_eV': 1.7, 'fg.phi_barrier_erase_eV': 1.8,
        'kinetics.nu0_Hz': 2e12, 'kinetics.nu1_Hz': 2e10, 'kinetics.nu2_Hz': 6e9,
        'kinetics.capacitance_eps_r': 9., 'tunneling.injection_energy_eV': .2,
        'tunneling.oxide_effective_mass_m0': .2, 'tunneling.field_coupling_factor': .7,
        'tunneling.activation_beta_V_inv': .9, 'simulation.qfix_C_m2': .001,
        'simulation.qit_C_m2': .001}
    value = values[target.value]
    binding = DeviceFitParameterBinding('parameter', target, 0 if target.value.startswith('fg.') else None)
    spec = DeviceCalibrationSpec(FitParameterSet((FitParameter('parameter', value, value*.5, value*1.5,
        unit=binding.canonical_unit),)), (binding,))
    d, p, c = make_v53_reference_device(grid_points=7), PhysicsModel.default(), SimulationConfig(dwell_time_s=0.)
    fit = fit_single_parameter_cv_dataset(sources[0], base_device=d, base_physics=p,
        base_simulation_config=c, calibration_spec=spec, protocol=CVCalibrationProtocol(-2, 2, 11))
    captured = capture_dataset_evidence(sources[0], origin=DataOrigin.SYNTHETIC,
        source='Application contract test', applicability='No recovery claim for insensitive targets')
    evidence = build_workflow_evidence(name='Target application', fit_dataset=captured, fit_result=fit, calibration_spec=spec)
    result = apply_workflow_parameters(evidence, calibration_spec=spec, base_device=d, base_physics=p,
        base_simulation_config=c, base_protocol=ProgramPulseReadProtocol(3, 1e-7), evaluation_id='i2-target')
    expected = apply_device_calibration_parameters(d, p, c, spec, fit.numerical_result.fitted_values)
    assert result.evidence.to_dict()['applied_context'] == _context_payload(expected.device,
        expected.physics, expected.simulation_config, expected.photo_config)
    assert AppliedWorkflowEvidence.from_json(result.evidence.to_json()).to_dict() == result.evidence.to_dict()


def test_phase_h_nominal_sample_contexts_match_and_failures_remain_visible(sources):
    from ncmemsim.dtco import (SamplingSpec, VariationDefinition, ParameterBinding, BindingScope,
        UniformVariation, VariationKind, VariationProvenance, sample_variations, propagate_samples,
        evaluate_nominal, MetricDefinition, MetricAnalysisSpec, SampleAnalysisSpec, analyze_samples, compare_nominal)
    result = adapter(sources)
    variations = (VariationDefinition('temperature', ParameterBinding(BindingScope.DEVICE, ('temperature_K',)),
        UniformVariation(295, 305), 'K', VariationKind.PARAMETER_ESTIMATION,
        VariationProvenance('Assumed', 'Software test')),
        VariationDefinition('duration', ParameterBinding(BindingScope.OPERATING, ('program', 'time_s')),
        UniformVariation(1e-7, 2e-7), 's', VariationKind.PARAMETER_ESTIMATION, VariationProvenance('Assumed', 'Software test')))
    manifest = sample_variations(SamplingSpec(variations, 42, 3))
    common = dict(evaluation_id=result.evaluation_id, evaluation_parameters=result.evaluation_parameters,
        base_protocol=result.base_protocol)
    nominal = evaluate_nominal(result.base_device, result.evaluate, **common)
    propagated = propagate_samples(manifest, result.base_device, result.evaluate, **common)
    assert propagated.success_count == 3 and propagated.failure_count == 0
    analysis = analyze_samples(propagated, SampleAnalysisSpec(MetricAnalysisSpec('delta-vfb',
        (MetricDefinition('delta_vfb', ('delta_vfb_V',), 'V'),))))
    assert compare_nominal(analysis, nominal).to_dict()['status'] == 'assessed'
    for point in propagated.points:
        assert point.output['delta_vfb_V'] != nominal.output['delta_vfb_V']
    def failed(candidate, protocol, point):
        if point.index == 1:
            return result.evaluate(candidate, None, point)
        return result.evaluate(candidate, protocol, point)
    with_failure = propagate_samples(manifest, result.base_device, failed, **common)
    assert with_failure.success_count == 2 and with_failure.failure_count == 1
    assert with_failure.points[1].to_dict()['failure']['stage'] == 'evaluation'


def test_rehashed_unfitted_context_change_is_rejected(sources):
    raw = adapter(sources).evidence.to_dict()
    raw['applied_context']['physics']['kinetics']['nu0_Hz'] *= 2
    raw['context_hash'] = canonical_hash(raw['applied_context'])
    raw.pop('evidence_hash'); raw['evidence_hash'] = canonical_hash(raw)
    with pytest.raises(ValueError, match='undeclared application'):
        AppliedWorkflowEvidence.from_json(json.dumps(raw))


def test_foreign_runtime_preserved_in_archive_but_cannot_execute(sources):
    result = adapter(sources)
    raw = result.evidence.to_dict()
    raw['runtime']['numpy'] = 'foreign-runtime'
    raw.pop('evidence_hash'); raw['evidence_hash'] = canonical_hash(raw)
    restored = AppliedWorkflowEvidence.from_json(json.dumps(raw))
    assert restored.to_dict()['runtime']['numpy'] == 'foreign-runtime'
    foreign = WorkflowEvaluator(restored, result.base_device, result.base_protocol)
    with pytest.raises(ValueError, match='runtime'):
        foreign.fresh_simulator()


def test_missing_photo_settings_and_photo_target_without_illumination_fail(sources, photo_adapter):
    optical = ElectroOpticalProgramPulseReadProtocol(ProgramPulseReadProtocol(2, 1e-7),
        LightSource.laser(1550, 1000), PhotoTransitionWeights())
    with pytest.raises(ValueError, match='explicit photo'):
        adapter(sources, base_protocol=optical)
    result = photo_adapter[0]
    source = result.evidence.to_dict()
    source['operating'] = adapter(sources).evidence.to_dict()['operating']
    source.pop('evidence_hash'); source['evidence_hash'] = canonical_hash(source)
    with pytest.raises(ValueError, match='photo fitted target'):
        AppliedWorkflowEvidence.from_json(json.dumps(source))


def test_genuine_program_fit_drives_adapter_predictions():
    from test_phase_f4h_program_fit import _base_objects, _synthetic_dataset, _protocol, _nu0_spec, _strict_solver
    from ncmemsim.program_fit import fit_single_parameter_delta_vfb_vs_programming_time
    device, physics, config = _base_objects()
    dataset = _synthetic_dataset()
    fit = fit_single_parameter_delta_vfb_vs_programming_time(dataset, base_device=device, base_physics=physics,
        base_simulation_config=config, calibration_spec=_nu0_spec(), protocol=_protocol(), least_squares_config=_strict_solver())
    captured = capture_dataset_evidence(dataset, origin=DataOrigin.SYNTHETIC,
        source='Generated program recovery fixture', applicability='Software test only')
    evidence = build_workflow_evidence(name='I2 program fit application', fit_dataset=captured,
        fit_result=fit, calibration_spec=_nu0_spec())
    result = apply_workflow_parameters(evidence, calibration_spec=_nu0_spec(), base_device=device,
        base_physics=physics, base_simulation_config=config,
        base_protocol=ProgramPulseReadProtocol(3, 1e-4, program_internal_dt_s=1e-5), evaluation_id='i2-program-fit')
    assert result.fresh_simulator().physics.occupancy.config.nu0_Hz == fit.fitted_parameter_values['nu0_Hz']
    assert result.evaluate(result.base_device, result.base_protocol)['delta_vfb_V'] == fit.prediction.predicted_delta_vfb_V[0]


@pytest.mark.parametrize('kind', ['duplicate', 'nonfinite', 'missing_digest'])
def test_strict_json_envelope_rejected(sources, kind):
    source = adapter(sources).evidence.to_json()
    if kind == 'duplicate': source = source.replace('{', '{"schema_version":"duplicate",', 1)
    elif kind == 'nonfinite': source = source.replace('"context_hash":', '"unsupported":NaN,"context_hash":', 1)
    else:
        raw = json.loads(source); raw.pop('evidence_hash'); source = json.dumps(raw)
    with pytest.raises(ValueError): AppliedWorkflowEvidence.from_json(source)


@pytest.mark.parametrize('suffix', ['.whl', '.tar.gz'])
def test_distribution_inventory_requires_application_module(tmp_path, suffix):
    import io, tarfile, zipfile
    from scripts.validate_dtco_distribution import REQUIRED, SOURCE_REQUIRED, check_archive
    path = tmp_path / ('i2-contract' + suffix)
    assert 'ncmemsim/workflows/application.py' in REQUIRED
    files = (REQUIRED | (SOURCE_REQUIRED if suffix == '.tar.gz' else set())) - {'ncmemsim/workflows/application.py'}
    if suffix == '.whl':
        with zipfile.ZipFile(path, 'w') as archive:
            for name in files: archive.writestr(name, '')
    else:
        with tarfile.open(path, 'w:gz') as archive:
            for name in files:
                info = tarfile.TarInfo('source/' + name); info.size = 0
                archive.addfile(info, io.BytesIO())
    with pytest.raises(ValueError, match='application.py'): check_archive(path)
