# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Verify finite-well declarations at the archive and physical-unit boundaries."""
from dataclasses import replace

import pytest

from ncmemsim.materials.finite_confinement_contracts import (
    FiniteConfinementRequest, confinement_depth_eV_to_J,
)
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence


@pytest.fixture
def request_model():
    evidence = StructuralEvidence('T1 synthetic control', 'control inputs',
                                  ParameterStatus.ASSUMED, 'Illustrative sphere and host')
    return FiniteConfinementRequest(
        'hole', 'synthetic dot', 'synthetic host', 2e-9, .2, .4, 0., 300.,
        evidence, evidence, evidence, evidence, evidence,
    )


def test_zero_depth_and_carrier_energy_reference_round_trip(request_model):
    for carrier, edge in [('electron', 'dot_conduction_edge'), ('hole', 'dot_hole_edge')]:
        model = replace(request_model, carrier=carrier)
        raw = model.to_dict()
        assert raw['energy_reference'] == edge
        assert raw['depth_J'] == 0
        restored = FiniteConfinementRequest.from_json(model.to_json())
        assert restored.contract_hash == model.contract_hash
        raw['depth_evidence']['source'] = 'changed'
        raw['numerical_policy']['threshold_guard'] = 1.
        assert restored.to_dict() == model.to_dict()


@pytest.mark.parametrize('field,value', [
    ('inside_mass_m0', True), ('outside_mass_m0', 0), ('depth_J', -1),
    ('depth_J', float('inf')), ('radius_m', 0), ('temperature_K', float('nan')),
    ('carrier', 'ion'),
])
def test_invalid_physical_declarations(request_model, field, value):
    with pytest.raises(ValueError):
        replace(request_model, **{field: value})


@pytest.mark.parametrize('field,value', [
    ('energy_reference', 'dot_conduction_edge'), ('angular_momentum', False),
    ('interface', 'reduced_radial_derivative'), ('numerical_policy', {}),
    ('extra', 1),
])
def test_archive_rejects_altered_semantics(request_model, field, value):
    raw = request_model.to_dict()
    raw[field] = value
    with pytest.raises(ValueError):
        FiniteConfinementRequest.from_dict(raw)


def test_evidence_requires_units_of_the_archived_input(request_model):
    evidence = replace(request_model.depth_evidence, reported_uncertainty=.1,
                       uncertainty_unit='eV')
    with pytest.raises(ValueError, match='uncertainty unit'):
        replace(request_model, depth_evidence=evidence)


def test_explicit_depth_conversion_rejects_underflow():
    assert confinement_depth_eV_to_J(1) == 1.602176634e-19
    assert confinement_depth_eV_to_J(0) == 0
    for value in (-1, True, 5e-324):
        with pytest.raises(ValueError):
            confinement_depth_eV_to_J(value)
