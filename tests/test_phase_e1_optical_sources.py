import math

import pytest

from ncmemsim import LightSource


def test_laser_photon_energy_at_1240_nm():
    source = LightSource.laser(
        wavelength_nm=1240.0,
        power_density_W_m2=100.0,
    )

    assert math.isclose(source.photon_energy_eV, 1.0, rel_tol=2e-3)


def test_monochromatic_photon_flux():
    source = LightSource.laser(
        wavelength_nm=1240.0,
        power_density_W_m2=100.0,
    )

    expected = source.power_density_W_m2 / source.photon_energy_J

    assert math.isclose(
        source.photon_flux_m2_s,
        expected,
        rel_tol=1e-14,
    )


def test_disabled_source_has_zero_photon_flux():
    source = LightSource(
        name="disabled laser",
        source_type="laser",
        power_density_W_m2=100.0,
        enabled=False,
        wavelength_nm=1300.0,
    )

    assert source.photon_flux_m2_s == 0.0


def test_negative_power_is_rejected():
    with pytest.raises(ValueError):
        LightSource.laser(
            wavelength_nm=1300.0,
            power_density_W_m2=-1.0,
        )


def test_invalid_wavelength_is_rejected():
    with pytest.raises(ValueError):
        LightSource.laser(
            wavelength_nm=0.0,
            power_density_W_m2=100.0,
        )


def test_broadband_source_has_no_single_photon_energy():
    source = LightSource.incandescent(
        power_density_W_m2=100.0,
    )

    with pytest.raises(ValueError):
        _ = source.photon_energy_J