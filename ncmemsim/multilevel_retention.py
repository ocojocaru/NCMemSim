# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent dark retention probes of source-linked Q3 prepared levels."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass
import math as _math
from .multilevel_contracts import (ElectricalPulseStep as _Step, ElectricalPulseSequence as _Sequence,
    ElectricalSequenceExperiment as _Experiment, WeightReferenceMapping as _Reference,
    PulseSequenceEvidence as _Evidence, _Archive, _canonical, _load, _keys, _match, _number)
from .multilevel_analysis import MultilevelStudyResult as _Prepared, MultilevelStudyPlan as _StudyPlan
from .multilevel_execution import ElectricalSequenceResult as _Result, run_electrical_sequence as _run

__all__ = ['MultilevelRetentionPlan', 'MultilevelRetentionResult',
           'run_multilevel_retention', 'analyze_multilevel_retention']


@_dataclass(frozen=True)
class MultilevelRetentionPlan(_Archive):
    """Delays after each preparation, independently probed at one fixed dark bias."""
    prepared: _Prepared
    delays_s: tuple[float, ...]
    retention_voltage_V: float
    internal_dt_s: float
    evidence: _Evidence
    reference: _Reference | None = None

    def __post_init__(self):
        if type(self.prepared) is not _Prepared or type(self.evidence) is not _Evidence:
            raise ValueError('owned prepared study and retention evidence required')
        prepared = _Prepared.from_dict(self.prepared.to_dict())
        _schedule(self.delays_s, self.retention_voltage_V, self.internal_dt_s)
        object.__setattr__(self, 'delays_s', tuple(float(x) for x in self.delays_s))
        object.__setattr__(self, 'retention_voltage_V', float(self.retention_voltage_V))
        object.__setattr__(self, 'internal_dt_s', float(self.internal_dt_s))
        object.__setattr__(self, 'prepared', prepared)
        study = _StudyPlan.from_dict(prepared.to_dict()['plan'])
        first = study.levels[0].experiment
        reference = self.reference
        if reference is not None:
            if type(reference) is not _Reference:
                raise ValueError('typed fixed reference required')
            if reference.context_hash != first.context.context_hash or reference.readout_hash != first.sequence.readout.contract_hash:
                raise ValueError('reference belongs to a different physical context or read policy')
            if first.weight_reference is not None and reference.contract_hash != first.weight_reference.contract_hash:
                raise ValueError('cannot replace an existing fixed reference')
        # Build immutable expected probe requests once per validated plan. This
        # keeps full source validation while avoiding repeated reconstruction of
        # the entire prepared study for every level-delay comparison.
        source = prepared.to_dict()
        states = tuple(None if raw is None or raw['summary']['status'] != 'completed'
                       else _Result.from_dict(raw).final_state for raw in source['results'])
        requests = []
        for delay in self.delays_s:
            row = []
            for level, state in zip(study.levels, states, strict=True):
                if delay == 0 or state is None:
                    row.append(None)
                    continue
                sequence = _Sequence('independent dark retention',
                    (_Step('retention-hold', 'idle', self.retention_voltage_V, delay, self.internal_dt_s),),
                    level.experiment.sequence.readout, self.evidence)
                row.append(_Experiment.from_state('retention '+level.level_id, level.experiment.context,
                    sequence, state, level.experiment.weight_reference))
            requests.append(tuple(row))
        object.__setattr__(self, '_probe_requests', tuple(requests))

    def to_dict(self):
        return {'schema_version': 'multilevel-retention-plan-v1', 'prepared': self.prepared.to_dict(),
                'delays_s': list(self.delays_s), 'retention_voltage_V': self.retention_voltage_V,
                'internal_dt_s': self.internal_dt_s, 'evidence': self.evidence.to_dict(),
                'reference': None if self.reference is None else self.reference.to_dict(),
                'probe_policy': 'independent_copies_of_each_original_prepared_physical_state',
                'delay_origin': 'end_of_each_level_preparation', 'illumination': 'dark',
                'margin_policy': 'original_order_threshold_and_half_widths',
                'experimental_qualification': False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'prepared', 'delays_s', 'retention_voltage_V', 'internal_dt_s',
                    'evidence', 'reference', 'probe_policy', 'delay_origin', 'illumination',
                    'margin_policy', 'experimental_qualification'))
        if type(raw['delays_s']) is not list:
            raise ValueError('archived delay list required')
        obj = cls(_Prepared.from_dict(raw['prepared']), tuple(raw['delays_s']), raw['retention_voltage_V'],
                  raw['internal_dt_s'], _Evidence.from_dict(raw['evidence']),
                  None if raw['reference'] is None else _Reference.from_dict(raw['reference']))
        _match(raw, obj.to_dict())
        return obj


def _schedule(delays, voltage, dt):
    if type(delays) is not tuple or not delays:
        raise ValueError('nonempty immutable delay tuple required')
    values = tuple(_number(x, 'retention delay', nonnegative=True) for x in delays)
    if values[0] != 0 or any(b <= a for a, b in zip(values, values[1:])):
        raise ValueError('strictly increasing delays starting at zero required')
    _number(voltage, 'retention bias')
    dt = _number(dt, 'retention timestep', positive=True)
    for delay in values[1:]:
        _number(delay/dt, 'retention subdivision count', positive=True)
    if len(values) > 1 and dt > values[1]:
        raise ValueError('retention timestep must resolve the smallest positive delay')


def _probe_experiment(plan, index, delay):
    request = plan._probe_requests[plan.delays_s.index(delay)][index]
    if request is None:
        raise ValueError('no eligible positive-delay probe for this preparation')
    return request


def _separation(rows, study):
    pairs = []
    for index, (a, b) in enumerate(zip(rows, rows[1:])):
        margin, gap, reason = None, None, None
        if a['readout_V'] is None or b['readout_V'] is None:
            status, reason = 'not_assessable', 'missing_or_failed_observation'
        else:
            gap = b['readout_V']-a['readout_V']
            margin = (b['readout_V']-study.levels[index+1].readout_half_width_V)-(a['readout_V']+study.levels[index].readout_half_width_V)
            if not _math.isfinite(margin) or not _math.isfinite(gap):
                status, reason, margin, gap = 'not_assessable', 'nonrepresentable_margin', None, None
            else:
                status = 'passed' if margin > 0 and margin >= study.minimum_margin_V else 'failed'
        pairs.append({'lower_level_id': a['level_id'], 'upper_level_id': b['level_id'],
                      'signed_margin_V': margin, 'signed_readout_gap_V': gap, 'status': status, 'reason': reason})
    failed = sum(x['status'] == 'failed' for x in pairs)
    assessable = sum(x['status'] != 'not_assessable' for x in pairs)
    return {'status': 'failed' if failed else ('passed' if assessable == len(pairs) else 'not_assessable'),
            'adjacent_pairs': pairs, 'assessable_pair_count': assessable, 'requested_pair_count': len(pairs),
            'pair_assessment_fraction': assessable/len(pairs),
            'crossed_pair_count': sum(x['signed_readout_gap_V'] is not None and x['signed_readout_gap_V'] < 0 for x in pairs),
            'minimum_signed_margin_V': min((x['signed_margin_V'] for x in pairs if x['signed_margin_V'] is not None), default=None),
            'minimum_margin_scope': 'assessable_pairs_only'}


def _projection(raw):
    _keys(raw, ('schema_version', 'plan', 'plan_hash', 'probes', 'summary'))
    if raw['schema_version'] != 'multilevel-retention-result-v1':
        raise ValueError('unsupported multilevel retention schema')
    plan = MultilevelRetentionPlan.from_dict(raw['plan'])
    if raw['plan_hash'] != plan.contract_hash:
        raise ValueError('retention plan source hash mismatch')
    source = plan.prepared.to_dict()
    study = _StudyPlan.from_dict(source['plan'])
    if type(raw['probes']) is not list or len(raw['probes']) != len(plan.delays_s):
        raise ValueError('one ordered observation row per delay required')
    attempted = completed_probes = failed_probes = missing = observations = unavailable = 0
    delays = []
    for delay, records in zip(plan.delays_s, raw['probes'], strict=True):
        if type(records) is not list or len(records) != len(study.levels):
            raise ValueError('one result slot per original level required')
        rows = []
        for index, (level, record) in enumerate(zip(study.levels, records, strict=True)):
            baseline = source['results'][index]
            prep_status = 'missing' if baseline is None else baseline['summary']['status']
            value = elapsed = drift = weight = None
            failure = None
            if prep_status != 'completed':
                if record is not None:
                    raise ValueError('unavailable preparation cannot have a retention probe')
                status = 'unavailable_preparation'
                unavailable += 1
                failure = None if baseline is None else baseline['failure']
            elif delay == 0:
                if record is not None:
                    raise ValueError('zero delay reuses the original audited preparation read')
                status = 'completed'
                value = baseline['steps'][-1]['read']['delta_vfb_V']
                elapsed = 0.
            elif record is None:
                status = 'missing_probe'
                missing += 1
            else:
                attempted += 1
                result = _Result.from_dict(record)
                expected = _probe_experiment(plan, index, delay)
                if record['experiment_hash'] != expected.contract_hash:
                    raise ValueError('retention probe source, delay or original prepared state mismatch')
                result_summary = result.summary
                status = result_summary['status']
                failure = record['failure']
                # Failed probes retain actual elapsed physical time, never masquerade
                # as observations at their requested endpoint.
                elapsed = result_summary['elapsed_physical_time_s']
                if status == 'completed':
                    completed_probes += 1
                    value = record['steps'][-1]['read']['delta_vfb_V']
                else:
                    failed_probes += 1
            normalization = 'not_requested' if plan.reference is None else 'not_assessable'
            if value is not None:
                observations += 1
                drift = value-baseline['steps'][-1]['read']['delta_vfb_V']
                drift = drift if _math.isfinite(drift) else None
                if plan.reference is not None:
                    r = plan.reference
                    computed = (value-r.low_readout_V)/(r.high_readout_V-r.low_readout_V)
                    weight = computed if _math.isfinite(computed) else None
                    normalization = 'assessable' if weight is not None else 'not_assessable'
            rows.append({'level_id': level.level_id, 'preparation_status': prep_status, 'status': status,
                         'readout_V': value, 'signed_drift_V': drift, 'actual_elapsed_s': elapsed,
                         'weight_proxy': weight, 'normalization_status': normalization,
                         'out_of_reference': None if weight is None else not 0 <= weight <= 1,
                         'failure': failure})
        delays.append({'delay_s': delay, 'levels': rows, 'separation': _separation(rows, study)})
    requested = len(study.levels)*len(plan.delays_s)
    requested_probes = len(study.levels)*(len(plan.delays_s)-1)
    eligible = sum(x is not None and x['summary']['status'] == 'completed' for x in source['results'])*(len(plan.delays_s)-1)
    return {'requested_observation_count': requested, 'completed_observation_count': observations,
            'observation_coverage_fraction': observations/requested,
            'requested_probe_count': requested_probes, 'eligible_probe_count': eligible,
            'attempted_probe_count': attempted, 'completed_probe_count': completed_probes,
            'failed_probe_count': failed_probes, 'missing_probe_count': missing,
            'unavailable_preparation_observation_count': unavailable,
            'complete': observations == requested, 'delays': delays,
            'time_semantics': 'delay_after_each_own_preparation_not_common_absolute_device_age',
            'weights': 'fixed_reference_no_clipping' if plan.reference is not None else 'not_requested',
            'experimental_qualification': False, 'lifetime_claim': 'none'}


@_dataclass(frozen=True)
class MultilevelRetentionResult(_Archive):
    """All probes or missing slots, original preparations and static drift/separation."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _projection(raw)
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


def analyze_multilevel_retention(plan, probes):
    if type(plan) is not MultilevelRetentionPlan or type(probes) is not tuple:
        raise ValueError('typed retention plan and immutable probe rows required')
    if any(type(row) is not tuple or any(x is not None and type(x) is not _Result for x in row) for row in probes):
        raise ValueError('immutable rows of typed Q2 results or missing slots required')
    raw = {'schema_version': 'multilevel-retention-result-v1', 'plan': plan.to_dict(),
           'plan_hash': plan.contract_hash, 'probes': [[None if x is None else x.to_dict() for x in row] for row in probes],
           'summary': None}
    raw['summary'] = _projection(raw)
    return MultilevelRetentionResult.from_dict(raw)


def run_multilevel_retention(plan):
    if type(plan) is not MultilevelRetentionPlan:
        raise ValueError('owned multilevel retention plan required')
    plan = MultilevelRetentionPlan.from_dict(plan.to_dict())
    source = plan.prepared.to_dict()
    probes = tuple(tuple(None if delay == 0 or result is None or result['summary']['status'] != 'completed'
                         else _run(_probe_experiment(plan, index, delay))
                         for index, result in enumerate(source['results'])) for delay in plan.delays_s)
    return analyze_multilevel_retention(plan, probes)
