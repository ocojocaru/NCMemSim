# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Accounting, source reconstruction and bundle integrity checks for U6."""
import hashlib
import json

import pytest

from examples.phase_u6_coulomb_report import build_report
from ncmemsim.coulomb_reporting import (
    CoulombStudyReport, load_coulomb_study_bundle, write_coulomb_study_bundle,
)
from ncmemsim.performance_contracts import _hash


def test_report_retains_population_and_owns_inputs():
    report = build_report()
    raw = report.to_dict()
    assert raw['summary'] == {
        'attempted_count': 6,
        'outcomes': {'evaluated': 4, 'unavailable': 1, 'numerical_failure': 1},
    }
    assert raw['cases'][4]['result']['hole']['status'] == 'no_bound_state'
    assert raw['cases'][4]['result']['energy_shift_J'] is None
    assert raw['cases'][5]['result']['reason']
    assert raw['cases'][0]['result']['tail_bound'] < 1e-10
    assert CoulombStudyReport.from_json(report.to_json()).to_dict() == raw
    raw['cases'].clear()
    assert len(report.to_dict()['cases']) == 6


@pytest.mark.parametrize('field', ['coefficient', 'energy_shift_J', 'tail_bound', 'screening_evidence'])
def test_rehashed_source_tampering_rejected(field):
    raw = build_report().to_dict()
    row = raw['cases'][0]
    row['result'][field] = None
    row['result_hash'] = _hash(row['result'])
    with pytest.raises(ValueError):
        CoulombStudyReport.from_dict(raw)


def test_summary_policy_and_json_validation():
    report = build_report()
    for field in ('summary', 'numerical_policy', 'constants', 'limitations'):
        raw = report.to_dict()
        raw[field] = None
        with pytest.raises(ValueError, match='inconsistent'):
            CoulombStudyReport.from_dict(raw)
    with pytest.raises(ValueError, match='duplicate'):
        CoulombStudyReport.from_json('{"title":"first","title":"second"}')
    raw = report.to_dict()
    case = {key: raw['cases'][0][key] for key in ('label', 'result', 'settings')}
    with pytest.raises(ValueError, match='duplicate'):
        CoulombStudyReport('Duplicate control', [case, case])


def test_bundle_determinism_and_overwrite(tmp_path):
    report = build_report()
    first = write_coulomb_study_bundle(report, tmp_path / 'first')
    second = write_coulomb_study_bundle(report, tmp_path / 'second')
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert load_coulomb_study_bundle(first).contract_hash == report.contract_hash
    with pytest.raises(FileExistsError):
        write_coulomb_study_bundle(report, first)
    (first / 'extra').touch()
    with pytest.raises(ValueError, match='membership'):
        load_coulomb_study_bundle(first)


def test_rehashed_csv_tampering_rejected(tmp_path):
    bundle = write_coulomb_study_bundle(build_report(), tmp_path / 'bundle')
    csv = bundle / 'cases.csv'
    csv.write_bytes(csv.read_bytes() + b'forged\n')
    manifest = bundle / 'bundle.json'
    raw = json.loads(manifest.read_bytes())
    raw['files']['cases.csv'] = hashlib.sha256(csv.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(ValueError, match='inconsistent'):
        load_coulomb_study_bundle(bundle)
