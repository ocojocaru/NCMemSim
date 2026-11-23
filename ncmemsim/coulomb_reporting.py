# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned direct Coulomb evaluations and deterministic study bundles."""
import hashlib as _hashlib
import html as _html
import json as _json
from pathlib import Path as _Path

from .barrier_reporting import _bytes, _table
from .constants import ELEMENTARY_CHARGE_C as _Q, EPSILON_0_F_M as _EPS0
from .materials.electron_hole_coulomb import evaluate_electron_hole_coulomb as _evaluate
from .materials.finite_confinement_contracts import FiniteConfinementRequest as _Request
from .materials.structural import StructuralEvidence as _Evidence
from .performance_contracts import _Owned, _canonical, _hash, _reject, _text, _unique

__all__ = ['CoulombStudyReport', 'write_coulomb_study_bundle', 'load_coulomb_study_bundle']

_LIMITS = [
    'First-order direct electron–hole energy with declared uniform dielectric screening.',
    'Reference provenance and model applicability are caller declarations.',
    'Restoration repeats the isolated evaluation with exact diagnostic agreement.',
    'Restoration requires a numerically compatible runtime.',
    'Off-diagonal radial and angular study outputs use their separate U4 and U5 formats.',
    'Optical applicability requires assessment beyond the diagonal energy shift.',
]
_POLICY = {
    'id': 'u1-direct-coulomb-quadrature-v1',
    'orders': [16, 32, 64, 128],
    'max_relative_refinement_plus_tail': 1e-8,
    'max_tail_bound': 1e-10,
}


def _keys(raw, names):
    if type(raw) is not dict or set(raw) != set(names):
        raise ValueError('unknown or missing Coulomb report fields')


def _same(actual, expected):
    if _canonical(actual) != _canonical(expected):
        raise ValueError('inconsistent Coulomb source or projection')


def _restore_result(raw):
    if type(raw) is not dict:
        raise ValueError('Coulomb result object required')
    try:
        result = _evaluate(
            _Request.from_dict(raw['electron']['request']),
            _Request.from_dict(raw['hole']['request']),
            relative_permittivity=raw['relative_permittivity'],
            screening_evidence=_Evidence.from_dict(raw['screening_evidence']),
        )
    except (KeyError, TypeError) as error:
        raise ValueError('incomplete Coulomb result source') from error
    _same(raw, result)
    return result


class CoulombStudyReport(_Owned):
    """Own an ordered population of source-verified U1 Coulomb results."""
    __slots__ = ()

    def __init__(self, title, cases):
        _text(title, 'title')
        if type(cases) is not list or not cases:
            raise ValueError('nonempty ordered cases required')
        rows = []
        labels = set()
        counts = dict.fromkeys(('evaluated', 'unavailable', 'numerical_failure'), 0)
        for case in cases:
            _keys(case, ('label', 'result', 'settings'))
            label = _text(case['label'], 'case label')
            if label in labels:
                raise ValueError('duplicate case label')
            labels.add(label)
            if type(case['settings']) is not dict:
                raise ValueError('settings object required')
            result = _restore_result(case['result'])
            counts[result['status']] += 1
            rows.append(dict(case, result=result, result_hash=_hash(result)))
        self._store({
            'schema_version': 'direct-coulomb-study-report-v1',
            'title': title, 'cases': rows,
            'units': {'energy_shift': 'J', 'radius': 'm', 'relative_permittivity': '1'},
            'constants': {'elementary_charge_C': _Q, 'epsilon_0_F_m': _EPS0},
            'numerical_policy': _POLICY,
            'summary': {'attempted_count': len(rows), 'outcomes': counts},
            'limitations': _LIMITS,
        })

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'title', 'cases', 'units', 'constants',
                    'numerical_policy', 'summary', 'limitations'))
        if type(raw['cases']) is not list:
            raise ValueError('ordered cases required')
        cases = []
        for row in raw['cases']:
            _keys(row, ('label', 'result', 'settings', 'result_hash'))
            cases.append({key: row[key] for key in ('label', 'result', 'settings')})
        obj = cls(raw['title'], cases)
        _same(raw, obj.to_dict())
        return obj


def _render(report):
    raw = report.to_dict()
    rows = [
        (index, case['result']['status'], case['result']['reason'],
         case['result']['coefficient'], case['result']['energy_shift_J'],
         case['result']['relative_permittivity'], case['result']['quadrature_change'],
         case['result']['tail_bound'], case['result_hash'])
        for index, case in enumerate(raw['cases'], 1)
    ]
    title = _html.escape(' '.join(raw['title'].splitlines()))
    lines = ['# ' + title, '', f"Attempted cases: {raw['summary']['attempted_count']}.", '']
    lines += [f'- {status}: {count}' for status, count in raw['summary']['outcomes'].items()]
    lines += ['', '| Case | Status | Energy shift in J |', '|---|---|---|']
    lines += [f'| {row[0]} | {row[1]} | {row[4] if row[4] is not None else "unavailable"} |' for row in rows]
    lines += ['', '## Scope and restoration', '', *('- ' + limit for limit in _LIMITS), '']
    return {
        'report.json': _bytes(raw),
        'report.md': '\n'.join(lines).encode('utf-8'),
        'cases.csv': _table(
            ('case', 'status', 'reason', 'coefficient', 'energy_shift_J',
             'relative_permittivity', 'quadrature_change', 'tail_bound', 'result_hash'), rows,
        ),
    }


def _manifest(report, files):
    return {
        'schema_version': 'direct-coulomb-study-bundle-v1',
        'report_hash': report.contract_hash,
        'files': {name: _hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }


def write_coulomb_study_bundle(report, destination):
    """Write a new deterministic bundle with exclusive file creation."""
    if type(report) is not CoulombStudyReport:
        raise ValueError('typed Coulomb study report required')
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


def load_coulomb_study_bundle(destination):
    """Rebuild source diagnostics and check exact membership and file contents."""
    destination = _Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('ordinary bundle directory required')
    entries = list(destination.iterdir())
    names = {'report.json', 'report.md', 'cases.csv', 'bundle.json'}
    if {path.name for path in entries} != names or any(
        path.is_symlink() or not path.is_file() for path in entries
    ):
        raise ValueError('invalid bundle membership')
    report = CoulombStudyReport.from_json((destination / 'report.json').read_text(encoding='utf-8'))
    files = _render(report)
    manifest = _json.loads((destination / 'bundle.json').read_text(encoding='utf-8'),
                           object_pairs_hook=_unique, parse_constant=_reject)
    _same(manifest, _manifest(report, files))
    for name, data in files.items():
        if (destination / name).read_bytes() != data:
            raise ValueError('bundle projection mismatch: ' + name)
    return report
