import math
import pytest

from ncmemsim.materials import HFO2, make_ge
from ncmemsim.layers import FloatingGateLayer
from ncmemsim.optics import (
    absorbed_photon_flux,
    beer_lambert_absorption_fraction,
    effective_nc_absorption_coefficient,
    floating_gate_absorbed_photon_flux,
)


def test_zero_absorption_coefficient_gives_zero_absorption():
    fraction = beer_lambert_absorption_fraction(
        absorption_coefficient_m_inv=0.0,
        thickness_m=10e-9,
    )

    assert fraction == 0.0


def test_zero_thickness_gives_zero_absorption():
    fraction = beer_lambert_absorption_fraction(
        absorption_coefficient_m_inv=1.0e6,
        thickness_m=0.0,
    )

    assert fraction == 0.0


def test_beer_lambert_matches_analytic_expression():
    alpha = 1.0e6
    thickness = 100e-9

    fraction = beer_lambert_absorption_fraction(
        alpha,
        thickness,
    )

    expected = 1.0 - math.exp(-alpha * thickness)

    assert fraction == pytest.approx(
        expected,
        rel=1e-14,
    )


def test_absorbed_plus_transmitted_equals_incident():
    result = absorbed_photon_flux(
        incident_flux_m2_s=1.0e20,
        absorption_coefficient_m_inv=1.0e6,
        thickness_m=100e-9,
    )

    assert (
        result.absorbed_flux_m2_s
        + result.transmitted_flux_m2_s
    ) == pytest.approx(
        result.incident_flux_m2_s,
        rel=1e-14,
    )


def test_absorption_increases_with_thickness():
    thin = beer_lambert_absorption_fraction(
        1.0e6,
        10e-9,
    )

    thick = beer_lambert_absorption_fraction(
        1.0e6,
        100e-9,
    )

    assert thick > thin


def test_invalid_beer_lambert_inputs_rejected():
    with pytest.raises(ValueError):
        beer_lambert_absorption_fraction(
            -1.0,
            10e-9,
        )

    with pytest.raises(ValueError):
        beer_lambert_absorption_fraction(
            1.0,
            -10e-9,
        )

        
def make_test_fg(
    volume_fraction: float = 0.60,
    thickness_nm: float = 15.0,
):
    return FloatingGateLayer(
        name="FG",
        matrix_material=HFO2,
        thickness_nm=thickness_nm,
        nc_material=make_ge(),
        nc_diameter_nm=5.0,
        nc_volume_fraction=volume_fraction,
        electrically_active_fraction=1.0,
        grid_points=7,
    )
    
    
def test_effective_absorption_scales_with_nc_volume_fraction():
    alpha_nc = 1.0e6

    alpha_eff = effective_nc_absorption_coefficient(
        alpha_nc,
        0.60,
    )

    assert alpha_eff == pytest.approx(6.0e5)


def test_zero_nc_fraction_gives_zero_effective_absorption():
    assert effective_nc_absorption_coefficient(
        1.0e6,
        0.0,
    ) == 0.0


def test_pure_nc_limit_recovers_bulk_absorption():
    alpha_nc = 1.0e6

    assert effective_nc_absorption_coefficient(
        alpha_nc,
        1.0,
    ) == pytest.approx(alpha_nc)


def test_invalid_nc_volume_fraction_rejected():
    with pytest.raises(ValueError):
        effective_nc_absorption_coefficient(
            1.0e6,
            -0.1,
        )

    with pytest.raises(ValueError):
        effective_nc_absorption_coefficient(
            1.0e6,
            1.1,
        )


def test_floating_gate_absorption_uses_layer_thickness():
    layer = make_test_fg(
        volume_fraction=0.60,
        thickness_nm=15.0,
    )

    result = floating_gate_absorbed_photon_flux(
        incident_flux_m2_s=1.0e20,
        nc_absorption_coefficient_m_inv=1.0e6,
        layer=layer,
    )

    expected_fraction = 1.0 - math.exp(
        -(0.60 * 1.0e6) * 15.0e-9
    )

    assert result.absorption_fraction == pytest.approx(
        expected_fraction,
        rel=1e-14,
    )


def test_electrically_active_fraction_does_not_change_optical_absorption():
    layer_all_active = make_test_fg()
    layer_partly_active = FloatingGateLayer(
        name="FG",
        matrix_material=HFO2,
        thickness_nm=15.0,
        nc_material=make_ge(),
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
        electrically_active_fraction=0.20,
        grid_points=7,
    )

    result_all = floating_gate_absorbed_photon_flux(
        1.0e20,
        1.0e6,
        layer_all_active,
    )

    result_partial = floating_gate_absorbed_photon_flux(
        1.0e20,
        1.0e6,
        layer_partly_active,
    )

    assert result_partial.absorbed_flux_m2_s == pytest.approx(
        result_all.absorbed_flux_m2_s
    )