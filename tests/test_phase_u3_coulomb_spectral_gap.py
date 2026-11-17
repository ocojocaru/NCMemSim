# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Check excitation matching and the total-L=0 gap in the U3 controls."""
import math

import pytest
from scipy.special import spherical_jn, spherical_kn

from examples.phase_u3_coulomb_spectral_gap import first_excitation, run_study
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from test_phase_t2_finite_confinement import _request


@pytest.mark.parametrize('rho', [3.0, 4.0, 12.0])
def test_first_excitation_boundary_matching(rho):
    state = evaluate_finite_confinement(_request(1., rho)).to_dict()
    result = first_excitation(state)
    if rho < math.pi:
        assert result == {'channel': 'continuum_threshold', 'energy_J': state['request']['depth_J']}
    else:
        x = result['x']
        y = math.sqrt((rho-x)*(rho+x))
        assert result['channel'] == 'l1_bound'
        assert state['energy_J'] < result['energy_J'] < state['request']['depth_J']
        assert x*spherical_jn(1, x, derivative=True)/spherical_jn(1, x) == pytest.approx(
            y*spherical_kn(1, y, derivative=True)/spherical_kn(1, y), abs=1e-11,
        )


def test_pair_gaps_and_unavailable_case():
    rows = {row['label']: row for row in run_study()['cases']}
    reference = rows['baseline']
    assert reference['shift_to_min_continuum_separation'] < 1 < reference['shift_to_pair_spectral_gap']
    assert reference['pair_spectral_gap_J'] < reference['total_L0_gap_J']
    assert reference['shift_to_min_continuum_separation'] <= reference['shift_to_total_L0_gap']
    assert rows['weaker_screening']['shift_to_total_L0_gap'] == pytest.approx(
        2*reference['shift_to_total_L0_gap'],
    )
    assert rows['unbound_hole']['total_L0_gap_J'] is None
