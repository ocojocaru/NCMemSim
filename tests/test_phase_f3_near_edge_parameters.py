from __future__ import annotations

import pytest

from ncmemsim.materials.optics import (
    GeSnNearEdgeParameterSet,
    TRAN_2016_NEAR_EDGE_PARAMETERS,
)
from ncmemsim.materials.provenance import ParameterStatus


def test_tran_near_edge_parameter_set_identity():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    assert isinstance(params, GeSnNearEdgeParameterSet)
    assert params.name == "gesn-near-edge-tran2016-v1"


def test_tran_direct_prefactor_value():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    assert params.direct_prefactor_A == pytest.approx(3.68e6)


def test_tran_urbach_width_value():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    assert params.urbach_energy_eV == pytest.approx(0.01058)


def test_tran_reference_temperature():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    assert params.temperature_K == pytest.approx(300.0)


def test_tran_direct_prefactor_provenance():
    provenance = TRAN_2016_NEAR_EDGE_PARAMETERS.provenance[
        "direct_prefactor_A"
    ]

    assert provenance.status is ParameterStatus.LITERATURE_FITTED
    assert provenance.doi == "10.1063/1.4943652"
    assert provenance.parameter_set == "gesn-near-edge-tran2016-v1"

    assert provenance.reported_uncertainty == pytest.approx(0.86e6)
    assert provenance.uncertainty_unit == "m^-1 eV^(1/2)"


def test_tran_urbach_width_provenance():
    provenance = TRAN_2016_NEAR_EDGE_PARAMETERS.provenance[
        "urbach_energy_eV"
    ]

    assert provenance.status is ParameterStatus.LITERATURE_FITTED
    assert provenance.doi == "10.1063/1.4943652"
    assert provenance.parameter_set == "gesn-near-edge-tran2016-v1"

    assert provenance.reported_uncertainty == pytest.approx(0.00106)
    assert provenance.uncertainty_unit == "eV"


def test_near_edge_parameter_values_must_be_positive():
    with pytest.raises(ValueError):
        GeSnNearEdgeParameterSet(
            direct_prefactor_A=0.0,
        )

    with pytest.raises(ValueError):
        GeSnNearEdgeParameterSet(
            urbach_energy_eV=0.0,
        )


def test_near_edge_temperature_must_be_positive():
    with pytest.raises(ValueError):
        GeSnNearEdgeParameterSet(
            temperature_K=0.0,
        )
