# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Verify report reconstruction and deterministic bundle integrity."""
import hashlib
import json
from dataclasses import replace

import pytest

from examples.phase_t6_finite_confinement_report import build_report
from ncmemsim.finite_confinement_reporting import (
    FiniteConfinementStudyReport, load_finite_confinement_study_bundle,
    write_finite_confinement_study_bundle,
)
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from test_phase_t2_finite_confinement import _request


def test_case_accounting_reference_and_owned_data():
    report = build_report()
    raw = report.to_dict()
    assert raw['summary']['carrier_outcomes'] == {
        'bound': 6, 'no_bound_state': 1, 'numerical_failure': 0, 'threshold_unresolved': 0,
    }
    assert raw['summary']['pair_outcomes'] == {'available': 2, 'unavailable': 1, 'numerical_failure': 0}
    assert raw['cases'][0]['assessments'][0]['status'] == 'matched'
    assert raw['cases'][1]['pair'] == {'kinetic_sum_J': None, 'status': 'unavailable'}
    assert raw['cases'][0]['results'][0]['outside_probability'] > 0
    assert FiniteConfinementStudyReport.from_json(report.to_json()).contract_hash == report.contract_hash
    raw['cases'].clear()
    assert len(report.to_dict()['cases']) == 4


def test_threshold_and_numerical_failure_are_retained():
    threshold = _request(1., 1.5707963267948966)
    failed = replace(threshold, inside_mass_m0=1e308, outside_mass_m0=5e-324)
    cases = [
        {'label': label, 'results': [evaluate_finite_confinement(request).to_dict()],
         'settings': {}, 'references': [None]}
        for label, request in [('threshold', threshold), ('unrepresentable mass ratio', failed)]
    ]
    report = FiniteConfinementStudyReport('Negative controls', cases)
    restored = FiniteConfinementStudyReport.from_json(report.to_json()).to_dict()
    assert [row['results'][0]['status'] for row in restored['cases']] == [
        'threshold_unresolved', 'numerical_failure',
    ]
    assert all(row['results'][0]['energy_J'] is None for row in restored['cases'])


@pytest.mark.parametrize('field', ['energy_J', 'outside_probability', 'request_hash', 'status'])
def test_reconstruction_rejects_rehashed_result_tamper(field):
    from ncmemsim.performance_contracts import _hash

    raw = build_report().to_dict()
    row = raw['cases'][0]
    row['results'][0][field] = None
    row['result_hashes'][0] = _hash(row['results'][0])
    with pytest.raises(ValueError, match='inconsistent'):
        FiniteConfinementStudyReport.from_dict(raw)


def test_bundle_is_deterministic_and_refuses_overwrite(tmp_path):
    report = build_report()
    first = write_finite_confinement_study_bundle(report, tmp_path / 'first')
    second = write_finite_confinement_study_bundle(report, tmp_path / 'second')
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert load_finite_confinement_study_bundle(first).to_dict() == report.to_dict()
    with pytest.raises(FileExistsError):
        write_finite_confinement_study_bundle(report, first)


def test_bundle_rejects_modified_projection_even_with_updated_digest(tmp_path):
    bundle = write_finite_confinement_study_bundle(build_report(), tmp_path / 'bundle')
    projection = bundle / 'carriers.csv'
    data = projection.read_bytes() + b'forged\n'
    projection.write_bytes(data)
    manifest_path = bundle / 'bundle.json'
    manifest = json.loads(manifest_path.read_bytes())
    manifest['files']['carriers.csv'] = hashlib.sha256(data).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='inconsistent'):
        load_finite_confinement_study_bundle(bundle)
    (bundle / 'extra').touch()
    with pytest.raises(ValueError, match='membership'):
        load_finite_confinement_study_bundle(bundle)
