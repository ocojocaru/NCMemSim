from __future__ import annotations

import math

import pytest

from ncmemsim import make_gesn
from ncmemsim.constants import (
    ELEMENTARY_CHARGE_C,
    LIGHT_SPEED_M_S,
    PLANCK_J_S,
)
from ncmemsim.materials.optics import (
    EvaluationDomainStatus,
    GeSnNearEdgeParameterSet,
    GeSnNearEdgeReferenceModel,
    NearEdgeBranch,
    direct_gap_gesn_eV,
)
from ncmemsim.materials.optics.near_edge import (
    derive_near_edge_connection,
    near_edge_direct_absorption_m_inv,
)
from ncmemsim.materials.provenance import ParameterStatus


def _wavelength_nm_from_energy_eV(energy_eV: float) -> float:
    return (
        PLANCK_J_S
        * LIGHT_SPEED_M_S
        / (energy_eV * ELEMENTARY_CHARGE_C)
        * 1.0e9
    )


def test_direct_gap_red_shifts_monotonically_over_tran_compositions():
    sn_fractions = [
        0.00,
        0.02,
        0.04,
        0.06,
        0.08,
        0.10,
    ]

    gaps = [
        direct_gap_gesn_eV(sn_fraction)
        for sn_fraction in sn_fractions
    ]

    assert gaps[0] == pytest.approx(0.7985)
    assert gaps[-1] == pytest.approx(0.41725)

    assert all(
        next_gap < gap
        for gap, next_gap in zip(gaps, gaps[1:])
    )


def test_reference_model_is_finite_and_nonnegative_over_tran_domain():
    model = GeSnNearEdgeReferenceModel()

    sn_fractions = [
        0.00,
        0.02,
        0.04,
        0.06,
        0.08,
        0.10,
    ]

    wavelengths_nm = [
        1500.0,
        1750.0,
        2000.0,
        2250.0,
        2500.0,
    ]

    for sn_fraction in sn_fractions:
        material = make_gesn(sn_fraction)

        for wavelength_nm in wavelengths_nm:
            point = model.evaluate(
                material,
                wavelength_nm=wavelength_nm,
            )

            assert math.isfinite(
                point.absorption_coefficient_m_inv
            )

            assert point.absorption_coefficient_m_inv >= 0.0

            assert math.isfinite(point.direct_gap_eV)
            assert point.direct_gap_eV > 0.0

            assert math.isfinite(
                point.connection_energy_eV
            )

            assert (
                point.connection_energy_eV
                > point.direct_gap_eV
            )

            assert (
                point.domain_status
                is EvaluationDomainStatus.WITHIN_VALIDATION_DOMAIN
            )


def test_reference_model_contains_both_branches_in_tran_domain():
    model = GeSnNearEdgeReferenceModel()
    material = make_gesn(0.0)

    short_wavelength_point = model.evaluate(
        material,
        wavelength_nm=1500.0,
    )

    long_wavelength_point = model.evaluate(
        material,
        wavelength_nm=1600.0,
    )

    assert (
        short_wavelength_point.branch
        is NearEdgeBranch.DIRECT
    )

    assert (
        long_wavelength_point.branch
        is NearEdgeBranch.URBACH
    )


def test_model_switch_is_continuous_across_connection():
    model = GeSnNearEdgeReferenceModel()
    material = make_gesn(0.0)

    direct_gap_eV = direct_gap_gesn_eV(
        material.sn_fraction,
    )

    connection = derive_near_edge_connection(
        direct_gap_eV=direct_gap_eV,
    )

    energy_offset_eV = 1.0e-7

    energy_below_eV = (
        connection.connection_energy_eV
        - energy_offset_eV
    )

    energy_above_eV = (
        connection.connection_energy_eV
        + energy_offset_eV
    )

    wavelength_below_nm = _wavelength_nm_from_energy_eV(
        energy_below_eV
    )

    wavelength_above_nm = _wavelength_nm_from_energy_eV(
        energy_above_eV
    )

    point_below = model.evaluate(
        material,
        wavelength_nm=wavelength_below_nm,
    )

    point_above = model.evaluate(
        material,
        wavelength_nm=wavelength_above_nm,
    )

    assert point_below.branch is NearEdgeBranch.URBACH
    assert point_above.branch is NearEdgeBranch.DIRECT

    alpha_at_connection = near_edge_direct_absorption_m_inv(
        photon_energy_eV=connection.connection_energy_eV,
        direct_gap_eV=direct_gap_eV,
    )

    assert point_below.absorption_coefficient_m_inv == pytest.approx(
        alpha_at_connection,
        rel=2.0e-5,
    )

    assert point_above.absorption_coefficient_m_inv == pytest.approx(
        alpha_at_connection,
        rel=2.0e-5,
    )


def test_connection_for_pure_ge_lies_inside_tran_wavelength_domain():
    direct_gap_eV = direct_gap_gesn_eV(0.0)

    connection = derive_near_edge_connection(
        direct_gap_eV=direct_gap_eV,
    )

    connection_wavelength_nm = _wavelength_nm_from_energy_eV(
        connection.connection_energy_eV
    )

    assert 1500.0 < connection_wavelength_nm < 1600.0


def test_custom_parameters_do_not_inherit_tran_fitted_provenance():
    custom_parameters = GeSnNearEdgeParameterSet(
        name="custom-near-edge-test",
        direct_prefactor_A=4.0e6,
        urbach_energy_eV=0.011,
    )

    model = GeSnNearEdgeReferenceModel(
        parameters=custom_parameters,
    )

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    assert (
        point.provenance["direct_prefactor_A"].status
        is ParameterStatus.ASSUMED
    )

    assert (
        point.provenance["urbach_energy_eV"].status
        is ParameterStatus.ASSUMED
    )

    assert (
        point.provenance["continuity"].status
        is ParameterStatus.DERIVED
    )


def test_reference_model_does_not_claim_calibrated_parameter_status():
    model = GeSnNearEdgeReferenceModel()

    point = model.evaluate(
        make_gesn(0.05),
        wavelength_nm=2000.0,
    )

    statuses = {
        provenance.status
        for provenance in point.provenance.values()
    }

    assert ParameterStatus.CALIBRATED not in statuses
    assert ParameterStatus.FITTED not in statuses
