# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R4 original-data ownership, dimensional conversion and missing-condition controls."""
import json
import pytest
from ncmemsim.interoperability import (InteroperabilitySource, InteroperabilityDataset,
    ObservableMapping, convert_interoperability_data)


def dataset(quantity='position', unit='nm', values=None, exclusions=None, missing=None):
    source = InteroperabilitySource('synthetic-r4', 'a'*64, 'synthetic-generator',
        '1', {'model': 'analytical control; no TCAD export'}, 'synthetic test only')
    fields = {'geometry_materials': ('layers','contacts'), 'contacts_bias': ('contact_voltages',),
        'history': ('sweep_direction','prior_operations'), 'initial_state': ('description',),
        'time_conditions': ('description',), 'frequency_conditions': ('description',),
        'coordinates': ('origin','axis_direction','layer_order'),
        'potential_reference': ('description',), 'energy_reference': ('description',),
        'applicability': ('scope','limitations'),
        'optical_conditions': ('sample_plane_spectrum','normalization','reflection',
            'generation_assumptions','contributing_regions')}
    metadata = {name: {key:'synthetic explicitly assumed condition' for key in keys}
                for name,keys in fields.items()}
    metadata.update(temperature_K=300., area_m2=2e-12, electron_charge_sign='negative')
    if missing: metadata[missing] = None
    return InteroperabilityDataset('control', source, metadata,
        [dict(name='x', quantity=quantity, unit=unit, values=[0., 2., 5.] if values is None else values)],
        [] if exclusions is None else exclusions)


def mapping(d, quantity='position', unit='m', sign=1, offset=0., area='none'):
    return ObservableMapping(d.contract_hash, 'x', quantity, unit, sign, offset, area,
                             'explicit synthetic dimensional/reference conversion')


@pytest.mark.parametrize('cls', [InteroperabilitySource, InteroperabilityDataset, ObservableMapping])
def test_strict_roundtrip_and_ownership(cls):
    d=dataset(); obj={InteroperabilitySource: InteroperabilitySource.from_dict(d.to_dict()['source']),
                     InteroperabilityDataset: d, ObservableMapping: mapping(d)}[cls]
    raw=obj.to_dict(); assert cls.from_json(obj.to_json()).contract_hash == obj.contract_hash
    raw['schema_version']='changed'
    with pytest.raises(ValueError): cls.from_dict(raw)
    raw=obj.to_dict(); raw['unexpected']=1
    with pytest.raises(ValueError): cls.from_dict(raw)
    with pytest.raises((AttributeError, TypeError)): obj.extra=1
    with pytest.raises(ValueError): cls.from_json('{"a":1,"a":2}')
    with pytest.raises(ValueError): cls.from_json('{"a":NaN}')


def test_coordinate_reversal_retains_original_order_and_exclusions():
    d=dataset(exclusions=[{'index':1,'reason':'synthetic missing calibration'}])
    m=mapping(d,sign=-1,offset=1e-8)
    result=convert_interoperability_data(d,m)
    assert result['values']==pytest.approx([1e-8,5e-9])
    assert result['included_indices']==[0,2]
    assert result['original_dataset']==d.to_dict()
    result['original_dataset']['columns'][0]['values'][0]=999
    assert d.to_dict()['columns'][0]['values'][0]==0
    assert not result['experimental_qualification'] and not result['external_agreement']


@pytest.mark.parametrize('quantity,unit,target,targetunit,area,expected', [
    ('total_charge','C','charge_per_area','C/m^2','divide_by_area',1.),
    ('charge_per_area','C/m^2','total_charge','C','multiply_by_area',4e-24),
    ('small_signal_capacitance','F','small_signal_capacitance_per_area','F/m^2','divide_by_area',1.),
    ('current','A','current_per_area','A/m^2','divide_by_area',1.),
    ('optical_transition_energy','eV','optical_transition_energy','J','none',2e-12*1.602176634e-19)])
def test_explicit_dimension_conversion(quantity,unit,target,targetunit,area,expected):
    d=dataset(quantity,unit,[2e-12]); result=convert_interoperability_data(d,mapping(d,target,targetunit,area=area))
    assert result['values']==pytest.approx([expected],rel=1e-14,abs=0)


@pytest.mark.parametrize('name', ['geometry_materials','contacts_bias','temperature_K','history',
    'initial_state','time_conditions','coordinates','electron_charge_sign','applicability'])
def test_missing_conditions_never_fabricate_comparison(name):
    d=dataset(missing=name); result=convert_interoperability_data(d,mapping(d))
    assert result['status']=='unavailable' and name in result['missing_conditions']
    assert result['values'] is None and result['original_dataset']==d.to_dict()


@pytest.mark.parametrize('q,u,missing', [('total_charge','C','area_m2'),
    ('small_signal_capacitance','F','frequency_conditions'),
    ('potential','V','potential_reference'),
    ('optical_transition_energy','eV','optical_conditions'),
    ('tunnelling_barrier_energy','eV','energy_reference')])
def test_observable_specific_missing_conditions(q,u,missing):
    d=dataset(q,u,missing=missing)
    m=mapping(d,'charge_per_area','C/m^2',area='divide_by_area') if q=='total_charge' else mapping(d,q,u)
    assert convert_interoperability_data(d,m)['missing_conditions']==[missing]


@pytest.mark.parametrize('original,target,unit', [
    ('signed_flat_band_shift','absolute_threshold_voltage','V'),
    ('small_signal_capacitance','compact_capacitance_readout','F'),
    ('optical_transition_energy','tunnelling_barrier_energy','eV')])
def test_semantic_substitution_rejected(original,target,unit):
    d=dataset(original,unit)
    with pytest.raises(ValueError): convert_interoperability_data(d,mapping(d,target,unit))


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),10**400])
def test_invalid_original_numbers(value):
    with pytest.raises(ValueError): dataset(values=[value])


@pytest.mark.parametrize('exclusions',[[{'index':True,'reason':'x'}],
    [{'index':4,'reason':'x'}],[{'index':0,'reason':'x'},{'index':0,'reason':'y'}]])
def test_invalid_exclusions(exclusions):
    with pytest.raises(ValueError): dataset(exclusions=exclusions)


def test_all_excluded_and_overflow_are_not_success():
    d=dataset(values=[1.],exclusions=[{'index':0,'reason':'all excluded'}])
    assert convert_interoperability_data(d,mapping(d))['status']=='unavailable'
    d=dataset('position','m',[1e308])
    with pytest.raises(ValueError): convert_interoperability_data(d,mapping(d,unit='nm'))


def test_source_and_mapping_identity_must_match():
    d=dataset(); other=dataset(values=[4.])
    with pytest.raises(ValueError): convert_interoperability_data(other,mapping(d))
    raw=d.to_dict(); raw['columns'].append(dict(name='y',quantity='position',unit='nm',values=[1.]))
    with pytest.raises(ValueError): InteroperabilityDataset.from_dict(raw)
    raw=d.to_dict(); raw['columns'][0]['unit']='V'
    with pytest.raises(ValueError): InteroperabilityDataset.from_dict(raw)
    with pytest.raises(ValueError): mapping(d,sign=True)
    with pytest.raises(ValueError): convert_interoperability_data(d,mapping(d,offset=float('inf')))


def test_incomplete_declaration_rejected():
    raw=dataset().to_dict(); raw['metadata']['coordinates']={'origin':'zero'}
    with pytest.raises(ValueError): InteroperabilityDataset.from_dict(raw)
