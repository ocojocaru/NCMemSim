# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Manifest-bound multilevel preparation/retention for supported FG fractions."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass, replace as _replace
from .multilevel_contracts import (_Archive, _canonical, _load, _keys, _match, _text,
                                  PulseSequenceEvidence as _Evidence)
from .multilevel_analysis import MultilevelStudyPlan as _Study, run_multilevel_study as _prepare
from .multilevel_retention import (MultilevelRetentionPlan as _RetentionPlan,
    MultilevelRetentionResult as _RetentionResult, run_multilevel_retention as _retain, _schedule)
from .ensemble.sampling import SampleManifest as _Manifest
from .ensemble.realization import apply_sample_to_context as _apply
from .temperature_context import _device_payload

__all__ = ['MultilevelEnsemblePlan', 'MultilevelEnsembleResult', 'run_multilevel_ensemble']


@_dataclass(frozen=True)
class MultilevelEnsemblePlan(_Archive):
    """Fixed waveforms/read/margins; only FG active/NC volume fractions vary.

    Reference-bound normalized weights are excluded from this first adapter:
    binding a nominal-context mapping to a changed device would change its meaning.
    Physical readout, drift and separation in volts remain directly comparable.
    """
    study: _Study
    manifest: _Manifest
    delays_s: tuple[float, ...]
    retention_voltage_V: float
    internal_dt_s: float
    evidence: _Evidence

    def __post_init__(self):
        if type(self.study) is not _Study or type(self.manifest) is not _Manifest or type(self.evidence) is not _Evidence:
            raise ValueError('owned study, sample manifest and evidence required')
        study = _Study.from_dict(self.study.to_dict())
        manifest = _Manifest.from_dict(self.manifest.to_dict())
        _schedule(self.delays_s, self.retention_voltage_V, self.internal_dt_s)
        if any(x.experiment.weight_reference is not None for x in study.levels):
            raise ValueError('ensemble adapter does not rebind nominal-context weight references')
        spec = manifest.sampling_spec.ensemble_spec
        device = study.levels[0].experiment.context.device
        spec.require_matching_device(device)
        if spec.base_operating_hash is not None:
            raise ValueError('operating variation is outside the fixed-waveform adapter')
        names = {x.name for x in device.floating_gates()}
        for variable in spec.variables:
            path = variable.binding.path
            if variable.binding.scope.value != 'device' or len(path) != 3 or path[0] != 'layers' or path[1] not in names or path[2] not in ('electrically_active_fraction', 'nc_volume_fraction'):
                raise ValueError('only existing FG electrically_active_fraction/nc_volume_fraction bindings are supported')
        object.__setattr__(self, 'study', study)
        object.__setattr__(self, 'manifest', manifest)
        object.__setattr__(self, 'delays_s', tuple(float(x) for x in self.delays_s))
        object.__setattr__(self, 'retention_voltage_V', float(self.retention_voltage_V))
        object.__setattr__(self, 'internal_dt_s', float(self.internal_dt_s))

    def to_dict(self):
        return {'schema_version': 'multilevel-ensemble-plan-v1', 'study': self.study.to_dict(),
                'manifest': self.manifest.to_dict(), 'delays_s': list(self.delays_s),
                'retention_voltage_V': self.retention_voltage_V, 'internal_dt_s': self.internal_dt_s,
                'evidence': self.evidence.to_dict(), 'sample_policy': 'serial_isolated_manifest_order',
                'initial_state_policy': 'same_declared_probability_coordinates_preserved_grid',
                'reference_policy': 'fixed_read_voltage_order_margins_no_weight_rebinding',
                'experimental_qualification': False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'study', 'manifest', 'delays_s', 'retention_voltage_V', 'internal_dt_s',
                    'evidence', 'sample_policy', 'initial_state_policy', 'reference_policy', 'experimental_qualification'))
        if type(raw['delays_s']) is not list:
            raise ValueError('archived retention delay list required')
        obj = cls(_Study.from_dict(raw['study']), _Manifest.from_dict(raw['manifest']), tuple(raw['delays_s']),
                  raw['retention_voltage_V'], raw['internal_dt_s'], _Evidence.from_dict(raw['evidence']))
        _match(raw, obj.to_dict())
        return obj


def _realized_study(plan, sample):
    original = plan.study.levels[0].experiment.context
    realized = _apply(plan.manifest.sampling_spec, sample, original.device)
    # An exact zero-variation sample preserves the original context identity.
    if realized.device.to_dict() == original.device.to_dict():
        context = original
    else:
        nominal = _replace(original.context, nominal_device_json=_canonical(_device_payload(realized.device)))
        context = nominal.resolve(temperature_K=original.temperature_K)
    levels = tuple(_replace(level, experiment=_replace(level.experiment, context=context)) for level in plan.study.levels)
    return _replace(plan.study, levels=levels)


def _projection(raw):
    _keys(raw, ('schema_version', 'plan', 'plan_hash', 'points', 'summary'))
    if raw['schema_version'] != 'multilevel-ensemble-result-v1':
        raise ValueError('unsupported multilevel ensemble schema')
    plan = MultilevelEnsemblePlan.from_dict(raw['plan'])
    if raw['plan_hash'] != plan.contract_hash:
        raise ValueError('ensemble plan identity mismatch')
    if type(raw['points']) is not list or len(raw['points']) != len(plan.manifest.samples):
        raise ValueError('every manifest sample requires an ordered result slot')
    summaries = []
    counts = {key: 0 for key in ('attempted', 'completed', 'partial', 'failed', 'missing')}
    for sample, point in zip(plan.manifest.samples, raw['points'], strict=True):
        if point is None:
            counts['missing'] += 1
            summaries.append(None)
            continue
        counts['attempted'] += 1
        _keys(point, ('sample_id', 'sample_index', 'status', 'realized_study', 'result', 'failure'))
        if type(point['sample_index']) is not int or point['sample_id'] != sample.sample_id or point['sample_index'] != sample.sample_index:
            raise ValueError('ensemble sample identity or order mismatch')
        expected, static_error = None, None
        try:
            expected = _realized_study(plan, sample)
        except Exception as exc:
            static_error = exc
        if point['result'] is None:
            if point['status'] != 'failed' or point['failure'] is None:
                raise ValueError('missing sample output requires explicit execution failure')
            failure = point['failure']
            _keys(failure, ('stage', 'exception_type', 'message'))
            for key in failure:
                _text(failure[key], key)
            if failure['stage'] not in ('realization', 'workflow'):
                raise ValueError('unsupported ensemble failure stage')
            if failure['stage'] == 'realization':
                if point['realized_study'] is not None or static_error is None:
                    raise ValueError('inconsistent failed realization evidence')
                expected_error = type(static_error).__module__+'.'+type(static_error).__qualname__
                _match(failure['exception_type'], expected_error)
                _match(failure['message'], str(static_error).strip() or type(static_error).__name__)
            else:
                if static_error is not None or expected is None:
                    raise ValueError('workflow failure requires a valid realization')
                _match(point['realized_study'], expected.to_dict())
            counts['failed'] += 1
            summaries.append(None)
        else:
            if static_error is not None or expected is None or point['failure'] is not None:
                raise ValueError('successful source requires a valid exact realization')
            _match(point['realized_study'], expected.to_dict())
            result = _RetentionResult.from_dict(point['result'])
            retention_plan = result.to_dict()['plan']
            _match(retention_plan['prepared']['plan'], expected.to_dict())
            _match(retention_plan['delays_s'], list(plan.delays_s))
            _match(retention_plan['retention_voltage_V'], plan.retention_voltage_V)
            _match(retention_plan['internal_dt_s'], plan.internal_dt_s)
            _match(retention_plan['evidence'], plan.evidence.to_dict())
            if retention_plan['reference'] is not None:
                raise ValueError('unexpected ensemble reference normalization')
            result_summary = result.summary
            status = 'completed' if result_summary['complete'] else 'partial'
            if point['status'] != status:
                raise ValueError('sample completion status mismatch')
            counts[status] += 1
            summaries.append(result_summary)
    n = len(plan.manifest.samples)
    delays = []
    for index, delay in enumerate(plan.delays_s):
        rows = []
        for sample, summary in zip(plan.manifest.samples, summaries, strict=True):
            separation = None if summary is None else summary['delays'][index]['separation']
            full = separation is not None and separation['pair_assessment_fraction'] == 1
            rows.append({'sample_id': sample.sample_id,
                'fully_assessed': full, 'separation_status': 'not_assessable' if separation is None else separation['status'],
                'minimum_signed_margin_V': None if separation is None else separation['minimum_signed_margin_V']})
        fully = sum(x['fully_assessed'] for x in rows)
        passed = sum(x['separation_status'] == 'passed' for x in rows)
        known_failed = sum(x['separation_status'] == 'failed' for x in rows)
        delays.append({'delay_s': delay, 'samples': rows, 'requested_sample_count': n,
            'fully_assessed_sample_count': fully, 'passed_sample_count': passed,
            'known_failed_sample_count': known_failed, 'not_fully_assessed_sample_count': n-fully,
            'full_assessment_fraction_of_requested': fully/n,
            'passed_fraction_of_requested': passed/n,
            'passed_fraction_of_fully_assessed': None if not fully else passed/fully})
    return {'requested_sample_count': n, **{key+'_sample_count': value for key, value in counts.items()},
            'complete': counts['completed'] == n, 'delays': delays,
            'denominator_policy': 'requested_is_full_manifest_fully_assessed_requires_every_adjacent_pair',
            'interpretation': 'conditional_between_device_variation_not_cycle_noise_or_manufacturing_yield',
            'experimental_qualification': False}


@_dataclass(frozen=True)
class MultilevelEnsembleResult(_Archive):
    """Full manifest and source-linked realizations, with all failures in denominators."""
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


def run_multilevel_ensemble(plan):
    if type(plan) is not MultilevelEnsemblePlan:
        raise ValueError('owned multilevel ensemble plan required')
    plan = MultilevelEnsemblePlan.from_dict(plan.to_dict())
    points = []
    for sample in plan.manifest.samples:
        stage, realized = 'realization', None
        point = {'sample_id': sample.sample_id, 'sample_index': sample.sample_index,
                 'status': None, 'realized_study': None, 'result': None, 'failure': None}
        try:
            realized = _realized_study(plan, sample)
            point['realized_study'] = realized.to_dict()
            stage = 'workflow'
            prepared = _prepare(realized)
            result = _retain(_RetentionPlan(prepared, plan.delays_s, plan.retention_voltage_V,
                                           plan.internal_dt_s, plan.evidence))
            point['result'] = result.to_dict()
            point['status'] = 'completed' if result.summary['complete'] else 'partial'
        except Exception as exc:
            point['status'] = 'failed'
            point['failure'] = {'stage': stage, 'exception_type': type(exc).__module__+'.'+type(exc).__qualname__,
                                'message': str(exc).strip() or type(exc).__name__}
        points.append(point)
    raw = {'schema_version': 'multilevel-ensemble-result-v1', 'plan': plan.to_dict(),
           'plan_hash': plan.contract_hash, 'points': points, 'summary': None}
    raw['summary'] = _projection(raw)
    return MultilevelEnsembleResult.from_dict(raw)
