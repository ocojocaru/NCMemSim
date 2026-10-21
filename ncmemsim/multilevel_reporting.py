# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Strict source-linked multilevel reports and deterministic local bundles."""
from __future__ import annotations
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path
import csv as _csv
import io as _io
import html as _html
import hashlib as _hashlib
import json as _json
from contextlib import contextmanager as _contextmanager
from contextvars import ContextVar as _ContextVar
import sys as _sys
from .multilevel_contracts import PulseSequenceEvidence as _Evidence, _Archive, _canonical, _load, _keys, _match, _text
from .multilevel_execution import ElectricalSequenceResult as _Electrical
from .multilevel_analysis import MultilevelStudyResult as _Separation
from .multilevel_updates import GradualUpdateAnalysis as _Updates, PairedUpdateAnalysis as _Paired
from .multilevel_optical import OpticalSequenceResult as _Optical, MatchedOpticalSequenceResult as _Matched
from .multilevel_retention import MultilevelRetentionResult as _Retention
from .multilevel_ensemble import MultilevelEnsembleResult as _Ensemble

__all__ = ['MultilevelReportCase', 'MultilevelReport', 'build_multilevel_report',
           'write_multilevel_report', 'load_multilevel_report_bundle']

_TYPES = {'electrical': _Electrical, 'separation': _Separation, 'updates': _Updates,
          'paired_updates': _Paired, 'optical': _Optical, 'matched_optical': _Matched,
          'retention': _Retention, 'ensemble': _Ensemble}
_LIMITS = (
    'Conditional compact-model studies; no experimental qualification or new calibration.',
    'Signed delta-VFB and normalized weight proxies are not channel conductance or circuit MAC.',
    'Assumed intervals, numerical tolerances and measured noise are different quantities.',
    'Partial, failed, missing and non-assessable outcomes remain visible; null is not zero.',
    'Short retention probes and deterministic repeats establish no lifetime, endurance or cycle noise.',
    'Conditional ensemble passing fractions are not manufacturing yield.',
    'Optical accounting is not total electrical-plus-optical programming energy.',
    'Restoration validates stored evidence and static projections, without solver integration or RNG sampling.',
    'Hashes establish consistency, not experimental authenticity or proof that trajectories were executed.',
)
_FILES = frozenset(('report.json', 'report.md', 'cases.csv', 'observations.csv', 'metrics.csv', 'failures.csv', 'bundle.json'))


# Only immutable validated JSON strings are retained, and only for one restore.
# A changed validator or source text is a different key. Invalid inputs never enter.
_SOURCE_VALIDATION_CACHE = _ContextVar('multilevel_source_validation_cache', default=None)
_SOURCE_CACHE_MAX_BYTES = 2 * 1024 * 1024
_SOURCE_CACHE_MAX_ENTRIES = 16


@_contextmanager
def _source_validation_scope():
    if _SOURCE_VALIDATION_CACHE.get() is not None:
        yield
        return
    token = _SOURCE_VALIDATION_CACHE.set({'values': {}, 'bytes': 0})
    try:
        yield
    finally:
        _SOURCE_VALIDATION_CACHE.reset(token)


def _validated_source_json(kind, text):
    validator = _TYPES[kind].from_dict
    cache = _SOURCE_VALIDATION_CACHE.get()
    # The normal parser provides the existing error for non-string input.
    key = (validator, text) if type(text) is str else None
    if cache is not None and key is not None and key in cache['values']:
        return cache['values'][key]
    validated = validator(_load(text)).to_json()
    if cache is not None and key is not None:
        size = _sys.getsizeof(key) + _sys.getsizeof(text) + _sys.getsizeof(validated)
        if (len(cache['values']) < _SOURCE_CACHE_MAX_ENTRIES
                and cache['bytes'] + size <= _SOURCE_CACHE_MAX_BYTES):
            cache['values'][key] = validated
            cache['bytes'] += size
    return validated


@_dataclass(frozen=True)
class MultilevelReportCase(_Archive):
    """One exactly typed existing result, with explicit case identity and evidence."""
    name: str
    kind: str
    source_json: str
    evidence: _Evidence

    def __post_init__(self):
        _text(self.name, 'case name')
        if type(self.kind) is not str or self.kind not in _TYPES or type(self.evidence) is not _Evidence:
            raise ValueError('supported multilevel result kind and typed evidence required')
        object.__setattr__(self, 'source_json', _validated_source_json(self.kind, self.source_json))

    @classmethod
    def from_result(cls, name, result, evidence):
        kinds = [kind for kind, implementation in _TYPES.items() if type(result) is implementation]
        if len(kinds) != 1:
            raise ValueError('supported typed multilevel result required')
        return cls(name, kinds[0], result.to_json(), evidence)

    @property
    def source(self):
        return _load(self.source_json)

    @property
    def source_hash(self):
        return _hashlib.sha256(self.source_json.encode('utf-8')).hexdigest()

    def to_dict(self):
        return {'schema_version': 'multilevel-report-case-v1', 'name': self.name, 'kind': self.kind,
                'source': self.source, 'source_hash': self.source_hash, 'evidence': self.evidence.to_dict(),
                'experimental_qualification': False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'name', 'kind', 'source', 'source_hash', 'evidence', 'experimental_qualification'))
        obj = cls(raw['name'], raw['kind'], _canonical(raw['source']), _Evidence.from_dict(raw['evidence']))
        _match(raw, obj.to_dict())
        return obj


def _status(kind, summary):
    if 'status' in summary:
        return summary['status']
    if kind == 'matched_optical':
        return 'completed' if summary['light_status'] == summary['dark_status'] == 'completed' else 'partial_or_failed'
    return 'completed' if summary['complete'] else 'partial'


@_dataclass(frozen=True)
class MultilevelReport(_Archive):
    """Ordered heterogeneous studies; no pooling of incompatible contexts or metrics."""
    title: str
    cases: tuple[MultilevelReportCase, ...]
    evidence: _Evidence

    def __post_init__(self):
        _text(self.title, 'report title')
        if type(self.cases) is not tuple or not self.cases or any(type(x) is not MultilevelReportCase for x in self.cases):
            raise ValueError('nonempty immutable tuple of multilevel report cases required')
        if len({x.name for x in self.cases}) != len(self.cases) or type(self.evidence) is not _Evidence:
            raise ValueError('unique case names and typed report evidence required')
        object.__setattr__(self, 'cases', tuple(MultilevelReportCase.from_dict(x.to_dict()) for x in self.cases))

    @property
    def summary(self):
        return {'case_count': len(self.cases), 'cases': [
            {'name': x.name, 'kind': x.kind, 'source_hash': x.source_hash,
             'status': _status(x.kind, x.source['summary']), 'source_summary': x.source['summary']}
            for x in self.cases], 'pooling': 'none_case_specific_contexts_definitions_and_denominators',
            'experimental_qualification': False}

    def to_dict(self):
        return {'schema_version': 'multilevel-report-v1', 'title': self.title,
                'cases': [x.to_dict() for x in self.cases], 'evidence': self.evidence.to_dict(),
                'scientific_status': 'conditional_unqualified_compact_model_studies',
                'experimental_qualification': False, 'limitations': list(_LIMITS), 'summary': self.summary}

    @classmethod
    def from_dict(cls, raw):
        with _source_validation_scope():
            _keys(raw, ('schema_version', 'title', 'cases', 'evidence', 'scientific_status',
                        'experimental_qualification', 'limitations', 'summary'))
            if type(raw['cases']) is not list:
                raise ValueError('archived report case list required')
            obj = cls(raw['title'], tuple(MultilevelReportCase.from_dict(x) for x in raw['cases']),
                      _Evidence.from_dict(raw['evidence']))
            _match(raw, obj.to_dict())
            return obj


def build_multilevel_report(title, cases, evidence):
    return MultilevelReport(title, cases, evidence)


def _escape(value):
    if value is None:
        return 'undefined'
    return _html.escape(str(value)).replace('|', '&#124;').replace('\r', ' ').replace('\n', ' ')


def _json_bytes(raw):
    return (_json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')


def _csv_bytes(header, rows):
    stream = _io.StringIO(newline='')
    writer = _csv.writer(stream, lineterminator='\n')
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _pointer(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def _unit(key):
    for suffix, unit in (('_V', 'V'), ('_s', 's'), ('_J_m2', 'J/m2'), ('_W_m2', 'W/m2'),
                         ('_J', 'J'), ('_W', 'W'), ('_count', 'count')):
        if key.endswith(suffix):
            return unit
    if key == 'absorbed_photon_fluence_by_fg_m2':
        return 'm^-2'
    if key in ('linearity_deviation', 'asymmetry', 'weight_proxy', 'signed_weight_updates') or 'fraction' in key:
        return '1'
    return ''


def _leaves(raw, path='', unit=''):
    if type(raw) is dict:
        for key, value in sorted(raw.items()):
            yield from _leaves(value, path+'/'+_pointer(key), _unit(key) or unit)
    elif type(raw) is list:
        for index, value in enumerate(raw):
            yield from _leaves(value, path+'/'+str(index), unit)
    else:
        yield path, raw, unit


def _failures(kind, raw, path=''):
    # Follow typed result positions, never arbitrary state/evidence metadata
    # which may legitimately contain a user key called "failure".
    if kind in ('electrical', 'optical'):
        if raw['failure'] is not None:
            yield path+'/failure', raw['failure']
    elif kind == 'separation':
        for index, result in enumerate(raw['results']):
            if result is not None:
                yield from _failures('electrical', result, path+'/results/'+str(index))
    elif kind == 'updates':
        source = raw['source']
        source_kind = 'electrical' if source['schema_version'] == 'electrical-sequence-result-v1' else 'optical'
        yield from _failures(source_kind, source, path+'/source')
    elif kind == 'paired_updates':
        for branch in ('first', 'second'):
            yield from _failures('updates', raw[branch], path+'/'+branch)
    elif kind == 'matched_optical':
        yield from _failures('optical', raw['light'], path+'/light')
        yield from _failures('electrical', raw['dark'], path+'/dark')
    elif kind == 'retention':
        yield from _failures('separation', raw['plan']['prepared'], path+'/plan/prepared')
        for j, row in enumerate(raw['probes']):
            for i, result in enumerate(row):
                if result is not None:
                    yield from _failures('electrical', result, path+'/probes/'+str(j)+'/'+str(i))
    elif kind == 'ensemble':
        for index, point in enumerate(raw['points']):
            if point is not None:
                prefix = path+'/points/'+str(index)
                if point['failure'] is not None:
                    yield prefix+'/failure', point['failure']
                if point['result'] is not None:
                    yield from _failures('retention', point['result'], prefix+'/result')


def _observations(kind, raw, path='', role='', sample_id=''):
    """Yield source JSON pointers and scalar observations, never recompute physics."""
    if kind in ('electrical', 'optical'):
        read = raw['initial_read']
        if read is not None:
            yield (path+'/initial_read', role or 'initial_read', '', sample_id, 0, '',
                   read['state']['time_s'], 'delta_vfb_V', read['delta_vfb_V'], '', '', 'completed')
        else:
            yield (path+'/initial_read', role or 'initial_read', '', sample_id, 0, '', '',
                   'delta_vfb_V', '', '', '', 'missing_or_failed_read')
        for i, step in enumerate(raw['steps']):
            read = step['read']
            yield (path+'/steps/'+str(i)+'/read', role or 'post_segment_read', step['step_id'], sample_id,
                   i+1, '', step['final_state']['time_s'], 'delta_vfb_V',
                   '' if read is None else read['delta_vfb_V'], '', '',
                   'missing_or_failed_read' if read is None else 'completed')
    elif kind == 'separation':
        for i, row in enumerate(raw['summary']['levels']):
            yield (path+'/summary/levels/'+str(i), role or 'prepared_level', row['level_id'], sample_id,
                   i, '', '', 'delta_vfb_V', '' if row['readout_V'] is None else row['readout_V'],
                   '', '', row['status'])
    elif kind == 'updates':
        s = raw['summary']
        for i, value in enumerate(s['read_delta_vfb_V']):
            yield (path+'/summary/read_delta_vfb_V/'+str(i), role or 'update_read', '', sample_id, i, '',
                   s['read_times_s'][i], 'delta_vfb_V', value,
                   '' if s['weight_proxy'][i] is None else s['weight_proxy'][i], '', 'completed')
        if not s['read_delta_vfb_V']:
            yield (path+'/source', role or 'update_read', '', sample_id, '', '', '', 'delta_vfb_V',
                   '', '', '', 'no_accepted_read')
    elif kind == 'paired_updates':
        for branch in ('first', 'second'):
            yield from _observations('updates', raw[branch], path+'/'+branch, branch, sample_id)
    elif kind == 'matched_optical':
        yield from _observations('optical', raw['light'], path+'/light', 'light', sample_id)
        yield from _observations('electrical', raw['dark'], path+'/dark', 'matched_dark', sample_id)
        for i, value in enumerate(raw['summary']['light_minus_dark_delta_vfb_V']):
            yield (path+'/summary/light_minus_dark_delta_vfb_V/'+str(i), 'contrast', '', sample_id,
                   i, '', '', 'light_minus_dark_delta_vfb_V', value, '', '', 'matched')
    elif kind == 'retention':
        for j, delay in enumerate(raw['summary']['delays']):
            for i, row in enumerate(delay['levels']):
                yield (path+'/summary/delays/'+str(j)+'/levels/'+str(i), role or 'retention_endpoint',
                       row['level_id'], sample_id, i, delay['delay_s'], '', 'delta_vfb_V',
                       '' if row['readout_V'] is None else row['readout_V'],
                       '' if row['weight_proxy'] is None else row['weight_proxy'],
                       '' if row['signed_drift_V'] is None else row['signed_drift_V'], row['status'])
    elif kind == 'ensemble':
        samples = raw['plan']['manifest']['samples']
        for i, point in enumerate(raw['points']):
            identity = samples[i]['sample_id']
            if point is not None and point['result'] is not None:
                yield from _observations('retention', point['result'], path+'/points/'+str(i)+'/result',
                                         'ensemble_retention_endpoint', identity)
            else:
                yield (path+'/points/'+str(i), 'ensemble_sample', '', identity, i, '', '', 'delta_vfb_V',
                       '', '', '', 'missing' if point is None else point['status'])


def _primary(kind, summary):
    fields = {'electrical': ('completed_step_count', 'requested_step_count'),
              'optical': ('completed_step_count', 'requested_step_count'),
              'separation': ('minimum_signed_margin_V', 'pair_assessment_fraction'),
              'updates': ('linearity_deviation', 'reason', 'direction_reversal_count'),
              'paired_updates': ('asymmetry', 'reason'),
              'matched_optical': ('matched_read_count', 'requested_read_count'),
              'retention': ('completed_observation_count', 'requested_observation_count'),
              'ensemble': ('completed_sample_count', 'partial_sample_count', 'failed_sample_count', 'requested_sample_count')}
    return '; '.join(key+'='+('undefined' if summary[key] is None else str(summary[key])) for key in fields[kind])


def _render(report):
    raw = report.to_dict()
    cases, observations, metrics, failures = [], [], [], []
    md = ['# '+_escape(report.title), '', 'Scientific status: **conditional compact-model studies**.',
          'Experimental qualification: **false**.', '', 'Report hash: `'+report.contract_hash+'`.', '',
          '## Cases', '', '| Case | Kind | Source status | Selected diagnostics |', '|---|---|---|---|']
    for case in raw['cases']:
        name, kind, source, digest = case['name'], case['kind'], case['source'], case['source_hash']
        s = source['summary']
        status = _status(kind, s)
        cases.append((name, kind, digest, status, _canonical(case['evidence']), 'false'))
        md.append('| '+' | '.join(_escape(x) for x in (name, kind, status, _primary(kind, s)))+' |')
        observations.extend((name, kind, digest, *row) for row in _observations(kind, source))
        for path, value, unit in _leaves(s, '/summary'):
            metrics.append((name, kind, digest, path, _canonical(value), unit))
        for path, failure in _failures(kind, source):
            failures.append((name, kind, digest, path, failure.get('stage', ''),
                             failure.get('exception_type', ''), failure.get('message', '')))
    md += ['', '## Source identities', '', '| Case | Source SHA-256 |', '|---|---|']
    md += ['| '+_escape(case['name'])+' | `'+case['source_hash']+'` |' for case in raw['cases']]
    md += ['', '## Reading the files', '',
           'report.json retains every original request, state, read observation, failure and source summary.',
           'observations.csv is a scalar view; source_path is a JSON pointer within that case source.',
           'metrics.csv preserves every scalar source-summary value as typed JSON, including null.',
           'Blank numeric observation cells are undefined, never silently zero.',
           'Case statuses retain their source-specific definitions. Cases are not pooled or ranked.', '',
           '## Limitations', '']+['- '+_escape(x) for x in _LIMITS]+['']
    return {'report.json': _json_bytes(raw), 'report.md': '\n'.join(md).encode('utf-8'),
            'cases.csv': _csv_bytes(('case','kind','source_hash','source_status','evidence_json','experimental_qualification'), cases),
            'observations.csv': _csv_bytes(('case','kind','source_hash','source_path','role','level_or_step_id',
                'sample_id','index','delay_s','absolute_time_s','observable','readout_V','weight_proxy','signed_drift_V','status'), observations),
            'metrics.csv': _csv_bytes(('case','kind','source_hash','source_path','value_json','unit'), metrics),
            'failures.csv': _csv_bytes(('case','kind','source_hash','source_path','stage','exception_type','message'), failures)}


def _manifest(report, files):
    return {'schema_version': 'multilevel-report-bundle-v1', 'report_hash': report.contract_hash,
            'case_sources': [{'name': x.name, 'kind': x.kind, 'source_hash': x.source_hash} for x in report.cases],
            'files': {name: _hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())}}


def write_multilevel_report(report, destination):
    """Write a new bundle directory; never overwrite existing content."""
    if type(report) is not MultilevelReport:
        raise ValueError('typed multilevel report required')
    report = MultilevelReport.from_dict(report.to_dict())
    files = _render(report)
    files['bundle.json'] = _json_bytes(_manifest(report, files))
    destination = _Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, value in files.items():
            path = destination/name
            with path.open('xb') as stream:
                created.append(path)
                stream.write(value)
    except BaseException:
        for path in created:
            path.unlink()
        if not any(destination.iterdir()):
            destination.rmdir()
        raise
    return destination


def load_multilevel_report_bundle(destination):
    """Validate exact membership, original sources, hashes and all regenerated views."""
    destination = _Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('ordinary multilevel bundle directory required')
    entries = list(destination.iterdir())
    if {x.name for x in entries} != _FILES or any(x.is_symlink() or not x.is_file() for x in entries):
        raise ValueError('invalid multilevel bundle membership')
    report = MultilevelReport.from_json((destination/'report.json').read_text(encoding='utf-8'))
    files = _render(report)
    manifest = _load((destination/'bundle.json').read_text(encoding='utf-8'))
    _match(manifest, _manifest(report, files))
    for name, value in files.items():
        if (destination/name).read_bytes() != value:
            raise ValueError('multilevel bundle projection mismatch: '+name)
    return report
