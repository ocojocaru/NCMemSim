from __future__ import annotations

import math

import pytest

from ncmemsim import make_gesn
from ncmemsim.materials.optics import (
    EvaluationDomainStatus,
    GeSnNearEdgeReferenceModel,
    NearEdgeBranch,
    NearEdgeOpticalPoint,
    TRAN_2016_NEAR_EDGE_DOMAIN,
    TRAN_2016_NEAR_EDGE_PARAMETERS,
    direct_gap_gesn_eV,
)
from ncmemsim.materials.optics.near_edge import (
    derive_near_edge_connection,
    near_edge_direct_absorption_m_inv,
    near_edge_urbach_absorption_m_inv,
)
from ncmemsim.materials.provenance import ParameterStatus


def test_near_edge_branch_values():
    assert NearEdgeBranch.URBACH.value == "urbach"
    assert NearEdgeBranch.DIRECT.value == "direct"


def test_reference_model_uses_tran_defaults():
    model = GeSnNearEdgeReferenceModel()

    assert model.parameters is TRAN_2016_NEAR_EDGE_PARAMETERS
    assert model.validation_domain is TRAN_2016_NEAR_EDGE_DOMAIN


def test_reference_model_returns_near_edge_point():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    assert isinstance(point, NearEdgeOpticalPoint)
    assert point.wavelength_nm == pytest.approx(2000.0)
    assert point.photon_energy_eV > 0.0
    assert math.isfinite(point.absorption_coefficient_m_inv)
    assert point.absorption_coefficient_m_inv >= 0.0


def test_direct_gap_uses_existing_ncmemsim_parameterization():
    model = GeSnNearEdgeReferenceModel()
    material = make_gesn(0.10)

    point = model.evaluate(
        material,
        wavelength_nm=1500.0,
    )

    expected_gap = direct_gap_gesn_eV(0.10)

    assert point.direct_gap_eV == pytest.approx(expected_gap)


def test_direct_branch_selected_above_connection():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.10),
        wavelength_nm=1500.0,
    )

    assert point.branch is NearEdgeBranch.DIRECT
    assert (
        point.photon_energy_eV
        >= point.connection_energy_eV
    )

    expected = near_edge_direct_absorption_m_inv(
        photon_energy_eV=point.photon_energy_eV,
        direct_gap_eV=point.direct_gap_eV,
    )

    assert point.absorption_coefficient_m_inv == pytest.approx(
        expected
    )


def test_urbach_branch_selected_below_connection():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.0),
        wavelength_nm=1600.0,
    )

    assert point.branch is NearEdgeBranch.URBACH
    assert (
        point.photon_energy_eV
        < point.connection_energy_eV
    )

    expected = near_edge_urbach_absorption_m_inv(
        photon_energy_eV=point.photon_energy_eV,
        direct_gap_eV=point.direct_gap_eV,
    )

    assert point.absorption_coefficient_m_inv == pytest.approx(
        expected
    )


def test_branch_switch_occurs_near_derived_connection():
    model = GeSnNearEdgeReferenceModel()
    material = make_gesn(0.0)

    point_1500 = model.evaluate(
        material,
        wavelength_nm=1500.0,
    )

    point_1600 = model.evaluate(
        material,
        wavelength_nm=1600.0,
    )

    assert point_1500.branch is NearEdgeBranch.DIRECT
    assert point_1600.branch is NearEdgeBranch.URBACH

    connection = derive_near_edge_connection(
        direct_gap_eV=direct_gap_gesn_eV(0.0),
    )

    assert point_1500.photon_energy_eV > (
        connection.connection_energy_eV
    )
    assert point_1600.photon_energy_eV < (
        connection.connection_energy_eV
    )


@pytest.mark.parametrize(
    ("sn_fraction", "wavelength_nm"),
    [
        (0.0, 1500.0),
        (0.05, 2000.0),
        (0.10, 2500.0),
    ],
)
def test_reference_model_marks_validated_domain(
    sn_fraction,
    wavelength_nm,
):
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(sn_fraction),
        wavelength_nm=wavelength_nm,
    )

    assert (
        point.domain_status
        is EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN
    )


@pytest.mark.parametrize(
    ("sn_fraction", "wavelength_nm"),
    [
        (0.15, 2000.0),
        (0.05, 1000.0),
        (0.05, 3000.0),
    ],
)
def test_reference_model_marks_extrapolation(
    sn_fraction,
    wavelength_nm,
):
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(sn_fraction),
        wavelength_nm=wavelength_nm,
    )

    assert (
        point.domain_status
        is EvaluationDomainStatus.EXTRAPOLATED
    )


def test_reference_point_records_connection_energy():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    connection = derive_near_edge_connection(
        direct_gap_eV=point.direct_gap_eV,
    )

    assert point.connection_energy_eV == pytest.approx(
        connection.connection_energy_eV
    )


def test_reference_point_provenance_is_explicit():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    assert (
        point.provenance["direct_gap"].status
        is ParameterStatus.LITERATURE
    )

    assert (
        point.provenance["direct_prefactor_A"].status
        is ParameterStatus.LITERATURE_FITTED
    )

    assert (
        point.provenance["urbach_energy_eV"].status
        is ParameterStatus.LITERATURE_FITTED
    )

    assert (
        point.provenance["continuity"].status
        is ParameterStatus.DERIVED
    )


def test_reference_model_has_no_indirect_absorption_component():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    assert not hasattr(point, "alpha_indirect_m_inv")


@pytest.mark.parametrize(
    "wavelength_nm",
    [
        0.0,
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ],
)
def test_reference_model_rejects_invalid_wavelength(
    wavelength_nm,
):
    model = GeSnNearEdgeReferenceModel()

    with pytest.raises(ValueError):
        model.evaluate(
            make_gesn(0.05),
            wavelength_nm=wavelength_nm,
        )
