from __future__ import annotations
import math
from dataclasses import dataclass

def nanocrystal_volume_m3(
    nc_diameter_nm: float,
) -> float:
    """
    Volume of a spherical nanocrystal.
    """
    if nc_diameter_nm <= 0:
        raise ValueError("nc_diameter_nm must be positive.")

    diameter_m = nc_diameter_nm * 1.0e-9
    radius_m = diameter_m / 2.0

    return (
        4.0
        / 3.0
        * math.pi
        * radius_m**3
    )


def nanocrystal_number_density_m3(
    nc_diameter_nm: float,
    nc_volume_fraction: float,
) -> float:
    """
    Number density of monodisperse spherical nanocrystals.

    Returns NCs per cubic metre of composite floating-gate layer.
    """
    if not 0.0 <= nc_volume_fraction <= 1.0:
        raise ValueError(
            "nc_volume_fraction must be in [0, 1]."
        )

    if nc_volume_fraction == 0.0:
        return 0.0

    volume_nc = nanocrystal_volume_m3(
        nc_diameter_nm
    )

    return nc_volume_fraction / volume_nc


def absorbed_photon_rate_per_nc_s(
    average_generation_rate_m3_s: float,
    nc_diameter_nm: float,
    nc_volume_fraction: float,
) -> float:
    """
    Average absorbed-photon rate per physical nanocrystal.

    The generation rate is averaged over the full composite
    floating-gate volume.
    """
    if average_generation_rate_m3_s < 0:
        raise ValueError(
            "average_generation_rate_m3_s cannot be negative."
        )

    density = nanocrystal_number_density_m3(
        nc_diameter_nm=nc_diameter_nm,
        nc_volume_fraction=nc_volume_fraction,
    )

    if density == 0.0:
        return 0.0

    return average_generation_rate_m3_s / density


@dataclass(frozen=True)
class PhotoTransitionConfig:
    """
    Parameters controlling conversion of absorbed photons into
    photo-assisted nanocrystal state transitions.

    photo_capture_efficiency is an effective probability that an
    absorbed photon produces a useful transition event.
    """
    photo_capture_efficiency: float = 1.0e-3

    def __post_init__(self) -> None:
        if not 0.0 <= self.photo_capture_efficiency <= 1.0:
            raise ValueError(
                "photo_capture_efficiency must be in [0, 1]."
            )


def photo_transition_rate_s(
    absorbed_photon_rate_per_nc_s: float,
    config: PhotoTransitionConfig | None = None,
) -> float:
    """
    Effective photo-assisted transition rate per nanocrystal.
    """
    if absorbed_photon_rate_per_nc_s < 0:
        raise ValueError(
            "absorbed_photon_rate_per_nc_s cannot be negative."
        )

    cfg = config or PhotoTransitionConfig()

    return (
        cfg.photo_capture_efficiency
        * absorbed_photon_rate_per_nc_s
    )