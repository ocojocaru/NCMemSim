# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned isolated-action reports and deterministic bundles; no device/provider replay."""
from __future__ import annotations
import csv as _csv
import hashlib as _hashlib
import html as _html
import io as _io
import json as _json
import math as _math
from pathlib import Path as _Path
from .performance_contracts import _Owned, _canonical, _hash, _text, _unique, _reject
from .barrier_evaluation import BarrierEvaluationResult as _Result

__all__ = ['BarrierStudyReport', 'write_barrier_study_report', 'load_barrier_study_bundle']
_LIMITS = [
    'Isolated electron action only; no simulator, provider or transport-step replay.',
    'Restoration verifies S2 diagnostics with its fixed portability budget, not a new device solve.',
    'Reference values, settings, provenance and source labels are caller declarations, not authenticated evidence.',
    'Reference comparisons use the original request tolerances, not physical uncertainty bounds.',
    'No current, retention lifetime, yield, optimal device or experimental qualification is inferred.',
    'Hashes and deterministic projections establish consistency, not authenticity.',
    'S4 snapshot-bound transport histories require a separate schema; they are not accepted as isolated results.']


def _keys(raw, names):
    if type(raw) is not dict or set(raw) != set(names):
        raise ValueError('unknown or missing S6 fields')


def _same(left, right):
    if _canonical(left) != _canonical(right):
        raise ValueError('inconsistent barrier report source or projection')


def _assessment(result, reference):
    actual = result['summary']['wkb_exponent']
    if reference is not None:
        try:
            valid = type(reference) in (int, float) and _math.isfinite(reference) and reference >= 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('reference exponent must be finite and nonnegative or null')
    if actual is None or reference is None:
        return dict(status='unavailable', absolute_error=None, acceptance_limit=None,
                    reason='evaluation_failed' if actual is None else 'reference_not_supplied')
    spec = result['request']
    # Work with exact binary rational values if the tolerance sum would overflow.
    from fractions import Fraction
    error = abs(Fraction(actual)-Fraction(reference))
    limit = Fraction(spec['exponent_atol'])+Fraction(spec['exponent_rtol'])*Fraction(reference)
    def finite(value):
        try:
            converted = float(value)
        except OverflowError:
            return None
        return converted if _math.isfinite(converted) else None
    return dict(status='matched' if error <= limit else 'mismatched',
        absolute_error=finite(error), acceptance_limit=finite(limit), reason=None,
        exact_absolute_error=dict(numerator=error.numerator, denominator=error.denominator),
        exact_acceptance_limit=dict(numerator=limit.numerator, denominator=limit.denominator))


class BarrierStudyReport(_Owned):
    """Ordered isolated evaluations with owned settings and retained negative outcomes."""
    __slots__ = ()

    def __init__(self, title, cases):
        _text(title, 'title')
        if type(cases) is not list or not cases:
            raise ValueError('nonempty ordered cases required')
        rows = []; labels = set()
        for case in cases:
            _keys(case, ('label', 'result', 'settings', 'reference_exponent', 'reference_description'))
            label = _text(case['label'], 'label')
            if label in labels:
                raise ValueError('duplicate case label')
            labels.add(label)
            if type(case['settings']) is not dict:
                raise ValueError('native settings object required')
            _canonical(case['settings'])
            _text(case['reference_description'], 'reference_description')
            result = _Result.from_dict(case['result']).to_dict()
            assessment = _assessment(result, case['reference_exponent'])
            row = dict(case, result=result, result_hash=_hash(result), assessment=assessment)
            rows.append(row)
        summary = dict(attempted_count=len(rows),
            completed_count=sum(r['result']['summary']['status']=='completed' for r in rows),
            failed_count=sum(r['result']['summary']['status']=='failed' for r in rows),
            matched_count=sum(r['assessment']['status']=='matched' for r in rows),
            mismatched_count=sum(r['assessment']['status']=='mismatched' for r in rows),
            unavailable_count=sum(r['assessment']['status']=='unavailable' for r in rows),
            transmission_underflow_count=sum(r['result']['summary']['attenuation_status']=='transmission_underflow' for r in rows),
            experimental_qualification=False, model_uncertainty_estimated=False)
        self._store(dict(schema_version='barrier-study-report-v1', title=title,
                         cases=rows, summary=summary, limitations=_LIMITS))

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ('schema_version', 'title', 'cases', 'summary', 'limitations'))
        if type(raw['cases']) is not list:
            raise ValueError('ordered cases required')
        cases = []
        for row in raw['cases']:
            _keys(row, ('label', 'result', 'settings', 'reference_exponent',
                        'reference_description', 'result_hash', 'assessment'))
            cases.append({key: row[key] for key in ('label', 'result', 'settings',
                         'reference_exponent', 'reference_description')})
        obj = cls(raw['title'], cases)
        _same(raw, obj.to_dict())
        return obj


def _bytes(raw):
    return (_json.dumps(raw, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')


def _table(header, rows):
    stream = _io.StringIO(newline='')
    writer = _csv.writer(stream, lineterminator='\n')
    writer.writerow(header); writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def _render(report):
    raw = report.to_dict(); cases = []; segments = []
    lines = ['# '+_html.escape(raw['title']).replace('\n', ' '), '',
             'Isolated action diagnostics. Experimental qualification: **false**.', '',
             '| Case | Evaluation | Comparison | B | T |', '|---|---|---|---|---|']
    for row in raw['cases']:
        s = row['result']['summary']
        cases.append([row['label'], row['result_hash'], row['result']['request_hash'],
            s['status'], s['wkb_exponent'], s['log_transmission'], s['transmission'],
            s['attenuation_status'], s['failure'], row['reference_exponent'],
            row['assessment']['status'], _canonical(row['assessment']),
            _canonical(row['settings']), row['reference_description']])
        cells = (row['label'], s['status'], row['assessment']['status'], s['wkb_exponent'], s['transmission'])
        lines.append('| '+' | '.join(_html.escape(str(v)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ') for v in cells)+' |')
        for segment in row['result']['segments']:
            segments.append([row['label'], _canonical(segment)])
    lines += ['', '## Limitations', '']+['- '+v for v in _LIMITS]+['',
        'Full profiles, units, provenance, settings and failed diagnostics remain in report.json.',
        'Undefined numeric CSV cells are empty; JSON retains null.', '']
    return {'report.json': _bytes(raw), 'report.md': '\n'.join(lines).encode('utf-8'),
        'cases.csv': _table(['label','result_hash','request_hash','status','wkb_exponent',
            'log_transmission','transmission','attenuation_status','failure','reference_exponent',
            'comparison','assessment_json','settings_json','reference_description'], cases),
        'segments.csv': _table(['label','segment_diagnostics_json'], segments)}


def _manifest(report, files):
    return dict(schema_version='barrier-study-bundle-v1', report_hash=report.contract_hash,
        files={name: _hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())})


def write_barrier_study_report(report, destination):
    """Create a new deterministic bundle, refusing to overwrite any destination."""
    if type(report) is not BarrierStudyReport:
        raise ValueError('typed barrier report required')
    report = BarrierStudyReport.from_dict(report.to_dict())
    files = _render(report); files['bundle.json'] = _bytes(_manifest(report, files))
    destination = _Path(destination); destination.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, value in files.items():
            path = destination/name
            with path.open('xb') as stream:
                created.append(path); stream.write(value)
    except BaseException:
        for path in created:
            path.unlink()
        if not any(destination.iterdir()):
            destination.rmdir()
        raise
    return destination


def load_barrier_study_bundle(destination):
    """Validate exact membership, source consistency, manifest and every projection."""
    destination = _Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('ordinary bundle directory required')
    entries = list(destination.iterdir())
    names = {'report.json','report.md','cases.csv','segments.csv','bundle.json'}
    if {p.name for p in entries} != names or any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError('invalid bundle membership')
    report = BarrierStudyReport.from_json((destination/'report.json').read_text(encoding='utf-8'))
    files = _render(report)
    manifest = _json.loads((destination/'bundle.json').read_text(encoding='utf-8'),
                          object_pairs_hook=_unique, parse_constant=_reject)
    _same(manifest, _manifest(report, files))
    for name, value in files.items():
        if (destination/name).read_bytes() != value:
            raise ValueError('bundle projection mismatch: '+name)
    return report
