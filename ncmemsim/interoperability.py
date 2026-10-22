# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Vendor-neutral, owned simulated-data exchange; no TCAD adapter or agreement claim."""
from __future__ import annotations
import math as _math
from .performance_contracts import (_Owned, _canonical, _restore, _text, _digest)

__all__ = ['InteroperabilitySource', 'InteroperabilityDataset', 'ObservableMapping',
           'convert_interoperability_data']

_SCHEMA = 'ncmemsim-interoperability-v1'
_METADATA = ('geometry_materials', 'contacts_bias', 'temperature_K', 'history',
             'initial_state', 'time_conditions', 'frequency_conditions', 'area_m2',
             'coordinates', 'potential_reference', 'energy_reference',
             'electron_charge_sign', 'applicability', 'optical_conditions')
# Unit factors are explicit, dimensional, and never inferred from numeric values.
_UNITS = {'1': ('dimensionless', 1.), 'm': ('length', 1.),
          'nm': ('length', 1e-9), 'um': ('length', 1e-6),
          's': ('time', 1.), 'ms': ('time', 1e-3), 'us': ('time', 1e-6),
          'V': ('voltage', 1.), 'mV': ('voltage', 1e-3),
          'C': ('charge', 1.), 'C/m^2': ('charge_density', 1.),
          'F': ('capacitance', 1.), 'F/m^2': ('capacitance_density', 1.),
          'A': ('current', 1.), 'A/m^2': ('current_density', 1.),
          'eV': ('energy', 1.), 'J': ('energy', 1./1.602176634e-19)}
_QUANTITIES = {'position': 'length', 'time': 'time', 'gate_voltage': 'voltage',
    'potential': 'voltage', 'signed_flat_band_shift': 'voltage',
    'absolute_threshold_voltage': 'voltage', 'total_charge': 'charge',
    'charge_per_area': 'charge_density', 'small_signal_capacitance': 'capacitance',
    'small_signal_capacitance_per_area': 'capacitance_density',
    'compact_capacitance_readout': 'capacitance', 'current': 'current',
    'current_per_area': 'current_density', 'optical_transition_energy': 'energy',
    'tunnelling_barrier_energy': 'energy', 'occupation_fraction': 'dimensionless'}
_DECLARATIONS = {
    'geometry_materials': ('layers', 'contacts'),
    'contacts_bias': ('contact_voltages',),
    'history': ('sweep_direction', 'prior_operations'),
    'initial_state': ('description',),
    'time_conditions': ('description',),
    'frequency_conditions': ('description',),
    'coordinates': ('origin', 'axis_direction', 'layer_order'),
    'potential_reference': ('description',), 'energy_reference': ('description',),
    'applicability': ('scope', 'limitations'),
    'optical_conditions': ('sample_plane_spectrum', 'normalization', 'reflection',
                           'generation_assumptions', 'contributing_regions')}
_REQUIRED = _METADATA[:6] + ('coordinates', 'electron_charge_sign', 'applicability')


def _number(value, name, positive=False):
    if type(value) not in (int, float):
        raise ValueError(name + ' must be a finite number, not boolean')
    try:
        finite = _math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (positive and value <= 0):
        raise ValueError(name + ' outside finite domain')
    return value


def _unit(quantity, unit):
    if quantity not in _QUANTITIES or unit not in _UNITS:
        raise ValueError('unsupported quantity or explicit unit')
    if _QUANTITIES[quantity] != _UNITS[unit][0]:
        raise ValueError('quantity/unit dimension mismatch')


class InteroperabilitySource(_Owned):
    """Upstream source identity declarations; digest consistency is not authenticity."""
    __slots__ = ()

    def __init__(self, source_id, file_sha256, simulator, simulator_version, models, citation):
        for name, value in [('source_id', source_id), ('simulator', simulator),
                            ('simulator_version', simulator_version), ('citation', citation)]:
            _text(value, name)
        _digest(file_sha256, 'file_sha256')
        if type(models) is not dict or not models:
            raise ValueError('explicit model declarations required')
        self._store(dict(schema_version=_SCHEMA, evidence_kind='simulated',
            source_id=source_id, file_sha256=file_sha256, simulator=simulator,
            simulator_version=simulator_version, models=models, citation=citation))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('source_id', 'file_sha256', 'simulator',
            'simulator_version', 'models', 'citation'),
            dict(schema_version=_SCHEMA, evidence_kind='simulated'))


class InteroperabilityDataset(_Owned):
    """Ordered original columns and nullable conditions, without automatic conversions."""
    __slots__ = ()

    def __init__(self, dataset_id, source, metadata, columns, exclusions):
        _text(dataset_id, 'dataset_id')
        if isinstance(source, InteroperabilitySource):
            source = source.to_dict()
        source = InteroperabilitySource.from_dict(source).to_dict()
        if type(metadata) is not dict or set(metadata) != set(_METADATA):
            raise ValueError('all metadata keys required; unknown values must be null')
        _canonical(metadata)
        for name, value in metadata.items():
            if value is None:
                continue
            if name in ('temperature_K', 'area_m2'):
                _number(value, name, positive=True)
            elif name == 'electron_charge_sign':
                if value != 'negative':
                    raise ValueError('electron_charge_sign must be negative or null')
            elif type(value) is not dict or not value:
                raise ValueError(name + ' needs a nonempty explicit declaration object or null')
            if name in _DECLARATIONS:
                if set(value) != set(_DECLARATIONS[name]):
                    raise ValueError('missing or unknown declaration fields: ' + name)
                for field, statement in value.items():
                    _text(statement, name + '.' + field)
        if type(columns) is not list or not columns:
            raise ValueError('ordered nonempty columns required')
        names = set(); count = None
        for column in columns:
            if type(column) is not dict or set(column) != {'name', 'quantity', 'unit', 'values'}:
                raise ValueError('invalid column fields')
            _text(column['name'], 'column name')
            if column['name'] in names:
                raise ValueError('duplicate column name')
            names.add(column['name'])
            _unit(column['quantity'], column['unit'])
            values = column['values']
            if type(values) is not list or not values:
                raise ValueError('nonempty original values required')
            if count is None:
                count = len(values)
            if len(values) != count:
                raise ValueError('column lengths must agree; no interpolation')
            for value in values:
                _number(value, 'original value')
        if type(exclusions) is not list:
            raise ValueError('explicit exclusion list required')
        seen = set()
        for item in exclusions:
            if type(item) is not dict or set(item) != {'index', 'reason'}:
                raise ValueError('invalid exclusion fields')
            index = item['index']
            if type(index) is not int or not 0 <= index < count or index in seen:
                raise ValueError('invalid or duplicate exclusion index')
            seen.add(index); _text(item['reason'], 'exclusion reason')
        self._store(dict(schema_version=_SCHEMA, dataset_id=dataset_id,
            source=source, metadata=metadata, columns=columns, exclusions=exclusions))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('dataset_id', 'source', 'metadata', 'columns', 'exclusions'),
                        dict(schema_version=_SCHEMA))


class ObservableMapping(_Owned):
    """One explicit dimensional/coordinate transform with declared applicability review."""
    __slots__ = ()

    def __init__(self, dataset_hash, column, target_quantity, target_unit, sign,
                 offset, area_operation, rationale):
        _digest(dataset_hash, 'dataset_hash'); _text(column, 'column')
        _unit(target_quantity, target_unit); _text(rationale, 'rationale')
        if type(sign) is not int or sign not in (-1, 1):
            raise ValueError('explicit sign must be integer -1 or +1')
        _number(offset, 'offset in target units')
        if area_operation not in ('none', 'divide_by_area', 'multiply_by_area'):
            raise ValueError('unsupported area operation')
        self._store(dict(schema_version=_SCHEMA, dataset_hash=dataset_hash, column=column,
            target_quantity=target_quantity, target_unit=target_unit, sign=sign,
            offset=offset, area_operation=area_operation, rationale=rationale))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('dataset_hash', 'column', 'target_quantity', 'target_unit',
            'sign', 'offset', 'area_operation', 'rationale'), dict(schema_version=_SCHEMA))


def convert_interoperability_data(dataset, mapping):
    """Return an owned finite projection or explicit missing-condition outcome; no fitting."""
    if not isinstance(dataset, InteroperabilityDataset) or not isinstance(mapping, ObservableMapping):
        raise ValueError('owned dataset and mapping required')
    data = dataset.to_dict(); rule = mapping.to_dict()
    if rule['dataset_hash'] != dataset.contract_hash:
        raise ValueError('mapping belongs to a different original dataset')
    columns = [c for c in data['columns'] if c['name'] == rule['column']]
    if len(columns) != 1:
        raise ValueError('mapping column unavailable')
    column = columns[0]; original = column['quantity']; target = rule['target_quantity']
    operation = rule['area_operation']
    pairs = {'total_charge': 'charge_per_area', 'small_signal_capacitance':
             'small_signal_capacitance_per_area', 'current': 'current_per_area'}
    if operation == 'none':
        valid = original == target
    elif operation == 'divide_by_area':
        valid = pairs.get(original) == target
    else:
        valid = pairs.get(target) == original
    if not valid:
        raise ValueError('observable semantics cannot be interchanged by unit conversion')
    if rule['offset'] != 0 and original not in ('position', 'time', 'potential', 'gate_voltage'):
        raise ValueError('offset not defined for this observable')
    meta = data['metadata']; required = list(_REQUIRED)
    if 'capacitance' in original:
        required.append('frequency_conditions')
    if original in ('potential', 'signed_flat_band_shift', 'absolute_threshold_voltage', 'gate_voltage'):
        required.append('potential_reference')
    if original in ('optical_transition_energy', 'tunnelling_barrier_energy'):
        required.append('energy_reference')
    if original == 'optical_transition_energy':
        required.append('optical_conditions')
    if operation != 'none':
        required.append('area_m2')
    missing = [name for name in required if meta[name] is None]
    result = dict(schema_version=_SCHEMA, dataset_hash=dataset.contract_hash,
        mapping_hash=mapping.contract_hash, original_dataset=data, mapping=rule,
        status='unavailable' if missing else 'converted', missing_conditions=missing,
        experimental_qualification=False, external_agreement=False, values=None,
        included_indices=[], exclusions=data['exclusions'])
    if missing:
        return result
    factor = _UNITS[column['unit']][1] / _UNITS[rule['target_unit']][1]
    if operation == 'divide_by_area':
        factor /= meta['area_m2']
    elif operation == 'multiply_by_area':
        factor *= meta['area_m2']
    _number(factor, 'conversion factor')
    excluded = {item['index'] for item in data['exclusions']}
    indices = [i for i in range(len(column['values'])) if i not in excluded]
    values = [rule['sign'] * column['values'][i] * factor + rule['offset'] for i in indices]
    for value in values:
        _number(value, 'converted value')
    result.update(values=values, included_indices=indices)
    if not indices:
        result.update(status='unavailable', missing_conditions=['included_samples'])
    return result
