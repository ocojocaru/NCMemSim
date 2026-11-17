# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check the controlled U2 population and one-sided conclusions."""
import json

import pytest

from examples.phase_u2_coulomb_applicability import run_study
from ncmemsim.hashing import canonical_hash


def test_continuum_diagnostic():
    report = run_study()
    rows = {row['label']: row for row in report['cases']}
    baseline = rows['baseline']
    eps_control = rows['weaker_screening']
    shallow = rows['shallower_hole']
    assert baseline['assessment'] == eps_control['assessment'] == 'inconclusive'
    ratio = baseline['shift_to_min_continuum_separation']
    assert eps_control['continuum_separation_J'] == baseline['continuum_separation_J']
    assert eps_control['shift_to_min_continuum_separation'] == pytest.approx(2*ratio)
    assert shallow['result']['hole']['status'] == 'bound'
    assert shallow['result']['hole']['outside_probability'] > baseline['result']['hole']['outside_probability']
    for label in ('smaller_radius', 'shallower_hole'):
        row = rows[label]
        assert row['assessment'] == 'shift_reaches_continuum_scale'
        assert row['shift_to_min_continuum_separation'] >= 1
    unbound = rows['unbound_hole']
    assert unbound['result']['hole']['status'] == 'no_bound_state'
    assert unbound['assessment'] == 'unavailable'
    assert unbound['shift_to_min_continuum_separation'] is None
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report['study_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'study_hash'})
