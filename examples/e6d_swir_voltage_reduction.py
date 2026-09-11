from __future__ import annotations

import numpy as np

from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    PhysicsModel,
    Simulator,
    SimulationConfig,
    make_gesn,
)
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionConfig


# ---------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------

POWER_DENSITY_W_M2 = 1000.0

# Benchmark-only coupling chosen so that dark and illuminated
# programming curves overlap within the 0-4 V voltage window.
#
# This is NOT an experimentally calibrated photo-capture efficiency.
PHOTO_CAPTURE_EFFICIENCY = 1.0e-10

WAVELENGTHS_NM = (
    1300.0,
    1550.0,
    1700.0,
)

VOLTAGES_V = np.linspace(
    0.0,
    4.0,
    17,
)

DWELL_TIME_S = 1.0e-3
INTERNAL_DT_S = 1.0e-5


def make_simulator():
    device = DeviceBuilder.v1(
        n_fgs=1,
        nc_material=[make_gesn(0.08)],
        nc_diameter_nm=[5.0],
        active_fraction=[1.0],
        fg_thickness_nm=[15.0],
    )

    fg = device.floating_gates()[0]
    fg.grid_points = 7

    physics = PhysicsModel.default()

    sim = Simulator(
        device,
        physics,
        SimulationConfig(
            dwell_time_s=DWELL_TIME_S,
            internal_dt_s=INTERNAL_DT_S,
        ),
    )

    return device, sim


def make_light(wavelength_nm: float) -> LightSource:
    return LightSource.laser(
        wavelength_nm=wavelength_nm,
        power_density_W_m2=POWER_DENSITY_W_M2,
    )


def make_photo_config() -> PhotoTransitionConfig:
    return PhotoTransitionConfig(
        photo_capture_efficiency=PHOTO_CAPTURE_EFFICIENCY,
    )


def occupation_curve(
    sim,
    device,
    wavelength_nm: float | None = None,
):
    occupations = []
    photo_rates = []
    absorbed_fluxes = []

    light_source = (
        None
        if wavelength_nm is None
        else make_light(wavelength_nm)
    )

    for voltage_V in VOLTAGES_V:
        state = DeviceState.empty_for_device(device)

        out = sim.relax_voltage(
            state,
            gate_voltage_V=float(voltage_V),
            light_source=light_source,
            photo_config=make_photo_config(),
        )

        occupations.append(
            out["mean_occupation"]
        )

        photo_rates.append(
            out["photo_transition_rate_s"]
        )

        absorbed_fluxes.append(
            out["absorbed_photon_flux_m2_s"]
        )

    return {
        "occupation": np.asarray(
            occupations,
            dtype=float,
        ),
        "photo_rate": np.asarray(
            photo_rates,
            dtype=float,
        ),
        "absorbed_flux": np.asarray(
            absorbed_fluxes,
            dtype=float,
        ),
    }


def common_target_occupation(
    dark_occupation,
    *light_occupations,
):
    
    curves = (
        dark_occupation,
        *light_occupations,
    )
    
    lower = max(
        np.min(curve)
        for curve in curves
    )

    upper = min(
        np.max(curve)
        for curve in curves
    )

    if upper <= lower:
        raise ValueError(
            "Dark and illuminated occupation curves "
            "do not share a common overlap range."
        )

    return 0.5 * (lower + upper)

def required_voltage_for_occupation(
    occupations,
    target_occupation,
):
    order = np.argsort(occupations)

    occupation_sorted = occupations[order]
    voltage_sorted = VOLTAGES_V[order]

    return float(
        np.interp(
            target_occupation,
            occupation_sorted,
            voltage_sorted,
        )
    )


def main():
    device, sim = make_simulator()

    dark = occupation_curve(
        sim,
        device,
        wavelength_nm=None,
    )

    print()
    print("NCMemSim E6d - SWIR voltage-reduction benchmark")
    print("=" * 78)

    print(
        f"GeSn composition       : 8% Sn"
    )
    print(
        f"NC diameter            : 5 nm"
    )
    print(
        f"FG thickness           : 15 nm"
    )
    print(
        f"Optical power density  : "
        f"{POWER_DENSITY_W_M2:.1f} W/m^2"
    )
    print(
        f"Photo capture eta      : "
        f"{PHOTO_CAPTURE_EFFICIENCY:.1e}"
    )
    print(
        f"Programming time       : "
        f"{DWELL_TIME_S:.1e} s"
    )
    print(
        f"Voltage range          : "
        f"{VOLTAGES_V[0]:.2f} to "
        f"{VOLTAGES_V[-1]:.2f} V"
    )

    print()
    print(
        "NOTE: eta_photo is a benchmark coupling parameter; "
        "it is not experimentally calibrated."
    )

    print()
    print(
        f"{'lambda':>8s} "
        f"{'R_photo':>13s} "
        f"{'Phi_abs':>13s} "
        f"{'target occ.':>13s} "
        f"{'V_dark':>9s} "
        f"{'V_light':>9s} "
        f"{'DeltaV':>9s}"
    )

    print(
        f"{'(nm)':>8s} "
        f"{'(s^-1)':>13s} "
        f"{'(m^-2 s^-1)':>13s} "
        f"{'':>13s} "
        f"{'(V)':>9s} "
        f"{'(V)':>9s} "
        f"{'(V)':>9s}"
    )

    print("-" * 93)

    results = []

    illuminated = {}

    for wavelength_nm in WAVELENGTHS_NM:
        illuminated[wavelength_nm] = occupation_curve(
            sim,
            device,
            wavelength_nm=wavelength_nm,
        )

    target = common_target_occupation(
        dark["occupation"],
        *[
            illuminated[wavelength_nm]["occupation"]
            for wavelength_nm in WAVELENGTHS_NM
        ],
    )

    for wavelength_nm in WAVELENGTHS_NM:
        light = illuminated[wavelength_nm]

        v_dark = required_voltage_for_occupation(
            dark["occupation"],
            target,
        )

        v_light = required_voltage_for_occupation(
            light["occupation"],
            target,
        )

        delta_v = v_dark - v_light

        photo_rate = float(
            np.mean(light["photo_rate"])
        )

        absorbed_flux = float(
            np.mean(light["absorbed_flux"])
        )

        results.append(
            {
                "wavelength_nm": wavelength_nm,
                "photo_rate_s": photo_rate,
                "absorbed_flux_m2_s": absorbed_flux,
                "target_occupation": target,
                "v_dark_V": v_dark,
                "v_light_V": v_light,
                "delta_v_V": delta_v,
            }
        )

        print(
            f"{wavelength_nm:8.0f} "
            f"{photo_rate:13.6e} "
            f"{absorbed_flux:13.6e} "
            f"{target:13.6e} "
            f"{v_dark:9.4f} "
            f"{v_light:9.4f} "
            f"{delta_v:9.4f}"
        )

    print()
    print("Spectral ranking by photo-transition rate:")

    by_photo_rate = sorted(
        results,
        key=lambda item: item["photo_rate_s"],
        reverse=True,
    )

    for rank, item in enumerate(
        by_photo_rate,
        start=1,
    ):
        print(
            f"  {rank}. "
            f"{item['wavelength_nm']:.0f} nm  "
            f"R_photo={item['photo_rate_s']:.6e} s^-1"
        )

    print()
    print("Spectral ranking by voltage reduction:")

    by_delta_v = sorted(
        results,
        key=lambda item: item["delta_v_V"],
        reverse=True,
    )

    for rank, item in enumerate(
        by_delta_v,
        start=1,
    ):
        print(
            f"  {rank}. "
            f"{item['wavelength_nm']:.0f} nm  "
            f"DeltaV={item['delta_v_V']:.6f} V"
        )

    print()
    print(
        "Interpretation: positive DeltaV means that SWIR "
        "illumination reduces the gate voltage required to "
        "reach the selected occupation."
    )

    print(
        "These values demonstrate the behavior of the compact "
        "model and must not be interpreted as experimentally "
        "calibrated predictions."
    )


if __name__ == "__main__":
    main()