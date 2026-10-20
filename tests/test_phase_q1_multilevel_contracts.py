# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Q1 ownership, invalid-input and archive boundary tests; no solver execution."""
from dataclasses import FrozenInstanceError, replace
import json
import math

import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, Simulator
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.multilevel_contracts import (
    PulseSequenceEvidence, ElectricalPulseStep, DarkReadoutPolicy,
    WeightReferenceMapping, ElectricalPulseSequence, ElectricalSequenceExperiment,
)


@pytest.fixture
def experiment():
    device = DeviceBuilder.v2(n_fgs=1)
    context = ThermalContext.from_nominal(device).resolve()
    evidence = PulseSequenceEvidence('Q1 synthetic test', 'test source', 'synthetic', 'no measured qualification')
    read = DarkReadoutPolicy('dark-common', 0, evidence)
    steps = (ElectricalPulseStep('write-1', 'program', 2, 1e-7, 1e-9),
             ElectricalPulseStep('idle-1', 'idle', 0, 2e-8, 1e-9),
             ElectricalPulseStep('erase-1', 'erase', -2, 1e-7, 1e-9))
    sequence = ElectricalPulseSequence('three steps', steps, read, evidence)
    mapping = WeightReferenceMapping('fixed pair', context.context_hash, read.contract_hash,
                                     -.2, .3, .01, 'low preparation', 'high preparation',
                                     'this device and read condition only', evidence)
    state = DeviceState.empty_for_device(device)
    state.metadata['nested'] = {'labels': ['original']}
    return ElectricalSequenceExperiment.from_state('Q1 experiment', context, sequence, state, mapping)


def contracts(experiment):
    return (experiment.sequence.evidence, experiment.sequence.steps[0], experiment.sequence.readout,
            experiment.weight_reference, experiment.sequence, experiment)


@pytest.mark.parametrize('index', range(6))
def test_roundtrip_owned_json_and_frozen_fields(experiment, index):
    value = contracts(experiment)[index]
    restored = type(value).from_json(value.to_json())
    assert restored.to_dict() == value.to_dict()
    assert restored.contract_hash == value.contract_hash
    assert len(value.contract_hash) == 64
    with pytest.raises(FrozenInstanceError):
        value.extra = 1
    payload = value.to_dict()
    payload['schema_version'] = 'caller mutation'
    assert value.to_dict()['schema_version'] != 'caller mutation'


@pytest.mark.parametrize('index', range(6))
@pytest.mark.parametrize('mutation', ['unknown', 'missing', 'version', 'duplicate', 'nan'])
def test_archive_rejection(experiment, index, mutation):
    value = contracts(experiment)[index]
    raw = value.to_dict()
    if mutation == 'unknown': raw['unknown'] = 1
    elif mutation == 'missing': raw.pop('schema_version')
    elif mutation == 'version': raw['schema_version'] = 'future-v2'
    if mutation == 'duplicate':
        text = value.to_json()[:-1] + ',"schema_version":"duplicate"}'
    elif mutation == 'nan':
        text = value.to_json()[:-1] + ',"bad":NaN}'
    else: text = json.dumps(raw)
    with pytest.raises(ValueError): type(value).from_json(text)


@pytest.mark.parametrize('bad', [True, None, '1', float('inf'), float('-inf'), float('nan'), 10**400])
@pytest.mark.parametrize('field', ['gate_voltage_V', 'duration_s', 'internal_dt_s'])
def test_strict_numeric_step_inputs(experiment, field, bad):
    with pytest.raises(ValueError): replace(experiment.sequence.steps[0], **{field: bad})


@pytest.mark.parametrize('changes', [dict(duration_s=0), dict(duration_s=-1), dict(internal_dt_s=0),
                                    dict(internal_dt_s=1), dict(role='potentiation'), dict(step_id=' '),
                                    dict(role=True), dict(duration_s=1e308, internal_dt_s=1e-308)])
def test_invalid_step_semantics(experiment, changes):
    with pytest.raises(ValueError): replace(experiment.sequence.steps[0], **changes)


@pytest.mark.parametrize('field,value', [('illumination','light'),('occupancy_integrator','explicit_euler'),
                                      ('time_unit','ms'),('voltage_unit','mV'),('waveform','ramp')])
def test_no_implicit_optical_or_unit_conversion(experiment, field, value):
    raw=experiment.sequence.steps[0].to_dict();raw[field]=value
    with pytest.raises(ValueError): ElectricalPulseStep.from_dict(raw)


@pytest.mark.parametrize('field,value', [('observable','conductance_S'),('observable_unit','S'),
                                      ('read_dwell_time_s',1e-9),('illumination','light'),
                                      ('sampling','after_train_only'),('probability_audit_atol',.01)])
def test_readout_conventions_are_fixed(experiment, field, value):
    raw=experiment.sequence.readout.to_dict();raw[field]=value
    with pytest.raises(ValueError): DarkReadoutPolicy.from_dict(raw)


@pytest.mark.parametrize('steps', [[], (), (None,), 'write', (1,)])
def test_requires_nonempty_immutable_typed_sequence(experiment, steps):
    with pytest.raises(ValueError): replace(experiment.sequence,steps=steps)


def test_order_ids_duration_and_clock(experiment):
    seq=experiment.sequence
    assert seq.to_dict()['read_count_if_complete']==4
    assert seq.to_dict()['total_duration_s']==math.fsum(s.duration_s for s in seq.steps)
    assert replace(seq,steps=tuple(reversed(seq.steps))).contract_hash!=seq.contract_hash
    with pytest.raises(ValueError): replace(seq,steps=(seq.steps[0],seq.steps[0]))
    huge=replace(seq.steps[0],duration_s=1e308,internal_dt_s=1e308)
    with pytest.raises(ValueError): replace(seq,steps=(huge,replace(huge,step_id='b')))
    with pytest.raises(ValueError): replace(seq,steps=(huge,seq.steps[1]))
    raw=seq.to_dict();raw['total_duration_s']*=2
    with pytest.raises(ValueError): ElectricalPulseSequence.from_dict(raw)
    raw=seq.to_dict();raw['read_count_if_complete']=True
    with pytest.raises(ValueError): ElectricalPulseSequence.from_dict(raw)


@pytest.mark.parametrize('changes', [dict(low_readout_V=.3),dict(high_readout_V=-.2),
    dict(minimum_span_V=0),dict(minimum_span_V=1),dict(low_readout_V=-1e308,high_readout_V=1e308),
    dict(context_hash='bad'),dict(readout_hash='A'*64),dict(low_preparation=' '),dict(evidence=None),
    dict(high_readout_V=True),dict(applicability=None)])
def test_invalid_reference_mapping(experiment,changes):
    with pytest.raises(ValueError): replace(experiment.weight_reference,**changes)


def test_reference_binding_and_no_conductance_or_calibration(experiment):
    ref=experiment.weight_reference
    assert ref.to_dict()['clipping']=='none'
    assert ref.to_dict()['weight_unit']=='1'
    assert not hasattr(ref,'evaluate') and not hasattr(ref,'normalize')
    assert not experiment.to_dict()['experimental_qualification']
    for change in ({'context_hash':'0'*64},{'readout_hash':'0'*64}):
        with pytest.raises(ValueError): replace(experiment,weight_reference=replace(ref,**change))
    assert replace(experiment,weight_reference=None).to_dict()['weight_reference'] is None
    raw=ref.to_dict();raw['weight_unit']='S'
    with pytest.raises(ValueError): WeightReferenceMapping.from_dict(raw)
    raw=ref.to_dict();raw['clipping']='[0,1]'
    with pytest.raises(ValueError): WeightReferenceMapping.from_dict(raw)


def test_deep_state_ownership_and_identity(experiment):
    state=experiment.initial_state
    raw=experiment.to_dict()
    state.floating_gates[0].P0[:]=.5
    state.metadata['nested']['labels'][0]='caller change'
    raw['initial_state']['metadata']['nested']['labels'].append('another')
    raw['context']['resolved']['device']['device']['temperature_K']=999
    assert experiment.initial_state.metadata['nested']['labels']==['original']
    assert np.all(experiment.initial_state.floating_gates[0].P0==1)
    changed=experiment.initial_state;changed.time_s=1e-3
    new=ElectricalSequenceExperiment.from_state(experiment.name,experiment.context,experiment.sequence,changed,experiment.weight_reference)
    assert new.contract_hash!=experiment.contract_hash
    changed=experiment.initial_state;changed.time_s=1e10
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_state(experiment.name,experiment.context,experiment.sequence,changed)


@pytest.mark.parametrize('mutation', ['time','count','grid','mass','boolean','metadata','schema_hash'])
def test_initial_state_and_experiment_tamper_rejected(experiment, mutation):
    raw=experiment.to_dict();state=raw['initial_state'];fg=state['floating_gates'][0]
    if mutation=='time': state['time_s']=-1
    elif mutation=='count': state['floating_gates']=[]
    elif mutation=='grid': fg['P0'].append(1)
    elif mutation=='mass': fg['P0'][0]=.9
    elif mutation=='boolean': fg['P0'][0]=True
    elif mutation=='metadata': state['metadata']['value']=float('inf')
    elif mutation=='schema_hash': raw['sequence_hash']='0'*64
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)


def test_constructor_does_not_mutate_caller_state(experiment):
    initial=experiment.initial_state
    new=ElectricalSequenceExperiment.from_state(experiment.name,experiment.context,experiment.sequence,initial)
    initial.metadata['nested']['labels'].clear()
    initial.floating_gates[0].P0[0]=0
    assert new.initial_state.metadata['nested']['labels']==['original']
    assert new.initial_state.floating_gates[0].P0[0]==1


def test_declaration_and_restoration_do_not_run_solver_optics_or_rng(experiment,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('Q1 must not execute a workflow')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(Simulator,'simulate_retention',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    import ncmemsim.materials.optics.models as models
    monkeypatch.setattr(models.CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    restored=ElectricalSequenceExperiment.from_json(experiment.to_json())
    assert restored.contract_hash==experiment.contract_hash
    assert not hasattr(restored,'run')


def test_source_declaration_does_not_certify_measurements(experiment):
    e=replace(experiment.sequence.evidence,data_kind='measured_declaration')
    assert e.to_dict()['experimental_qualification'] is False
    raw=e.to_dict();raw['experimental_qualification']=True
    with pytest.raises(ValueError): PulseSequenceEvidence.from_dict(raw)
    with pytest.raises(ValueError): replace(e,data_kind='CALIBRATED')


@pytest.mark.parametrize('field,value', [('time_s',True),('time_s',float('nan')),
                                      ('time_s',float('inf'))])
def test_initial_clock_is_finite_numeric(experiment,field,value):
    raw=experiment.to_dict();raw['initial_state'][field]=value
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)


@pytest.mark.parametrize('field,value', [('fg_id',False),('z_center_nm',True),
    ('local_field_V_m',True),('local_potential_V',float('inf'))])
def test_initial_state_coordinates_are_numeric(experiment,field,value):
    raw=experiment.to_dict();raw['initial_state']['floating_gates'][0][field]=value
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)


def test_typed_bindings_and_context_tamper(experiment):
    with pytest.raises(ValueError): replace(experiment,context=object())
    with pytest.raises(ValueError): replace(experiment,sequence=object())
    with pytest.raises(ValueError): replace(experiment.sequence,readout=object())
    raw=experiment.to_dict();raw['context_hash']='0'*64
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)
    raw=experiment.to_dict();raw['context']['resolved']['device']['device']['temperature_K']=301
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)


@pytest.mark.parametrize('mutation', ['huge_probability', 'missing_gate_field', 'gate_metadata', 'gate_list_type'])
def test_malformed_initial_archive_fails_with_value_error(experiment, mutation):
    raw=experiment.to_dict();state=raw['initial_state'];gate=state['floating_gates'][0]
    if mutation=='huge_probability': gate['P0'][0]=10**400
    elif mutation=='missing_gate_field': gate.pop('fg_id')
    elif mutation=='gate_metadata': gate['metadata']=[]
    elif mutation=='gate_list_type': state['floating_gates']='invalid'
    with pytest.raises(ValueError): ElectricalSequenceExperiment.from_dict(raw)
