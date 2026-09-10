import math

import pytest

from ncmemsim.photo import (
    absorbed_photon_rate_per_nc_s,
    nanocrystal_number_density_m3,
    nanocrystal_volume_m3,
)


def test_nanocrystal_volume_matches_sphere_formula():
    diameter_nm = 5.0

    volume = nanocrystal_volume_m3(
        diameter_nm
    )

    expected = (
        4.0
        / 3.0
        * math.pi
        * (2.5e-9) ** 3
    )

    assert volume == pytest.approx(expected)


def test_nanocrystal_number_density():
    density = nanocrystal_number_density_m3(
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
    )

    volume_nc = nanocrystal_volume_m3(5.0)

    assert density == pytest.approx(
        0.60 / volume_nc
    )


def test_zero_volume_fraction_gives_zero_density():
    density = nanocrystal_number_density_m3(
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.0,
    )

    assert density == 0.0


def test_photon_rate_per_nc_matches_generation_over_density():
    generation = 3.0e28

    density = nanocrystal_number_density_m3(
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
    )

    rate = absorbed_photon_rate_per_nc_s(
        average_generation_rate_m3_s=generation,
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
    )

    assert rate == pytest.approx(
        generation / density
    )


def test_zero_generation_gives_zero_photon_rate():
    rate = absorbed_photon_rate_per_nc_s(
        average_generation_rate_m3_s=0.0,
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
    )

    assert rate == 0.0


def test_invalid_photo_rate_inputs_rejected():
    with pytest.raises(ValueError):
        nanocrystal_volume_m3(-5.0)

    with pytest.raises(ValueError):
        nanocrystal_number_density_m3(
            5.0,
            -0.1,
        )

    with pytest.raises(ValueError):
        nanocrystal_number_density_m3(
            5.0,
            1.1,
        )

    with pytest.raises(ValueError):
        absorbed_photon_rate_per_nc_s(
            average_generation_rate_m3_s=-1.0,
            nc_diameter_nm=5.0,
            nc_volume_fraction=0.60,
        )