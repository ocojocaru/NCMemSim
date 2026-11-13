# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Strict finite-well reports and deterministic directory bundles."""
import hashlib as _hashlib
import html as _html
import json as _json
import math as _math
from pathlib import Path as _Path

from .barrier_reporting import _bytes, _table
from .materials.finite_confinement import evaluate_finite_confinement as _evaluate
from .materials.finite_confinement_contracts import FiniteConfinementRequest as _Request
from .performance_contracts import _Owned, _canonical, _hash, _reject, _text, _unique

__all__ = [
    'FiniteConfinementStudyReport', 'write_finite_confinement_study_bundle',
    'load_finite_confinement_study_bundle',
]

_CASE_FIELDS = ('label', 'results', 'settings', 'references')
_LIMITS = [
    'Restoration repeats the isolated ground-state evaluations and requires exact diagnostic agreement.',
    'Use a numerically compatible runtime to restore archived results.',
    'Reference values and settings are caller declarations. Hashes check consistency, not authenticity.',
    'Pair energies sum independent carrier contributions. No excitonic correction or experimental qualification.',
    'No optical, spectral or device simulation is replayed by this report format.',
]


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('unknown or missing finite confinement report fields')


def _same(actual, expected):
    if _canonical(actual) != _canonical(expected):
        raise ValueError('inconsistent finite confinement report source or projection')


def _result(raw):
    if type(raw) is not dict or 'request' not in raw:
        raise ValueError('result with an original request required')
    rebuilt = _evaluate(_Request.from_dict(raw['request'])).to_dict()
    _same(raw, rebuilt)
    return rebuilt


def _reference(reference, result):
    if reference is None:
        return {'status': 'not_supplied', 'absolute_error_J': None}
    _keys(reference, ('description', 'energy_J', 'absolute_tolerance_J'))
    _text(reference['description'], 'reference description')
    for key in ('energy_J', 'absolute_tolerance_J'):
        value = reference[key]
        try:
            valid = type(value) in (int, float) and _math.isfinite(value) and value >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f'{key} must be finite and nonnegative')
    if result['status'] != 'bound':
        return {'status': 'unavailable', 'absolute_error_J': None}
    error = abs(result['energy_J'] - reference['energy_J'])
    return {
        'status': 'matched' if error <= reference['absolute_tolerance_J'] else 'mismatched',
        'absolute_error_J': error,
    }


def _pair(results):
    if len(results) == 1:
        return None
    electron, hole = (result['request'] for result in results)
    if (electron['carrier'], hole['carrier']) != ('electron', 'hole') or any(
        electron[key] != hole[key] for key in ('radius_m', 'temperature_K', 'dot_material', 'host_material')
    ):
        raise ValueError('matched electron and hole requests required for a pair')
    if any(result['status'] != 'bound' for result in results):
        return {'status': 'unavailable', 'kinetic_sum_J': None}
    energy = results[0]['energy_J'] + results[1]['energy_J']
    if not _math.isfinite(energy):
        return {'status': 'numerical_failure', 'kinetic_sum_J': None}
    return {'status': 'available', 'kinetic_sum_J': energy}


class FiniteConfinementStudyReport(_Owned):
    """Own ordered single-carrier and pair cases, settings and reference evidence."""
    __slots__ = ()

    def __init__(self, title, cases):
        _text(title, 'title')
        if type(cases) is not list or not cases:
            raise ValueError('nonempty ordered cases required')
        rows = []
        labels = set()
        counts = dict.fromkeys(('bound', 'no_bound_state', 'threshold_unresolved', 'numerical_failure'), 0)
        for case in cases:
            _keys(case, _CASE_FIELDS)
            label = _text(case['label'], 'case label')
            if label in labels:
                raise ValueError('duplicate case label')
            labels.add(label)
            if type(case['settings']) is not dict:
                raise ValueError('case settings must be a JSON object')
            raw_results, references = case['results'], case['references']
            if (type(raw_results) is not list or len(raw_results) not in (1, 2)
                or type(references) is not list or len(references) != len(raw_results)):
                raise ValueError('one or two results with one reference entry per result required')
            results = [_result(raw) for raw in raw_results]
            assessments = [_reference(ref, result) for ref, result in zip(references, results)]
            for result in results:
                counts[result['status']] += 1
            rows.append(dict(case, results=results, result_hashes=[_hash(r) for r in results],
                             assessments=assessments, pair=_pair(results)))
        self._store({
            'schema_version': 'finite-confinement-study-report-v1',
            'title': title, 'cases': rows, 'limitations': _LIMITS,
            'summary': {
                'attempted_cases': len(rows), 'carrier_outcomes': counts,
                'pair_outcomes': {
                    status: sum(row['pair'] is not None and row['pair']['status'] == status for row in rows)
                    for status in ('available', 'unavailable', 'numerical_failure')
                },
                'experimental_qualification': False,
            },
        })

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'title', 'cases', 'summary', 'limitations'))
        if type(raw['cases']) is not list:
            raise ValueError('ordered cases required')
        cases = []
        for row in raw['cases']:
            _keys(row, (*_CASE_FIELDS, 'result_hashes', 'assessments', 'pair'))
            cases.append({key: row[key] for key in _CASE_FIELDS})
        obj = cls(raw['title'], cases)
        _same(raw, obj.to_dict())
        return obj


def _render(report):
    raw = report.to_dict()
    cases, carriers = [], []
    for index, row in enumerate(raw['cases'], 1):
        pair = row['pair']
        cases.append((index, len(row['results']), None if pair is None else pair['status'],
                      None if pair is None else pair['kinetic_sum_J']))
        for result, digest, assessment in zip(row['results'], row['result_hashes'], row['assessments']):
            carriers.append((
                index, result['request']['carrier'], result['status'], result['reason'],
                result['energy_J'], result['penetration_depth_m'], result['outside_probability'],
                assessment['status'], digest,
            ))
    title = _html.escape(' '.join(raw['title'].splitlines()))
    lines = ['# ' + title, '', f"Attempted cases: {raw['summary']['attempted_cases']}.", '']
    lines += [f"- {key}: {value}" for key, value in raw['summary']['carrier_outcomes'].items()]
    lines += ['', '## Limitations', '', *('- ' + limit for limit in _LIMITS), '']
    return {
        'report.json': _bytes(raw),
        'report.md': '\n'.join(lines).encode('utf-8'),
        'cases.csv': _table(('case', 'carriers', 'pair_status', 'kinetic_sum_J'), cases),
        'carriers.csv': _table((
            'case', 'carrier', 'status', 'reason', 'energy_J', 'penetration_depth_m',
            'outside_probability', 'reference_status', 'result_hash',
        ), carriers),
    }


def _manifest(report, files):
    return {
        'schema_version': 'finite-confinement-study-bundle-v1',
        'report_hash': report.contract_hash,
        'files': {name: _hashlib.sha256(value).hexdigest() for name, value in files.items()},
    }


def write_finite_confinement_study_bundle(report, destination):
    """Write a new bundle, with exclusive creation of its directory and files."""
    if type(report) is not FiniteConfinementStudyReport:
        raise ValueError('typed finite confinement report required')
    files = _render(report)
    files['bundle.json'] = _bytes(_manifest(report, files))
    destination = _Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, data in files.items():
            path = destination / name
            with path.open('xb') as stream:
                created.append(path)
                stream.write(data)
    except BaseException:
        for path in created:
            path.unlink()
        if not any(destination.iterdir()):
            destination.rmdir()
        raise
    return destination


def load_finite_confinement_study_bundle(destination):
    """Check the exact file set, reconstruct the report and verify every file."""
    destination = _Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('ordinary bundle directory required')
    entries = list(destination.iterdir())
    names = {'report.json', 'report.md', 'cases.csv', 'carriers.csv', 'bundle.json'}
    if {path.name for path in entries} != names or any(
        path.is_symlink() or not path.is_file() for path in entries
    ):
        raise ValueError('invalid bundle membership')
    report = FiniteConfinementStudyReport.from_json((destination / 'report.json').read_text(encoding='utf-8'))
    files = _render(report)
    manifest = _json.loads((destination / 'bundle.json').read_text(encoding='utf-8'),
                           object_pairs_hook=_unique, parse_constant=_reject)
    _same(manifest, _manifest(report, files))
    for name, data in files.items():
        if (destination / name).read_bytes() != data:
            raise ValueError('bundle projection mismatch: ' + name)
    return report
