"""Source linkage, snapshot isolation and scientific claim separation."""
from dataclasses import FrozenInstanceError, replace
import json
import numpy as np
import pytest
pytest.importorskip('scipy')
from ncmemsim.workflows import (DataOrigin, DatasetEvidence, WorkflowEvidence,
    capture_dataset_evidence, build_workflow_evidence)
from ncmemsim.calibration import CalibrationCriteria, qualify_calibration
from ncmemsim.device_calibration import DeviceCalibrationSpec, DeviceFitParameterBinding, DeviceFitTarget
from ncmemsim.device_fit import CVCalibrationProtocol, fit_single_parameter_cv_dataset
from ncmemsim.experimental import DeviceObservableDataset, ExperimentalDatasetMetadata, ExperimentalCondition
from ncmemsim.fitting import FitParameter, FitParameterSet, evaluate_least_squares_objective
from ncmemsim.fit_diagnostics import analyze_fit_uncertainty
from ncmemsim.hashing import canonical_hash
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig, Simulator


def evidence(dataset, origin=DataOrigin.SYNTHETIC):
    return capture_dataset_evidence(dataset, origin=origin, source='Contract test fixture', applicability='Synthetic C-V test')


@pytest.fixture(scope='module')
def sources():
    device = make_v53_reference_device(grid_points=7)
    physics = PhysicsModel.default()
    config = SimulationConfig(dwell_time_s=0.0, qfix_C_m2=0.0)
    protocol = CVCalibrationProtocol(vmin_V=-2, vmax_V=2, points=11)
    spec = DeviceCalibrationSpec(FitParameterSet((FitParameter('qfix', 0, -0.005, 0.005, unit='C/m^2'),)),
        (DeviceFitParameterBinding('qfix', DeviceFitTarget.SIMULATION_QFIX_C_M2),), name='Evidence C-V specification')
    def dataset(count, identifier):
        cv = Simulator(device, physics, replace(config, qfix_C_m2=0.0012)).simulate_cv(vmin_V=-2, vmax_V=2, points=count).forward
        return DeviceObservableDataset('gate_voltage', 'V', cv.voltages_V, 'capacitance', 'F/m^2',
            cv.capacitance_F_m2 + np.linspace(-1e-7, 1e-7, count),
            ExperimentalDatasetMetadata(identifier, 'Synthetic generated C-V'),
            conditions=(ExperimentalCondition('sweep_direction', 'forward'),))
    training = dataset(11, 'training')
    validation = dataset(13, 'validation')
    fit = fit_single_parameter_cv_dataset(training, base_device=device, base_physics=physics,
        base_simulation_config=config, calibration_spec=spec, protocol=protocol)
    diagnostic = analyze_fit_uncertainty(fit.numerical_result)
    cv = Simulator(fit.fitted_context.device, fit.fitted_context.physics,
        fit.fitted_context.simulation_config).simulate_cv(vmin_V=-2, vmax_V=2, points=13).forward
    objective = evaluate_least_squares_objective(validation.observed_values, cv.capacitance_F_m2)
    qualification = qualify_calibration(fit.numerical_result, diagnostic,
        fit_dataset_hash=training.dataset_hash(), validation_dataset_hash=validation.dataset_hash(),
        validation_objective=objective, criteria=CalibrationCriteria(max_validation_rmse=1e-5))
    return training, validation, fit, spec, diagnostic, qualification


def build(sources, qualified=True, **overrides):
    training, validation, fit, spec, diagnostic, qualification = sources
    args = dict(name='Evidence contract', fit_dataset=evidence(training), fit_result=fit,
        calibration_spec=spec, diagnostics=diagnostic, validation_dataset=evidence(validation),
        qualification=qualification if qualified else None)
    args.update(overrides)
    return build_workflow_evidence(**args)


def test_real_fit_qualification_and_snapshot_restoration(sources):
    result = build(sources)
    assert result.qualification_eligible is True
    assert result.scientific_status == 'FITTED'
    assert result.to_dict()['fit_dataset']['origin'] == 'synthetic'
    assert WorkflowEvidence.from_json(result.to_json()).to_dict() == result.to_dict()
    assert build(sources).evidence_hash == result.evidence_hash


def test_unqualified_evidence_retains_unknown_eligibility(sources):
    result = build(sources, qualified=False)
    assert result.qualification_eligible is None
    assert result.scientific_status == 'FITTED'


def test_failed_qualification_is_not_dropped_or_promoted(sources):
    q = sources[-1]
    failed = replace(q, criterion_results=(replace(q.criterion_results[0], passed=False), *q.criterion_results[1:]))
    result = build(sources, qualification=failed)
    assert result.qualification_eligible is False
    assert result.scientific_status == 'FITTED'
    assert result.to_dict()['qualification']['data']['failed_criteria']


def test_returned_json_and_source_mutation_do_not_change_evidence(sources):
    fit = replace(sources[2], fitted_context=replace(sources[2].fitted_context,
        parameter_values=dict(sources[2].fitted_context.parameter_values)))
    metadata = {'nested': [1]}
    result = build(sources, fit_result=fit, metadata=metadata)
    before = result.to_json()
    metadata['nested'].append(2)
    fit.fitted_context.parameter_values['qfix'] = 0.004
    result.to_dict()['fit_dataset']['dataset']['metadata']['dataset_id'] = 'edited'
    assert result.to_json() == before
    with pytest.raises(FrozenInstanceError): result.payload_json = '{}'


@pytest.mark.parametrize('field,value', [('source',''), ('source',' outer'), ('applicability','outer '), ('applicability',None)])
def test_provenance_is_required(sources, field, value):
    args = dict(origin=DataOrigin.SYNTHETIC, source='Declared', applicability='Near-room-temperature')
    args[field] = value
    with pytest.raises(ValueError): capture_dataset_evidence(sources[0], **args)


def test_origin_is_explicit_and_separate_from_dataset_hash(sources):
    a = evidence(sources[0]); b = evidence(sources[0], DataOrigin.MEASURED)
    assert a.dataset_hash == b.dataset_hash
    assert a.evidence_hash != b.evidence_hash
    assert DatasetEvidence.from_json(a.to_json()).origin is DataOrigin.SYNTHETIC
    with pytest.raises(TypeError): capture_dataset_evidence(sources[0], origin='synthetic', source='S', applicability='A')


@pytest.mark.parametrize('change', ['dataset', 'specification', 'application', 'protocol'])
def test_builder_rejects_source_identity_mismatch(sources, change):
    fit = replace(sources[2])
    if change == 'dataset': fit.dataset_hash = '0' * 64
    elif change == 'specification': fit.calibration_specification_hash = '0' * 64
    elif change == 'application':
        fit.fitted_context = replace(fit.fitted_context, parameter_values={'qfix': 0.004})
    else: fit.protocol = replace(fit.protocol, vmax_V=3)
    # Protocol self-consistent replacement is declared evidence, so tamper the
    # stored hash during restoration rather than pretend this class attests history.
    if change == 'protocol':
        data = build(sources).to_dict(); data['fit_result']['data']['protocol_hash'] = '0'*64
        data['fit_result']['source_hash'] = canonical_hash(data['fit_result']['data'])
        data.pop('evidence_hash'); data['evidence_hash'] = canonical_hash(data)
        with pytest.raises(ValueError, match='protocol'): WorkflowEvidence.from_json(json.dumps(data))
    else:
        with pytest.raises(ValueError, match='mismatch'): build(sources, fit_result=fit)


@pytest.mark.parametrize('field', ['validation_dataset', 'diagnostics'])
def test_qualification_requires_linked_evidence(sources, field):
    with pytest.raises(ValueError, match='requires'): build(sources, **{field: None})


def test_unrelated_diagnostics_rejected(sources):
    with pytest.raises(ValueError, match='diagnostics do not describe'):
        build(sources, diagnostics=replace(sources[4], residual_variance=sources[4].residual_variance + 1))


def test_qualification_dataset_link_rejected(sources):
    with pytest.raises(ValueError, match='qualification dataset'):
        build(sources, qualification=replace(sources[-1], validation_dataset_hash='0'*64))


@pytest.mark.parametrize('field,value', [('schema_version','unknown'), ('scientific_status','CALIBRATED')])
def test_rehashed_payload_cannot_bypass_semantic_links(sources, field, value):
    data = build(sources).to_dict()
    if field == 'schema_version': data[field] = value
    else:
        data['fit_result']['data'][field] = value
        data['fit_result']['source_hash'] = canonical_hash(data['fit_result']['data'])
    data.pop('evidence_hash'); data['evidence_hash'] = canonical_hash(data)
    with pytest.raises(ValueError): WorkflowEvidence.from_json(json.dumps(data))


def test_payload_tampering_and_duplicate_keys_rejected(sources):
    result = build(sources);data = result.to_dict();data['name'] = 'tampered'
    with pytest.raises(ValueError, match='integrity'): WorkflowEvidence.from_json(json.dumps(data))
    with pytest.raises(ValueError, match='duplicate'):
        WorkflowEvidence.from_json(result.to_json().replace('{', '{"name":"duplicate",',1))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), np.array([1]), (1,2)])
def test_non_json_metadata_rejected(sources, value):
    with pytest.raises((ValueError,TypeError)): build(sources, metadata={'invalid':value})


def test_infinite_rank_diagnostic_is_explicit_and_restorable(sources):
    numerical = replace(sources[2].numerical_result, jacobian=np.zeros_like(sources[2].numerical_result.jacobian))
    fit = replace(sources[2], numerical_result=numerical)
    diagnostic = analyze_fit_uncertainty(numerical)
    result = build(sources, qualified=False, fit_result=fit, diagnostics=diagnostic)
    assert result.to_dict()['diagnostics']['data']['scaled_condition_number'] == {'_workflow_float':'positive_infinity'}
    assert result.to_dict()['diagnostics']['data']['covariance_matrix'] is None
    assert WorkflowEvidence.from_json(result.to_json()).evidence_hash == result.evidence_hash


@pytest.mark.parametrize('argument', ['fit_dataset','fit_result','calibration_spec','diagnostics','qualification'])
def test_wrong_source_types_rejected(sources, argument):
    with pytest.raises(TypeError): build(sources, **{argument: {}})

@pytest.mark.parametrize('fault', ['shape','unit','unknown_field'])
def test_rehashed_invalid_dataset_snapshot_rejected(sources, fault):
    raw = evidence(sources[0]).to_dict()
    if fault == 'shape': raw['dataset']['observable']['values'] = [1.0]
    elif fault == 'unit': raw['dataset']['observable']['unit'] = ''
    else: raw['dataset']['unknown'] = True
    raw['dataset_hash'] = canonical_hash(raw['dataset'])
    raw.pop('evidence_hash'); raw['evidence_hash'] = canonical_hash(raw)
    with pytest.raises(ValueError): DatasetEvidence.from_json(json.dumps(raw))


def test_validation_units_must_match_training(sources):
    other = replace(sources[1], observable_unit='V')
    with pytest.raises(ValueError, match='observable/variable'):
        build(sources, validation_dataset=evidence(other))


def test_restoration_does_not_recompute_diagnostics_or_qualification(sources, monkeypatch):
    result = build(sources)
    import ncmemsim.workflows.evidence as module
    def forbidden(*args, **kwargs): raise AssertionError('unexpected scientific computation')
    monkeypatch.setattr(module, 'analyze_fit_uncertainty', forbidden)
    monkeypatch.setattr('ncmemsim.calibration.qualify_calibration', forbidden)
    assert WorkflowEvidence.from_json(result.to_json()).to_dict() == result.to_dict()


def test_declared_foreign_runtime_is_preserved_not_replaced(sources):
    result = build(sources); data = result.to_dict(); data['runtime']['numpy'] = 'future-runtime'
    data.pop('evidence_hash'); data['evidence_hash'] = canonical_hash(data)
    restored = WorkflowEvidence.from_json(json.dumps(data))
    assert restored.to_dict()['runtime']['numpy'] == 'future-runtime'
    assert restored.evidence_hash != result.evidence_hash


def test_optical_dataset_snapshot_uses_existing_domain_contracts():
    from ncmemsim.experimental import OpticalAbsorptionDataset
    dataset = OpticalAbsorptionDataset(np.array([1300.,1400.]), np.array([100.,200.]), 0.1,
        ExperimentalDatasetMetadata('optical','Synthetic optical fixture'))
    result = evidence(dataset)
    assert DatasetEvidence.from_json(result.to_json()).dataset_hash == dataset.dataset_hash()


@pytest.mark.parametrize('fault', ['criteria_hash','accounting','diagnostic_link','float_marker'])
def test_rehashed_qualification_corruption_rejected(sources, fault):
    data = build(sources).to_dict()
    q = data['qualification']['data']
    if fault == 'criteria_hash': q['criteria_hash'] = '0'*64
    elif fault == 'accounting': q['eligible_for_calibration'] = not q['eligible_for_calibration']
    elif fault == 'diagnostic_link': q['uncertainty_diagnostics']['scaled_condition_number'] = 100.0
    else: q['uncertainty_diagnostics']['scaled_condition_number'] = {'_workflow_float':'invalid'}
    if fault != 'float_marker': data['qualification']['source_hash'] = canonical_hash(q)
    data.pop('evidence_hash'); data['evidence_hash'] = canonical_hash(data)
    with pytest.raises(ValueError): WorkflowEvidence.from_json(json.dumps(data))


def test_dataset_origin_tampering_requires_new_evidence_identity(sources):
    data = evidence(sources[0]).to_dict();data['origin'] = 'measured'
    with pytest.raises(ValueError, match='integrity'):
        DatasetEvidence.from_json(json.dumps(data))

@pytest.mark.parametrize('kind', ['wheel','sdist'])
@pytest.mark.parametrize('missing', ['ncmemsim/workflows/__init__.py','ncmemsim/workflows/evidence.py'])
def test_distribution_rejects_missing_workflow_contracts(tmp_path, kind, missing):
    import io, tarfile, zipfile
    from scripts.validate_dtco_distribution import REQUIRED, SOURCE_REQUIRED, check_archive
    names = (REQUIRED if kind == 'wheel' else REQUIRED | SOURCE_REQUIRED) - {missing}
    path = tmp_path / ('contract.whl' if kind == 'wheel' else 'contract.tar.gz')
    if kind == 'wheel':
        with zipfile.ZipFile(path, 'w') as archive:
            for name in names: archive.writestr(name, '')
    else:
        with tarfile.open(path, 'w:gz') as archive:
            for name in names: archive.addfile(tarfile.TarInfo('contract/'+name), io.BytesIO(b''))
    with pytest.raises(ValueError, match=missing): check_archive(path)
