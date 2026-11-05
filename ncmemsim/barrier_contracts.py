# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned electron barrier declarations; no WKB evaluation or simulator attachment."""
from __future__ import annotations

import math as _math
from .constants import ELEMENTARY_CHARGE_C as _Q
from .performance_contracts import _Owned, _restore, _text, _choice

__all__ = ['BarrierProvenance', 'BarrierSegment', 'BarrierProfile',
           'BarrierEvaluationSpec', 'barrier_energy_eV_to_J']

_SCHEMA = 'ncmemsim-explicit-barrier-v1'


def _real(value, name, positive=False, nonnegative=False):
    if type(value) not in (int, float):
        raise ValueError(name + ' requires a finite real number, excluding bool')
    try:
        finite = _math.isfinite(float(value))
    except OverflowError:
        finite = False
    if not finite or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(name + ' outside the declared finite domain')
    return value


def _owned(value, cls):
    return cls.from_dict(value.to_dict() if isinstance(value, cls) else value).to_dict()


def barrier_energy_eV_to_J(energy_eV):
    """Explicit signed eV-to-J conversion; reject overflow and nonzero underflow."""
    _real(energy_eV, 'energy_eV')
    result = energy_eV * _Q
    if not _math.isfinite(result) or (energy_eV != 0 and result == 0):
        raise ValueError('energy conversion outside finite representable range')
    return result


class BarrierProvenance(_Owned):
    """Caller-declared provenance, never automatic experimental admission."""
    __slots__ = ()

    def __init__(self, parameter_status, source, evidence, applicability, limitations):
        _choice(parameter_status, ('assumed', 'reported', 'fitted'), 'parameter_status')
        for name, value in [('source', source), ('evidence', evidence),
                            ('applicability', applicability), ('limitations', limitations)]:
            _text(value, name)
        self._store(dict(schema_version=_SCHEMA, parameter_status=parameter_status,
            source=source, evidence=evidence, applicability=applicability,
            limitations=limitations, experimental_admission=False))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('parameter_status', 'source', 'evidence',
            'applicability', 'limitations'),
            dict(schema_version=_SCHEMA, experimental_admission=False))


class BarrierSegment(_Owned):
    """Linear electron potential energy U (J), before subtracting incident energy."""
    __slots__ = ()

    def __init__(self, segment_id, length_m, start_potential_energy_J,
                 end_potential_energy_J, effective_mass_m0, provenance):
        _text(segment_id, 'segment_id')
        _real(length_m, 'length_m', positive=True)
        _real(start_potential_energy_J, 'start_potential_energy_J')
        _real(end_potential_energy_J, 'end_potential_energy_J')
        _real(effective_mass_m0, 'effective_mass_m0', positive=True)
        self._store(dict(schema_version=_SCHEMA, segment_id=segment_id,
            length_m=length_m, start_potential_energy_J=start_potential_energy_J,
            end_potential_energy_J=end_potential_energy_J,
            effective_mass_m0=effective_mass_m0,
            provenance=_owned(provenance, BarrierProvenance),
            energy_semantics='electron_potential_energy_before_incident_subtraction',
            mass_semantics='constant_within_segment_ratio_to_free_electron_mass'))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('segment_id', 'length_m', 'start_potential_energy_J',
            'end_potential_energy_J', 'effective_mass_m0', 'provenance'),
            dict(schema_version=_SCHEMA,
                energy_semantics='electron_potential_energy_before_incident_subtraction',
                mass_semantics='constant_within_segment_ratio_to_free_electron_mass'))


class BarrierProfile(_Owned):
    """Ordered traversal, one global energy reference, explicit abrupt interfaces."""
    __slots__ = ()

    def __init__(self, profile_id, segments, incident_energy_J, energy_reference,
                 axis_origin, positive_axis_direction, traversal_direction,
                 source_contact, destination_contact, applicability, limitations):
        for name, value in [('profile_id', profile_id), ('energy_reference', energy_reference),
            ('axis_origin', axis_origin), ('positive_axis_direction', positive_axis_direction),
            ('source_contact', source_contact), ('destination_contact', destination_contact),
            ('applicability', applicability), ('limitations', limitations)]:
            _text(value, name)
        if source_contact == destination_contact:
            raise ValueError('source and destination contacts must differ')
        _choice(traversal_direction, ('along_positive_axis', 'against_positive_axis'),
                'traversal_direction')
        _real(incident_energy_J, 'incident_energy_J')
        if type(segments) not in (list, tuple) or not segments:
            raise ValueError('nonempty ordered segments required')
        rows = [_owned(row, BarrierSegment) for row in segments]
        ids = [row['segment_id'] for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('segment identifiers must be unique')
        try:
            _real(_math.fsum(row['length_m'] for row in rows), 'total_length_m', positive=True)
        except OverflowError as exc:
            raise ValueError('total length outside finite range') from exc
        for row in rows:
            for key in ('start_potential_energy_J', 'end_potential_energy_J'):
                _real(row[key] - incident_energy_J, 'potential minus incident energy')
        self._store(dict(schema_version=_SCHEMA, profile_id=profile_id, segments=rows,
            incident_energy_J=incident_energy_J, energy_reference=energy_reference,
            axis_origin=axis_origin, positive_axis_direction=positive_axis_direction,
            traversal_direction=traversal_direction, source_contact=source_contact,
            destination_contact=destination_contact, applicability=applicability,
            limitations=limitations, carrier='electron',
            interface_policy='independent_one_sided_endpoint_values',
            incident_energy_policy='subtract_once_from_each_potential_endpoint',
            physical_matching='not_included'))

    @property
    def total_length_m(self):
        return _math.fsum(row['length_m'] for row in self.to_dict()['segments'])

    def reversed(self):
        """Reverse the same energy landscape at the same E; not reverse-bias simulation."""
        data = self.to_dict()
        rows = []
        for raw in reversed(data['segments']):
            row = dict(raw)
            row['start_potential_energy_J'], row['end_potential_energy_J'] = (
                row['end_potential_energy_J'], row['start_potential_energy_J'])
            rows.append(row)
        data['segments'] = rows
        data['source_contact'], data['destination_contact'] = (
            data['destination_contact'], data['source_contact'])
        data['traversal_direction'] = ('against_positive_axis'
            if data['traversal_direction'] == 'along_positive_axis' else 'along_positive_axis')
        return type(self).from_dict(data)

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('profile_id', 'segments', 'incident_energy_J',
            'energy_reference', 'axis_origin', 'positive_axis_direction',
            'traversal_direction', 'source_contact', 'destination_contact',
            'applicability', 'limitations'), dict(schema_version=_SCHEMA, carrier='electron',
            interface_policy='independent_one_sided_endpoint_values',
            incident_energy_policy='subtract_once_from_each_potential_endpoint',
            physical_matching='not_included'))


class BarrierEvaluationSpec(_Owned):
    """Inert evaluation request and reference-comparison tolerances; no result values."""
    __slots__ = ()

    def __init__(self, profile, exponent_atol, exponent_rtol, reference_scope):
        _real(exponent_atol, 'exponent_atol', nonnegative=True)
        _real(exponent_rtol, 'exponent_rtol', nonnegative=True)
        if exponent_atol == 0 and exponent_rtol == 0:
            raise ValueError('at least one numerical comparison tolerance must be positive')
        _text(reference_scope, 'reference_scope')
        self._store(dict(schema_version=_SCHEMA, profile=_owned(profile, BarrierProfile),
            exponent_atol=exponent_atol, exponent_rtol=exponent_rtol,
            reference_scope=reference_scope, approximation='positive_segment_action_only',
            exponent_convention='twice_forbidden_action_over_hbar',
            underflow_policy='zero_transmission_retain_finite_exponent_and_log',
            overflow_policy='fail_not_clip', interface_matching=False,
            simulator_attachment=False, evaluated=False))

    @classmethod
    def from_dict(cls, raw):
        return _restore(cls, raw, ('profile', 'exponent_atol', 'exponent_rtol', 'reference_scope'),
            dict(schema_version=_SCHEMA, approximation='positive_segment_action_only',
                exponent_convention='twice_forbidden_action_over_hbar',
                underflow_policy='zero_transmission_retain_finite_exponent_and_log',
                overflow_policy='fail_not_clip', interface_matching=False,
                simulator_attachment=False, evaluated=False))
