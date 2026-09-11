import numpy as np
import pytest

from ncmemsim import (
    DeviceBuilder,
    make_gesn,
)
from ncmemsim.optics import (
    LightSource,
    evaluate_floating_gate_optical_absorption,
)
from ncmemsim.materials.optics import (
    CompositeGeSnAbsorptionModel,
    photon_energy_eV,
)
from ncmemsim.photo import (
    PhotoTransitionConfig,
    evaluate_photo_transition_rates,
)


WAVELENGTHS_NM = np.array(
    [1000.0, 1300.0, 1550.0, 1700.0, 2000.0]
)

POWER_DENSITY_W_M2 = 1000.0


def make_fg(sn_fraction=0.08):
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(sn_fraction)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )

    fg = device.floating_gates()[0]
    fg.grid_points = 7

    return fg


def evaluate_wavelength(
    wavelength_nm,
    sn_fraction=0.08,
    power_density_W_m2=POWER_DENSITY_W_M2,
    photo_capture_efficiency=1.0e-7,
):
    fg = make_fg(sn_fraction)

    source = LightSource.laser(
        wavelength_nm=float(wavelength_nm),
        power_density_W_m2=power_density_W_m2,
    )

    optical_model = CompositeGeSnAbsorptionModel()

    optical = evaluate_floating_gate_optical_absorption(
        source,
        fg,
        optical_model=optical_model,
    )

    photo = evaluate_photo_transition_rates(
        optical,
        fg,
        config=PhotoTransitionConfig(
            photo_capture_efficiency=photo_capture_efficiency,
        ),
    )

    return source, optical, photo


def test_photon_energy_decreases_with_wavelength():
    energies = np.asarray(
        [
            photon_energy_eV(wavelength)
            for wavelength in WAVELENGTHS_NM
        ]
    )

    assert np.all(energies > 0.0)
    assert np.all(np.diff(energies) < 0.0)


def test_absorption_coefficient_is_nonnegative_across_swir():
    alpha = []

    for wavelength in WAVELENGTHS_NM:
        _, optical, _ = evaluate_wavelength(wavelength)

        alpha.append(
            optical.nc_absorption_coefficient_m_inv
        )

    alpha = np.asarray(alpha)

    assert np.all(np.isfinite(alpha))
    assert np.all(alpha >= 0.0)


def test_incident_photon_flux_increases_with_wavelength_at_fixed_power():
    flux = []

    for wavelength in WAVELENGTHS_NM:
        source, _, _ = evaluate_wavelength(wavelength)

        flux.append(source.photon_flux_m2_s)

    flux = np.asarray(flux)

    assert np.all(flux > 0.0)
    assert np.all(np.diff(flux) > 0.0)


def test_absorbed_photon_flux_and_photo_rate_are_nonnegative():
    absorbed_flux = []
    photo_rates = []

    for wavelength in WAVELENGTHS_NM:
        _, optical, photo = evaluate_wavelength(wavelength)

        absorbed_flux.append(
            optical.absorbed_photon_flux_m2_s
        )

        photo_rates.append(
            photo.base_photo_transition_rate_s
        )

    absorbed_flux = np.asarray(absorbed_flux)
    photo_rates = np.asarray(photo_rates)

    assert np.all(np.isfinite(absorbed_flux))
    assert np.all(np.isfinite(photo_rates))

    assert np.all(absorbed_flux >= 0.0)
    assert np.all(photo_rates >= 0.0)


def test_higher_sn_extends_absorption_toward_longer_wavelength():
    wavelength_nm = 2000.0

    _, optical_ge, _ = evaluate_wavelength(
        wavelength_nm,
        sn_fraction=0.0,
    )

    _, optical_gesn, _ = evaluate_wavelength(
        wavelength_nm,
        sn_fraction=0.08,
    )

    assert (
        optical_gesn.nc_absorption_coefficient_m_inv
        >
        optical_ge.nc_absorption_coefficient_m_inv
    )


def test_photo_rate_matches_capture_efficiency_across_wavelength_sweep():
    eta = 1.0e-7

    for wavelength in WAVELENGTHS_NM:
        _, _, photo = evaluate_wavelength(
            wavelength,
            photo_capture_efficiency=eta,
        )

        assert photo.base_photo_transition_rate_s == pytest.approx(
            eta
            * photo.absorbed_photon_rate_per_nc_s
        )