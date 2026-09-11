from ncmemsim import DeviceBuilder, make_gesn
from ncmemsim.optics import (
    LightSource,
    evaluate_floating_gate_optical_absorption,
)
from ncmemsim.materials.optics import CompositeGeSnAbsorptionModel
from ncmemsim.photo import (
    PhotoTransitionConfig,
    evaluate_photo_transition_rates,
)


WAVELENGTHS_NM = [
    1000.0,
    1100.0,
    1200.0,
    1300.0,
    1400.0,
    1500.0,
    1550.0,
    1600.0,
    1700.0,
    1800.0,
    1900.0,
    2000.0,
    2200.0,
    2500.0,
]

SN_FRACTIONS = [
    0.00,
    0.04,
    0.08,
    0.12,
]

POWER_DENSITY_W_M2 = 1000.0
PHOTO_CAPTURE_EFFICIENCY = 1.0e-7


def make_fg(sn_fraction):
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


def main():
    optical_model = CompositeGeSnAbsorptionModel()

    print()
    print("NCMemSim E6a SWIR wavelength sweep")
    print("=" * 150)
    print(
        f"Power density = {POWER_DENSITY_W_M2:.1f} W/m^2, "
        f"eta_photo = {PHOTO_CAPTURE_EFFICIENCY:.1e}"
    )
    print()

    header = (
        f"{'Sn':>5} "
        f"{'lambda':>7} "
        f"{'Eph':>8} "
        f"{'EgG':>8} "
        f"{'EgL':>8} "
        f"{'a_dir':>11} "
        f"{'a_ind':>11} "
        f"{'a_U':>11} "
        f"{'a_NC':>11} "
        f"{'a_eff':>11} "
        f"{'A':>9} "
        f"{'Phi_inc':>11} "
        f"{'Phi_abs':>11} "
        f"{'Gavg':>11} "
        f"{'RgamNC':>11} "
        f"{'Rphoto':>11}"
    )

    print(header)
    print("-" * len(header))

    for sn_fraction in SN_FRACTIONS:
        fg = make_fg(sn_fraction)

        for wavelength_nm in WAVELENGTHS_NM:
            source = LightSource.laser(
                wavelength_nm=wavelength_nm,
                power_density_W_m2=POWER_DENSITY_W_M2,
            )

            optical = evaluate_floating_gate_optical_absorption(
                source,
                fg,
                optical_model=optical_model,
            )

            photo = evaluate_photo_transition_rates(
                optical,
                fg,
                config=PhotoTransitionConfig(
                    photo_capture_efficiency=PHOTO_CAPTURE_EFFICIENCY,
                ),
            )

            print(
                f"{sn_fraction:5.2f} "
                f"{wavelength_nm:7.0f} "
                f"{optical.photon_energy_eV:8.4f} "
                f"{optical.direct_gap_eV:8.4f} "
                f"{optical.indirect_gap_eV:8.4f} "
                f"{optical.alpha_direct_m_inv:11.3e} "
                f"{optical.alpha_indirect_m_inv:11.3e} "
                f"{optical.alpha_urbach_m_inv:11.3e} "
                f"{optical.nc_absorption_coefficient_m_inv:11.3e} "
                f"{optical.effective_absorption_coefficient_m_inv:11.3e} "
                f"{optical.absorption_fraction:9.3e} "
                f"{optical.incident_photon_flux_m2_s:11.3e} "
                f"{optical.absorbed_photon_flux_m2_s:11.3e} "
                f"{optical.average_generation_rate_m3_s:11.3e} "
                f"{photo.absorbed_photon_rate_per_nc_s:11.3e} "
                f"{photo.base_photo_transition_rate_s:11.3e}"
            )

        print()


if __name__ == "__main__":
    main()