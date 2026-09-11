from __future__ import annotations

import math
from dataclasses import dataclass
import numpy as np

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

    
@dataclass(frozen=True)
class PhotoTransitionWeights:
    """
    Relative strengths of the photo-assisted occupancy transitions.

    Each weight scales the base photo-transition rate. Values are
    dimensionless and non-negative.

    The default represents photo-assisted electron loading:
        0 -> 1
        1 -> 2

    Photo-assisted detrapping channels are disabled by default.
    """

    r01: float = 1.0
    r12: float = 1.0
    r10: float = 0.0
    r21: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("r01", self.r01),
            ("r12", self.r12),
            ("r10", self.r10),
            ("r21", self.r21),
        ):
            if value < 0.0:
                raise ValueError(
                    f"{name} photo-transition weight cannot be negative."
                )
                
                
@dataclass(frozen=True)
class PhotoTransitionRates:
    r01: np.ndarray
    r12: np.ndarray
    r21: np.ndarray
    r10: np.ndarray
    

@dataclass(frozen=True)
class PhotoTransitionEvaluation:
    """
    Diagnostic result for photo-assisted occupancy transitions.
    """

    rates: PhotoTransitionRates
    absorbed_photon_rate_per_nc_s: float
    base_photo_transition_rate_s: float
    photo_capture_efficiency: float


def evaluate_photo_transition_rates(
    optical_result,
    layer,
    config: PhotoTransitionConfig | None = None,
    weights: PhotoTransitionWeights | None = None,
) -> PhotoTransitionEvaluation:
    """
    Evaluate photo-assisted transition rates together with
    physically useful diagnostics.
    """
    cfg = config or PhotoTransitionConfig()

    rate_per_nc = absorbed_photon_rate_per_nc_s(
        average_generation_rate_m3_s=(
            optical_result.average_generation_rate_m3_s
        ),
        nc_diameter_nm=layer.nc_diameter_nm,
        nc_volume_fraction=layer.nc_volume_fraction,
    )

    base_photo_rate = photo_transition_rate_s(
        absorbed_photon_rate_per_nc_s=rate_per_nc,
        config=cfg,
    )

    rates = photo_transition_rate_arrays(
        base_photo_rate_s=base_photo_rate,
        grid_size=layer.grid_points,
        weights=weights,
    )

    return PhotoTransitionEvaluation(
        rates=rates,
        absorbed_photon_rate_per_nc_s=rate_per_nc,
        base_photo_transition_rate_s=base_photo_rate,
        photo_capture_efficiency=cfg.photo_capture_efficiency,
    )
    
    
def photo_transition_rate_arrays(
    base_photo_rate_s: float,
    grid_size: int,
    weights: PhotoTransitionWeights | None = None,
) -> PhotoTransitionRates:
    """
    Build spatial photo-assisted transition-rate arrays.

    The compact E4 model assumes the average absorbed-photon rate
    is spatially uniform across the floating-gate layer.
    """
    if base_photo_rate_s < 0.0:
        raise ValueError(
            "base_photo_rate_s cannot be negative."
        )

    if grid_size < 1:
        raise ValueError(
            "grid_size must be at least 1."
        )

    w = weights or PhotoTransitionWeights()

    return PhotoTransitionRates(
        r01=np.full(grid_size, w.r01 * base_photo_rate_s),
        r12=np.full(grid_size, w.r12 * base_photo_rate_s),
        r21=np.full(grid_size, w.r21 * base_photo_rate_s),
        r10=np.full(grid_size, w.r10 * base_photo_rate_s),
    )
    

def photo_transition_rates_from_optical_result(
    optical_result,
    layer,
    config: PhotoTransitionConfig | None = None,
    weights: PhotoTransitionWeights | None = None,
) -> PhotoTransitionRates:
    """
    Convert a floating-gate optical absorption result into
    photo-assisted occupancy transition-rate arrays.
    """
    return evaluate_photo_transition_rates(
        optical_result,
        layer,
        config=config,
        weights=weights,
    ).rates