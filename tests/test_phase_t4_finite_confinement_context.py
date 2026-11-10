# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Regression checks for source-bound finite optical composition."""
from dataclasses import replace
import math

import pytest

from examples.phase_t3_finite_confinement_reference import _baseline
from ncmemsim.constants import ELEMENTARY_CHARGE_C
from ncmemsim.finite_confinement_context import (
    FiniteConfinementOpticalBinding,
    FiniteConfinementOpticalContext,
)
from ncmemsim.materials import make_gesn
from ncmemsim.materials.temperature import GapKind
from ncmemsim.structural_optical_context import StructuralOpticalContext
from test_phase_o4_structural_optical_context import binding, resolution


def _binding(radius=4e-9):
    electron = replace(_baseline('electron', 0.2, 0.8), dot_material='Ge', radius_m=radius)
    hole = replace(_baseline('hole', 0.4, 0.15), dot_material='Ge', radius_m=radius)
    return FiniteConfinementOpticalBinding('FG1', GapKind.GAMMA, 'synthetic scalar hole', electron, hole)


def test_selected_term_replaced_and_evaluator_uses_resolved_gaps():
    owner = StructuralOpticalContext(resolution(), (binding(),))
    original = owner.projection['layers'][0]['targets']
    context = FiniteConfinementOpticalContext(owner, (_binding(),))
    targets = context.projection['layers'][0]['targets']
    gamma = targets[GapKind.GAMMA.value]
    result = gamma['confinement_result']
    shift = (result['electron']['energy_J'] + result['hole']['energy_J']) / ELEMENTARY_CHARGE_C
    assert 0 < shift < original[GapKind.GAMMA.value]['kinetic_confinement_gap_shift_eV']
    assert gamma['kinetic_confinement_gap_shift_eV'] == shift
    assert gamma['strain_gap_shift_eV'] == original[GapKind.GAMMA.value]['strain_gap_shift_eV']
    assert gamma['resolved_gap_eV'] == math.fsum((
        gamma['thermal_baseline_gap_eV'], gamma['strain_gap_shift_eV'], shift,
    ))
    assert targets[GapKind.L.value] == original[GapKind.L.value]
    material = owner.thermal_resolution.device.get_layer('FG1').nc_material
    point = context.optical_model('FG1').evaluate(material, 1550)
    assert point.direct_gap_eV == gamma['resolved_gap_eV']
    assert point.indirect_gap_eV == targets[GapKind.L.value]['resolved_gap_eV']
    assert owner.projection['layers'][0]['targets'] == original


def test_empty_bindings_preserve_legacy_projection_and_model():
    owner = StructuralOpticalContext(resolution(material=make_gesn(0.08)), ())
    context = FiniteConfinementOpticalContext(owner)
    assert context.projection == owner.projection
    assert context.optical_model('FG1') == owner.optical_model('FG1')
    with pytest.raises(ValueError, match='Ge material'):
        FiniteConfinementOpticalContext(owner, (_binding(),))


def test_rebuild_and_archive_tamper_detection():
    owner = StructuralOpticalContext(resolution(), ())
    context = FiniteConfinementOpticalContext(owner, (_binding(),))
    assert FiniteConfinementOpticalContext.from_json(context.to_json()) == context
    smaller = StructuralOpticalContext(resolution(diameter=4), ())
    with pytest.raises(ValueError, match='device radius'):
        replace(context, structural_context=smaller)
    rebuilt = FiniteConfinementOpticalContext(smaller, (_binding(2e-9),))
    assert rebuilt.contract_hash != context.contract_hash
    raw = context.to_dict()
    raw['bindings'][0]['hole'] = replace(_binding().hole, depth_J=1e-18).to_dict()
    with pytest.raises(ValueError):
        FiniteConfinementOpticalContext.from_dict(raw)


def test_unavailable_and_duplicate_targets_fail_closed():
    owner = StructuralOpticalContext(resolution(diameter=2), ())
    selected = _binding(1e-9)
    with pytest.raises(ValueError, match='electron=bound, hole=no_bound_state'):
        FiniteConfinementOpticalContext(owner, (selected,))
    with pytest.raises(ValueError, match='duplicate'):
        FiniteConfinementOpticalContext(owner, (selected, selected))
