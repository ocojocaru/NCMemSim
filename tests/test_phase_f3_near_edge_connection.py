from __future__ import annotations

import math

import pytest

from ncmemsim.materials.optics import (
    TRAN_2016_NEAR_EDGE_PARAMETERS,
)
from ncmemsim.materials.optics.near_edge import (
    NEAR_EDGE_CONTINUITY_PROVENANCE,
    NearEdgeConnection,
    derive_near_edge_connection,
    near_edge_direct_absorption_m_inv,
    near_edge_urbach_absorption_m_inv,
)
from ncmemsim.materials.provenance import ParameterStatus


def test_continuity_provenance_is_derived():
    provenance = NEAR_EDGE_CONTINUITY_PROVENANCE

    assert provenance.status is ParameterStatus.DERIVED
    assert provenance.doi is None
    assert (
        provenance.parameter_set
        == "gesn-near-edge-tran2016-v1"
    )


def test_connection_is_physically_ordered():
    connection = derive_near_edge_connection(
        direct_gap_eV=0.604,
    )

    assert isinstance(connection, NearEdgeConnection)
    assert connection.connection_offset_eV > 0.0
    assert connection.connection_energy_eV > connection.direct_gap_eV
    assert connection.urbach_prefactor_m_inv > 0.0


def test_connection_regression_value():
    connection = derive_near_edge_connection(
        direct_gap_eV=0.604,
    )

    assert connection.connection_offset_eV == pytest.approx(
        0.005199696622356279,
        rel=1e-12,
    )

    assert connection.connection_energy_eV == pytest.approx(
        0.6091996966223563,
        rel=1e-12,
    )

    assert connection.urbach_prefactor_m_inv == pytest.approx(
        266462.888709221,
        rel=1e-12,
    )


def test_connection_offset_approaches_half_urbach_width():
    connection = derive_near_edge_connection(
        direct_gap_eV=0.604,
    )

    half_width = (
        TRAN_2016_NEAR_EDGE_PARAMETERS.urbach_energy_eV / 2.0
    )

    assert connection.connection_offset_eV == pytest.approx(
        half_width,
        rel=0.02,
    )


def test_direct_and_urbach_values_are_continuous_at_connection():
    connection = derive_near_edge_connection(
        direct_gap_eV=0.604,
    )

    energy_eV = connection.connection_energy_eV

    alpha_direct = near_edge_direct_absorption_m_inv(
        photon_energy_eV=energy_eV,
        direct_gap_eV=connection.direct_gap_eV,
    )

    alpha_urbach = near_edge_urbach_absorption_m_inv(
        photon_energy_eV=energy_eV,
        direct_gap_eV=connection.direct_gap_eV,
    )

    assert alpha_direct == pytest.approx(
        alpha_urbach,
        rel=1e-12,
    )


def test_direct_and_urbach_first_derivatives_are_continuous():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    connection = derive_near_edge_connection(
        direct_gap_eV=0.604,
    )

    energy_eV = connection.connection_energy_eV
    y_eV = connection.connection_offset_eV

    alpha_direct = near_edge_direct_absorption_m_inv(
        photon_energy_eV=energy_eV,
        direct_gap_eV=connection.direct_gap_eV,
    )

    alpha_urbach = near_edge_urbach_absorption_m_inv(
        photon_energy_eV=energy_eV,
        direct_gap_eV=connection.direct_gap_eV,
    )

    direct_derivative = alpha_direct * (
        1.0 / (2.0 * y_eV)
        - 1.0 / energy_eV
    )

    urbach_derivative = (
        alpha_urbach / params.urbach_energy_eV
    )

    assert direct_derivative == pytest.approx(
        urbach_derivative,
        rel=1e-12,
    )


def test_direct_branch_matches_tran_equation():
    params = TRAN_2016_NEAR_EDGE_PARAMETERS

    direct_gap_eV = 0.604
    photon_energy_eV = 0.700

    expected = (
        params.direct_prefactor_A
        * math.sqrt(photon_energy_eV - direct_gap_eV)
        / photon_energy_eV
    )

    actual = near_edge_direct_absorption_m_inv(
        photon_energy_eV=photon_energy_eV,
        direct_gap_eV=direct_gap_eV,
    )

    assert actual == pytest.approx(expected)


def test_direct_branch_is_zero_at_and_below_gap():
    assert near_edge_direct_absorption_m_inv(
        photon_energy_eV=0.604,
        direct_gap_eV=0.604,
    ) == pytest.approx(0.0)

    assert near_edge_direct_absorption_m_inv(
        photon_energy_eV=0.600,
        direct_gap_eV=0.604,
    ) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "direct_gap_eV",
    [
        0.0,
        -0.1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_invalid_direct_gap_is_rejected(direct_gap_eV):
    with pytest.raises(ValueError):
        derive_near_edge_connection(
            direct_gap_eV=direct_gap_eV,
        )


@pytest.mark.parametrize(
    "photon_energy_eV",
    [
        0.0,
        -0.1,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_invalid_photon_energy_is_rejected(photon_energy_eV):
    with pytest.raises(ValueError):
        near_edge_direct_absorption_m_inv(
            photon_energy_eV=photon_energy_eV,
            direct_gap_eV=0.604,
        )

    with pytest.raises(ValueError):
        near_edge_urbach_absorption_m_inv(
            photon_energy_eV=photon_energy_eV,
            direct_gap_eV=0.604,
        )
