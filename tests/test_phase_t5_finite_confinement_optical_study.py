# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check controlled optical comparisons and source-grid refinement."""
import json

import pytest

from examples.phase_t5_finite_confinement_optical_study import run_study
from ncmemsim.hashing import canonical_hash


@pytest.fixture(scope='module')
def study():
    return run_study()


def test_fixed_physics_grid_refinement_and_balance(study):
    rows = study['wavelength_refinement']['responses']
    for model in ('finite', 'infinite'):
        series = [rows[str(n)][model] for n in (16, 32, 64, 128)]
        for row in series:
            assert row['model_identity'] == series[-1]['model_identity']
            assert row['optical_points'] == series[-1]['optical_points']
            summary = row['spectrum']
            assert summary['incident_irradiance_W_m2'] == pytest.approx(1)
            assert abs(summary['power_balance_residual_W_m2']) < 1e-14
            assert abs(summary['photon_balance_residual_m2_s']) < 1e-14 * summary['incident_photon_flux_m2_s']
        for key in ('absorbed_irradiance_W_m2', 'absorbed_photon_flux_m2_s'):
            values = [row['spectrum'][key] for row in series]
            assert abs(values[-2] - values[-1]) < abs(values[0] - values[-1])
            assert values[-2] == pytest.approx(values[-1], rel=0.01)


def test_matched_optical_comparison_and_sensitivity(study):
    baseline = study['wavelength_refinement']['responses']['128']
    finite, infinite = (baseline[model]['optical_points'][0] for model in ('finite', 'infinite'))
    assert finite['gamma_gap_eV'] < infinite['gamma_gap_eV']
    assert finite['l_gap_eV'] == infinite['l_gap_eV']
    assert finite['alpha_m_inv'] > infinite['alpha_m_inv']
    sensitivity = study['physical_sensitivity']
    smaller = sensitivity['smaller_radius']['responses']['128']['finite']['optical_points'][0]
    shallow = sensitivity['shallower_electron_well']['responses']['128']['finite']['optical_points'][0]
    assert shallow['gamma_gap_eV'] < finite['gamma_gap_eV'] < smaller['gamma_gap_eV']
    assert sensitivity['shallower_electron_well']['responses']['128']['infinite'] == baseline['infinite']


def test_unbound_case_has_no_finite_optical_result(study):
    case = study['physical_sensitivity']['unbound_hole']
    assert case['carrier_outcomes']['electron']['status'] == 'bound'
    assert case['carrier_outcomes']['hole']['status'] == 'no_bound_state'
    assert case['finite_status'] == 'unavailable'
    assert case['finite_context_hash'] is None
    assert case['responses']['128']['finite'] is None
    assert case['responses']['128']['infinite'] is not None


def test_strict_json_and_content_hash(study):
    assert json.loads(json.dumps(study, allow_nan=False)) == study
    payload = {key: value for key, value in study.items() if key != 'study_hash'}
    assert study['study_hash'] == canonical_hash(payload)
