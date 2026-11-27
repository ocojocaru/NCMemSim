# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Orthogonality, quadrature refinement and negative channel controls."""
from dataclasses import replace
import math

import pytest

from examples.phase_u4_coulomb_radial_coupling import radial_coupling, run_study
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from test_phase_t2_finite_confinement import _request


def test_radial_channel_orthogonality_and_refinement():
    state = evaluate_finite_confinement(_request(1., 6.)).to_dict()
    coarse = radial_coupling(state, state)
    fine = radial_coupling(state, state, tolerance=1e-12)
    assert abs(fine['overlap']) < 1e-10
    assert abs(fine['signed_coefficient']) > 1e-3
    assert coarse['signed_coefficient'] == pytest.approx(fine['signed_coefficient'], rel=1e-8)
    assert state['energy_J'] < fine['excited_energy_J'] < state['request']['depth_J']
    shallow = evaluate_finite_confinement(_request(1., math.pi)).to_dict()
    assert radial_coupling(shallow, state)['reason'] == 'no_bound_2s_state'
    unbound = evaluate_finite_confinement(replace(_request(1., 6.), depth_J=0.)).to_dict()
    assert radial_coupling(unbound, state)['reason'] == 'ground_state_unavailable'


def test_screening_changes_amplitude_and_second_order_energy():
    rows = {case['label']: case['channels'] for case in run_study()['cases']}
    for carrier in ('electron', 'hole'):
        base = rows['baseline'][carrier]
        screened = rows['weaker_screening'][carrier]
        assert base['status'] == 'evaluated'
        assert abs(base['overlap']) < 1e-10
        assert base['refinement_change'] < 1e-8
        assert base['second_order_energy_J'] < 0
        assert screened['first_order_amplitude_magnitude'] == pytest.approx(2*base['first_order_amplitude_magnitude'])
        assert screened['second_order_energy_J'] == pytest.approx(4*base['second_order_energy_J'], rel=1e-10, abs=0)
