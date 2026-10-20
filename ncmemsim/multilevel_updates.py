# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Explicit pulse-index update metrics using a fixed readout-derived weight proxy."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass
import math as _math
from .multilevel_contracts import (ElectricalSequenceExperiment as _Experiment,
    WeightReferenceMapping as _Mapping, _Archive, _canonical, _keys, _load, _match, _number)
from .multilevel_execution import ElectricalSequenceResult as _Electrical
from .multilevel_optical import OpticalSequenceResult as _Optical, OpticalSequenceExperiment as _OpticalExperiment

__all__ = ['GradualUpdateAnalysis', 'PairedUpdateAnalysis',
           'analyze_gradual_updates', 'analyze_paired_updates']


def _source(raw):
    if type(raw) is not dict:
        raise ValueError('source result dictionary required')
    if raw.get('schema_version') == 'electrical-sequence-result-v1':
        result = _Electrical.from_dict(raw)
        experiment = _Experiment.from_dict(raw['experiment'])
        optical = None
    elif raw.get('schema_version') == 'optical-sequence-result-v1':
        result = _Optical.from_dict(raw)
        optical = _OpticalExperiment.from_dict(raw['experiment'])
        experiment = optical.electrical
    else:
        raise ValueError('supported Q2 or Q4 trajectory required')
    return result, experiment, optical


def _finite(value):
    return value if _math.isfinite(value) else None


def _update_projection(raw):
    _keys(raw, ('schema_version', 'source', 'source_hash', 'reference',
                'expected_direction', 'minimum_excursion_V', 'summary'))
    if raw['schema_version'] != 'gradual-update-analysis-v1':
        raise ValueError('unsupported gradual update analysis schema')
    result, exp, optical = _source(raw['source'])
    if raw['source_hash'] != result.contract_hash:
        raise ValueError('update trajectory source hash mismatch')
    reference = _Mapping.from_dict(raw['reference'])
    if reference.context_hash != exp.context.context_hash or reference.readout_hash != exp.sequence.readout.contract_hash:
        raise ValueError('weight reference belongs to another context/read policy')
    if exp.weight_reference is not None and exp.weight_reference.contract_hash != reference.contract_hash:
        raise ValueError('cannot replace the experiment fixed weight reference')
    direction = raw['expected_direction']
    if type(direction) is not str or direction not in ('increasing', 'decreasing'):
        raise ValueError('explicit increasing/decreasing signed readout direction required')
    minimum = _number(raw['minimum_excursion_V'], 'minimum excursion', positive=True)
    r = result.summary['read_delta_vfb_V']
    span = reference.high_readout_V-reference.low_readout_V
    weights = [_finite((x-reference.low_readout_V)/span) for x in r]
    updates = [_finite(b-a) for a, b in zip(r, r[1:])]
    weight_updates = [_finite(x/span) if x is not None else None for x in updates]
    n = len(updates)
    sign = 1 if direction == 'increasing' else -1
    excursion = _finite(r[-1]-r[0]) if r else None
    complete = result.summary['status'] == 'completed'
    reason = None
    if not complete:
        reason = 'incomplete_sequence'
    elif n < 2:
        reason = 'fewer_than_two_updates'
    elif any(x is None for x in weights+updates+weight_updates) or excursion is None:
        reason = 'nonrepresentable_normalization'
    elif sign*excursion <= 0:
        reason = 'wrong_or_zero_net_direction'
    elif abs(excursion) < minimum:
        reason = 'insufficient_dynamic_range'
    deviation = None
    if reason is None:
        # Endpoint-interpolated pulse-index deviation, normalized by branch excursion.
        # Difference before interpolation avoids cancellation from a large offset.
        deviation = _finite(max(abs((value-r[0])/excursion-k/n) for k, value in enumerate(r)))
        if deviation is None:
            reason = 'nonrepresentable_normalization'
    signatures = []
    for s in exp.sequence.steps:
        signature = [s.role, s.gate_voltage_V, s.duration_s, s.internal_dt_s]
        if optical is not None:
            signature.append(s.step_id in optical.illuminated_step_ids)
        signatures.append(signature)
    outside = [i for i, x in enumerate(weights) if x is not None and not 0 <= x <= 1]
    return {'status': 'assessable' if reason is None else 'not_assessable', 'reason': reason,
            'complete': complete, 'requested_update_count': len(exp.sequence.steps),
            'requested_pulse_count': sum(s.role != 'idle' for s in exp.sequence.steps),
            'completed_pulse_count': sum(s.role != 'idle' for s in exp.sequence.steps[:result.summary['completed_step_count']]),
            'observed_pulse_update_count': sum(s.role != 'idle' for s in exp.sequence.steps[:n]),
            'requested_idle_segment_count': sum(s.role == 'idle' for s in exp.sequence.steps),
            'observed_update_count': n, 'update_coverage_fraction': n/len(exp.sequence.steps),
            'read_delta_vfb_V': r, 'signed_updates_V': updates,
            'read_times_s': ([raw['source']['initial_read']['state']['time_s']]
                + [s['read']['state']['time_s'] for s in raw['source']['steps'] if s['read'] is not None])
                if raw['source']['initial_read'] is not None else [],
            'weight_proxy': weights, 'signed_weight_updates': weight_updates,
            'out_of_reference_read_indices': outside, 'reference_span_V': span,
            'net_excursion_V': excursion,
            'direction_reversal_count': sum(x is not None and sign*x < 0 for x in updates),
            'exact_zero_update_count': sum(x == 0 for x in updates),
            'all_steps_identical': all(s == signatures[0] for s in signatures),
            'linearity_deviation': deviation,
            'linearity_definition': 'max_abs((R_k-R_0)/(R_N-R_0)-k/N)',
            'linearity_normalizer': 'absolute_endpoint_excursion_not_reference_span',
            'weight_definition': '(R-R_low)/(R_high-R_low)_no_clipping',
            'meaning': 'readout_derived_proxy_not_conductance',
            'experimental_qualification': False}


@_dataclass(frozen=True)
class GradualUpdateAnalysis(_Archive):
    """Full source and explicit definitions, with undefined metrics retained as null."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _update_projection(raw)
        _match(raw['summary'], summary)
        object.__setattr__(self, 'record_json', _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()['summary']

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def analyze_gradual_updates(result, reference, *, expected_direction, minimum_excursion_V):
    """Analyze every physical segment boundary; no sorting, clipping or dropped idle steps."""
    if type(result) not in (_Electrical, _Optical) or type(reference) is not _Mapping:
        raise ValueError('typed sequence result and fixed reference required')
    raw = {'schema_version': 'gradual-update-analysis-v1', 'source': result.to_dict(),
           'source_hash': result.contract_hash, 'reference': reference.to_dict(),
           'expected_direction': expected_direction, 'minimum_excursion_V': minimum_excursion_V, 'summary': None}
    raw['summary'] = _update_projection(raw)
    return GradualUpdateAnalysis.from_dict(raw)


def _pair_projection(raw):
    _keys(raw, ('schema_version', 'first', 'second', 'summary'))
    if raw['schema_version'] != 'paired-update-analysis-v1':
        raise ValueError('unsupported paired update schema')
    first = GradualUpdateAnalysis.from_dict(raw['first'])
    second = GradualUpdateAnalysis.from_dict(raw['second'])
    a, b = first.summary, second.summary
    ra, rb = raw['first'], raw['second']
    if ra['reference'] != rb['reference'] or ra['expected_direction'] == rb['expected_direction']:
        raise ValueError('same fixed reference and opposite declared directions required')
    _, ea, oa = _source(ra['source'])
    _, eb, ob = _source(rb['source'])
    if ea.context.context_hash != eb.context.context_hash or ea.sequence.readout.contract_hash != eb.sequence.readout.contract_hash:
        raise ValueError('paired updates require the same physical context and read policy')
    # Optical branch comparison also fixes the spectrum, path, capture and area.
    if (oa is None) != (ob is None):
        raise ValueError('paired branches must share the same electrical/optical modality')
    if oa is not None:
        for key in ('spectral_context', 'capture_efficiency', 'transition_weights', 'illuminated_area_m2'):
            _match(oa.to_dict()[key], ob.to_dict()[key])
    sa, sb = ea.sequence.steps, eb.sequence.steps
    aligned = len(sa) == len(sb) and all(x.duration_s == y.duration_s and x.internal_dt_s == y.internal_dt_s
                                        for x, y in zip(sa, sb))
    reason = None
    if not aligned:
        reason = 'unmatched_segment_count_duration_or_timestep'
    elif a['status'] != 'assessable' or b['status'] != 'assessable':
        reason = 'unassessable_branch'
    elif a['direction_reversal_count'] or b['direction_reversal_count']:
        reason = 'branch_direction_reversal'
    magnitudes_a, magnitudes_b = a['signed_weight_updates'], b['signed_weight_updates']
    score = None
    if reason is None:
        # Divide before summation to avoid overflow for large finite updates.
        scale = max(abs(x) for x in magnitudes_a+magnitudes_b)
        if scale == 0:
            reason = 'zero_update_normalizer'
        else:
            aa, bb = [abs(x)/scale for x in magnitudes_a], [abs(x)/scale for x in magnitudes_b]
            score = _math.fsum(abs(x-y) for x, y in zip(aa, bb, strict=True))/_math.fsum(aa+bb)
    return {'status': 'assessable' if reason is None else 'not_assessable', 'reason': reason,
            'asymmetry': score,
            'definition': 'sum(abs(abs(delta_w_first_k)-abs(delta_w_second_k)))/sum(abs(delta_w_first_k)+abs(delta_w_second_k))',
            'alignment': 'same_segment_index_no_reverse_or_state_matching',
            'matched_update_count': min(a['observed_update_count'], b['observed_update_count']) if aligned else 0,
            'first_update_coverage_fraction': a['update_coverage_fraction'],
            'second_update_coverage_fraction': b['update_coverage_fraction'],
            'experimental_qualification': False}


@_dataclass(frozen=True)
class PairedUpdateAnalysis(_Archive):
    """Pulse-index paired magnitude asymmetry; not state-matched hysteresis fitting."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _pair_projection(raw)
        _match(raw['summary'], summary)
        object.__setattr__(self, 'record_json', _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()['summary']

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def analyze_paired_updates(first, second):
    if type(first) is not GradualUpdateAnalysis or type(second) is not GradualUpdateAnalysis:
        raise ValueError('typed gradual-update branches required')
    raw = {'schema_version': 'paired-update-analysis-v1', 'first': first.to_dict(),
           'second': second.to_dict(), 'summary': None}
    raw['summary'] = _pair_projection(raw)
    return PairedUpdateAnalysis.from_dict(raw)
