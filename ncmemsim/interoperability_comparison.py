# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Source-bound comparisons on declared common grids; no external qualification."""
from __future__ import annotations
from fractions import Fraction as _Fraction
from .performance_contracts import _Owned, _restore, _text
from .interoperability import (InteroperabilityDataset as _Dataset,
    ObservableMapping as _Mapping, convert_interoperability_data as _convert,
    _number)

__all__ = ['InteroperabilityComparison', 'compare_interoperability_data']
_SCHEMA = 'ncmemsim-interoperability-comparison-v1'
_KEYS = ('reference_axis', 'reference_values', 'candidate_axis', 'candidate_values')
_AXIS = ('position', 'time', 'gate_voltage')
_BASE_CONDITIONS = ('geometry_materials', 'contacts_bias', 'temperature_K', 'history',
                    'initial_state', 'time_conditions', 'coordinates',
                    'electron_charge_sign', 'applicability')


def _dataset(value):
    return _Dataset.from_dict(value.to_dict() if isinstance(value, _Dataset) else value)


def _mapping(value):
    return _Mapping.from_dict(value.to_dict() if isinstance(value, _Mapping) else value)


class InteroperabilityComparison(_Owned):
    """Own both datasets, four mappings, common conditions and predeclared tolerances."""
    __slots__ = ()

    def __init__(self, reference, candidate, mappings, target_metadata,
                 applicability_review, axis_atol, axis_rtol, atol, rtol):
        reference = _dataset(reference); candidate = _dataset(candidate)
        if type(mappings) is not dict or set(mappings) != set(_KEYS):
            raise ValueError('exactly four named axis/observable mappings required')
        maps = {key: _mapping(value).to_dict() for key, value in mappings.items()}
        for label, dataset in [('reference', reference), ('candidate', candidate)]:
            data = dataset.to_dict()
            for key in (label + '_axis', label + '_values'):
                rule = maps[key]
                if rule['dataset_hash'] != dataset.contract_hash:
                    raise ValueError('mapping belongs to another dataset')
                if rule['column'] not in [c['name'] for c in data['columns']]:
                    raise ValueError('mapped source column not found')
            if maps[label+'_axis']['column'] == maps[label+'_values']['column']:
                raise ValueError('axis and observable must be distinct columns')
        for suffix in ('axis', 'values'):
            left, right = maps['reference_'+suffix], maps['candidate_'+suffix]
            if (left['target_quantity'], left['target_unit']) != (right['target_quantity'], right['target_unit']):
                raise ValueError('both sides must map explicitly to the same quantity and unit')
        if maps['reference_axis']['target_quantity'] not in _AXIS:
            raise ValueError('comparison axis must be position, time or gate voltage')
        # Reuse the R4 metadata schema check, without treating common conditions as source data.
        check = reference.to_dict(); check['metadata'] = target_metadata
        _Dataset.from_dict(check)
        if type(applicability_review) is not dict or set(applicability_review) != {'reference', 'candidate'}:
            raise ValueError('explicit applicability review for both sources required')
        for label in ('reference', 'candidate'):
            _text(applicability_review[label], label + ' applicability review')
        tolerances = dict(axis_atol=axis_atol, axis_rtol=axis_rtol, atol=atol, rtol=rtol)
        for name, value in tolerances.items():
            _number(value, name)
            if value < 0:
                raise ValueError('tolerances must be nonnegative')
        self._store(dict(schema_version=_SCHEMA, reference=reference.to_dict(),
            candidate=candidate.to_dict(), mappings=maps, target_metadata=target_metadata,
            applicability_review=applicability_review, **tolerances))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('reference', 'candidate', 'mappings', 'target_metadata',
            'applicability_review', 'axis_atol', 'axis_rtol', 'atol', 'rtol'),
            dict(schema_version=_SCHEMA))


def _ratio(number):
    return dict(numerator=str(number.numerator), denominator=str(number.denominator))


def _point(reference, candidate, atol, rtol):
    delta = _Fraction(candidate) - _Fraction(reference)
    limit = _Fraction(atol) + _Fraction(rtol) * abs(_Fraction(reference))
    return dict(reference=reference, candidate=candidate, residual=_ratio(delta),
                absolute_residual=_ratio(abs(delta)), tolerance=_ratio(limit),
                within_tolerance=abs(delta) <= limit)


def _target_missing(metadata, quantities):
    required = list(_BASE_CONDITIONS)
    for quantity in quantities:
        if 'capacitance' in quantity:
            required.append('frequency_conditions')
        if quantity in ('potential', 'gate_voltage', 'signed_flat_band_shift', 'absolute_threshold_voltage'):
            required.append('potential_reference')
        if quantity in ('optical_transition_energy', 'tunnelling_barrier_energy'):
            required.append('energy_reference')
        if quantity == 'optical_transition_energy':
            required.append('optical_conditions')
    return [key for key in dict.fromkeys(required) if metadata[key] is None]


def compare_interoperability_data(comparison):
    """Retain converted sources, coverage and exact tolerance decisions; never fit or align."""
    if not isinstance(comparison, InteroperabilityComparison):
        raise ValueError('owned comparison declaration required')
    data = comparison.to_dict(); maps = data['mappings']
    result = dict(schema_version=_SCHEMA, comparison_hash=comparison.contract_hash,
        declaration=data, status='unavailable', reasons=[], conversions={}, coverage={},
        scope='retained_rows_only', full_coverage=False, assessed_fraction=0.,
        axis_comparison=[], value_comparison=[], assessed_count=0, matched_count=0,
        mismatched_count=0, max_absolute_residual=None,
        experimental_qualification=False, external_agreement=False)
    for key in _KEYS:
        label = key.split('_')[0]
        # An invalid transformation is a malformed declaration, not an unavailable dataset.
        projection = _convert(_Dataset.from_dict(data[label]), _Mapping.from_dict(maps[key]))
        result['conversions'][key] = projection
        if projection['status'] != 'converted':
            result['reasons'].append(dict(stage='source_conditions', source=key,
                missing_conditions=projection['missing_conditions']))
    for label in ('reference', 'candidate'):
        dataset = data[label]; total = len(dataset['columns'][0]['values'])
        excluded = len(dataset['exclusions'])
        result['coverage'][label] = dict(original_count=total, excluded_count=excluded,
            retained_count=total-excluded, retained_fraction=(total-excluded)/total,
            exclusions=dataset['exclusions'])
    result['full_coverage'] = all(c['excluded_count'] == 0 for c in result['coverage'].values())
    missing = _target_missing(data['target_metadata'],
                             [maps['reference_'+s]['target_quantity'] for s in ('axis', 'values')])
    if missing:
        result['reasons'].append(dict(stage='target_conditions', missing_conditions=missing))
    if result['reasons']:
        return result
    converted = result['conversions']
    reference_indices = converted['reference_axis']['included_indices']
    candidate_indices = converted['candidate_axis']['included_indices']
    # Different row masks or lengths are never silently intersected or paired by nearest point.
    if (result['coverage']['reference']['original_count'] != result['coverage']['candidate']['original_count']
            or reference_indices != candidate_indices):
        result['reasons'].append(dict(stage='alignment', reason='different original counts or exclusion masks'))
        return result
    axes = zip(converted['reference_axis']['values'], converted['candidate_axis']['values'])
    result['axis_comparison'] = [dict(index=i, **_point(a, b, data['axis_atol'], data['axis_rtol']))
                                for i, (a, b) in zip(reference_indices, axes)]
    if not all(row['within_tolerance'] for row in result['axis_comparison']):
        result['reasons'].append(dict(stage='alignment', reason='converted grids outside axis tolerances'))
        return result
    values = zip(converted['reference_values']['values'], converted['candidate_values']['values'])
    rows = [dict(index=i, **_point(a, b, data['atol'], data['rtol']))
            for i, (a, b) in zip(reference_indices, values)]
    matched = sum(row['within_tolerance'] for row in rows)
    maximum = max(abs(_Fraction(row['candidate'])-_Fraction(row['reference'])) for row in rows)
    result.update(status='matched' if matched == len(rows) else 'mismatched',
        value_comparison=rows, assessed_count=len(rows), matched_count=matched,
        assessed_fraction=len(rows)/result['coverage']['reference']['original_count'],
        mismatched_count=len(rows)-matched, max_absolute_residual=_ratio(maximum))
    return result
