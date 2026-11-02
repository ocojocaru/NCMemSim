# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Energy/reference ownership and strict inert barrier contracts."""
import copy
import json
import math
import pytest
from ncmemsim.barrier_contracts import (
    BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec,
    barrier_energy_eV_to_J,
)


@pytest.fixture
def objects():
    provenance = BarrierProvenance('assumed', 'synthetic fixture', 'no measurement',
        'contract checks only', 'no experimental qualification')
    left = BarrierSegment('oxide-a', 2e-9, 3e-19, 1e-19, .2, provenance)
    right = BarrierSegment('oxide-b', 4e-9, 5e-19, -1e-19, .3, provenance)
    profile = BarrierProfile('synthetic', [left, right], 2e-20,
        'common arbitrary electron energy zero', 'left physical boundary',
        'gate to substrate', 'along_positive_axis', 'gate', 'substrate',
        'isolated compact action', 'no coherent interface matching')
    spec = BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'predeclared analytic controls')
    return provenance, left, profile, spec


@pytest.mark.parametrize('index', range(4))
def test_owned_roundtrip_and_immutable(objects, index):
    obj = objects[index]
    restored = type(obj).from_json(obj.to_json())
    assert restored.to_dict() == obj.to_dict()
    assert restored.contract_hash == obj.contract_hash
    raw = obj.to_dict(); raw['schema_version'] = 'mutated'
    assert obj.to_dict()['schema_version'] != 'mutated'
    with pytest.raises(AttributeError): obj._serialized = 'mutated'
    with pytest.raises(AttributeError): del obj._serialized
    with pytest.raises(AttributeError): obj._store({})


@pytest.mark.parametrize('index', range(4))
@pytest.mark.parametrize('fault', ['unknown', 'missing', 'schema', 'duplicate', 'nonfinite'])
def test_strict_deserialization(objects, index, fault):
    obj = objects[index]; raw = obj.to_dict()
    if fault == 'duplicate':
        text = obj.to_json().replace('{', '{"schema_version":"forged",', 1)
        with pytest.raises(ValueError): type(obj).from_json(text)
        return
    if fault == 'unknown': raw['extra'] = True
    elif fault == 'missing': del raw['schema_version']
    elif fault == 'schema': raw['schema_version'] = 'unsupported'
    else: raw['extra'] = math.nan
    with pytest.raises(ValueError): type(obj).from_dict(raw)


def test_profile_preserves_discontinuity_and_original_potentials(objects):
    profile = objects[2]; raw = profile.to_dict()
    assert raw['segments'][0]['end_potential_energy_J'] == 1e-19
    assert raw['segments'][1]['start_potential_energy_J'] == 5e-19
    assert raw['incident_energy_policy'] == 'subtract_once_from_each_potential_endpoint'
    assert raw['incident_energy_J'] == 2e-20
    assert profile.total_length_m == math.fsum([2e-9, 4e-9])
    assert raw['physical_matching'] == 'not_included'


def test_nested_input_ownership(objects):
    raw = objects[2].to_dict(); profile = BarrierProfile.from_dict(raw)
    digest = profile.contract_hash
    raw['segments'][0]['provenance']['source'] = 'caller mutation'
    raw['segments'].clear()
    spec = BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'synthetic')
    nested = spec.to_dict(); nested['profile']['segments'].clear()
    assert profile.contract_hash == digest
    assert len(spec.to_dict()['profile']['segments']) == 2


def test_reversal_is_same_energy_landscape_and_involution(objects):
    profile = objects[2]; reversed_profile = profile.reversed()
    assert reversed_profile.reversed().to_json() == profile.to_json()
    raw = reversed_profile.to_dict(); original = profile.to_dict()
    assert raw['source_contact'] == original['destination_contact']
    assert raw['traversal_direction'] == 'against_positive_axis'
    assert raw['segments'][0]['segment_id'] == 'oxide-b'
    assert raw['segments'][0]['start_potential_energy_J'] == -1e-19
    for key in ('incident_energy_J', 'energy_reference', 'axis_origin', 'positive_axis_direction'):
        assert raw[key] == original[key]
    assert reversed_profile.contract_hash != profile.contract_hash


@pytest.mark.parametrize('field', ['length_m', 'effective_mass_m0'])
@pytest.mark.parametrize('value', [0, -1, True, '1', math.inf, math.nan, 10**400])
def test_positive_dimensions(objects, field, value):
    raw = objects[1].to_dict(); raw[field] = value
    with pytest.raises(ValueError): BarrierSegment.from_dict(raw)


@pytest.mark.parametrize('value', [True, '1', math.inf, -math.inf, math.nan, 10**400])
@pytest.mark.parametrize('field', ['start_potential_energy_J', 'end_potential_energy_J'])
def test_finite_signed_energy(objects, field, value):
    raw = objects[1].to_dict(); raw[field] = value
    with pytest.raises(ValueError): BarrierSegment.from_dict(raw)


@pytest.mark.parametrize('value', [-1e-19, 0, 1e-19])
def test_signed_energy_zero_is_not_an_implicit_band_edge(objects, value):
    raw = objects[2].to_dict(); raw['incident_energy_J'] = value
    raw['segments'][0]['start_potential_energy_J'] = value
    assert BarrierProfile.from_dict(raw).to_dict()['incident_energy_J'] == value


@pytest.mark.parametrize('fault', ['empty', 'duplicate_ids', 'length_overflow', 'energy_overflow',
    'carrier', 'reference', 'direction', 'contacts', 'matching', 'subtracted', 'mass_semantics'])
def test_profile_domain_and_semantic_tampering(objects, fault):
    raw = objects[2].to_dict()
    if fault == 'empty': raw['segments'] = []
    elif fault == 'duplicate_ids': raw['segments'].append(copy.deepcopy(raw['segments'][0]))
    elif fault == 'length_overflow':
        for row in raw['segments']: row['length_m'] = 1e308
    elif fault == 'energy_overflow':
        raw['incident_energy_J'] = -1e308
        raw['segments'][0]['start_potential_energy_J'] = 1e308
    elif fault == 'carrier': raw['carrier'] = 'hole'
    elif fault == 'reference': raw['energy_reference'] = ''
    elif fault == 'direction': raw['traversal_direction'] = 'automatic'
    elif fault == 'contacts': raw['source_contact'] = raw['destination_contact']
    elif fault == 'matching': raw['physical_matching'] = 'coherent'
    elif fault == 'subtracted': raw['incident_energy_policy'] = 'already_subtracted'
    else: raw['segments'][0]['mass_semantics'] = 'kg'
    with pytest.raises(ValueError): BarrierProfile.from_dict(raw)


@pytest.mark.parametrize('field', ['source', 'evidence', 'applicability', 'limitations'])
def test_provenance_cannot_omit_essential_declarations(objects, field):
    raw = objects[0].to_dict(); raw[field] = ''
    with pytest.raises(ValueError): BarrierProvenance.from_dict(raw)


def test_provenance_status_is_not_experimental_admission(objects):
    for status in ('assumed', 'reported', 'fitted'):
        raw = objects[0].to_dict(); raw['parameter_status'] = status
        obj = BarrierProvenance.from_dict(raw)
        assert obj.to_dict()['experimental_admission'] is False
    raw['parameter_status'] = 'calibrated'
    with pytest.raises(ValueError): BarrierProvenance.from_dict(raw)
    raw = objects[0].to_dict(); raw['experimental_admission'] = True
    with pytest.raises(ValueError): BarrierProvenance.from_dict(raw)


@pytest.mark.parametrize('field,value', [('exponent_atol', -1), ('exponent_rtol', True),
    ('exponent_rtol', math.inf), ('underflow_policy', 'legacy_floor'),
    ('interface_matching', True), ('simulator_attachment', True), ('evaluated', True)])
def test_inert_request_policies(objects, field, value):
    raw = objects[3].to_dict(); raw[field] = value
    with pytest.raises(ValueError): BarrierEvaluationSpec.from_dict(raw)


def test_no_zero_zero_tolerance_or_result_in_request(objects):
    with pytest.raises(ValueError): BarrierEvaluationSpec(objects[2], 0, 0, 'undefined')
    raw = objects[3].to_dict(); raw['transmission'] = .5
    with pytest.raises(ValueError): BarrierEvaluationSpec.from_dict(raw)
    assert not hasattr(objects[3], 'evaluate')


@pytest.mark.parametrize('value', [-2., 0., .1, 3.])
def test_named_signed_unit_conversion(value):
    assert barrier_energy_eV_to_J(value) == value * 1.602176634e-19


@pytest.mark.parametrize('value', [True, '1', math.nan, math.inf, 10**400, 5e-324])
def test_conversion_rejects_invalid_and_nonzero_underflow(value):
    with pytest.raises(ValueError): barrier_energy_eV_to_J(value)


def test_request_does_not_invoke_existing_evaluators(objects, monkeypatch):
    import ncmemsim.tunneling as direct
    import ncmemsim.transport.tat as tat
    def forbidden(*args, **kwargs): raise AssertionError('S1 must not evaluate transport')
    monkeypatch.setattr(direct.TunnelingEngine, 'trapezoidal_wkb', forbidden)
    monkeypatch.setattr(tat, 'linear_wkb_transmission', forbidden)
    assert BarrierEvaluationSpec.from_json(objects[3].to_json()).to_dict()['evaluated'] is False


def test_energy_reference_shift_is_preserved_not_interpreted(objects):
    raw = objects[2].to_dict(); shift = 1e-18
    differences = [(r['start_potential_energy_J'] - raw['incident_energy_J'],
                    r['end_potential_energy_J'] - raw['incident_energy_J']) for r in raw['segments']]
    raw['incident_energy_J'] += shift
    for row in raw['segments']:
        row['start_potential_energy_J'] += shift
        row['end_potential_energy_J'] += shift
    raw['energy_reference'] = 'shifted common reference'
    shifted = BarrierProfile.from_dict(raw).to_dict()
    for row, pair in zip(shifted['segments'], differences):
        assert row['start_potential_energy_J'] - shifted['incident_energy_J'] == pytest.approx(pair[0], rel=1e-14, abs=1e-33)
        assert row['end_potential_energy_J'] - shifted['incident_energy_J'] == pytest.approx(pair[1], rel=1e-14, abs=1e-33)
