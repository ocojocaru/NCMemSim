from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import math

from .constants import (
    ELEMENTARY_CHARGE_C,
    LIGHT_SPEED_M_S,
    PLANCK_J_S,
)

from .materials.optics import CompositeGeSnAbsorptionModel


@dataclass(frozen=True)
class LightSource:
    """Description of an optical source incident on the simulated device."""

    name: str
    source_type: str
    power_density_W_m2: float
    enabled: bool = True
    spectrum_mode: str = "compact"

    temperature_K: float | None = None
    wavelength_nm: float | None = None
    wavelength_min_nm: float | None = None
    wavelength_max_nm: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.power_density_W_m2 < 0:
            raise ValueError("power_density_W_m2 cannot be negative")

        if self.source_type not in {
            "incandescent",
            "led",
            "laser",
            "custom",
        }:
            raise ValueError(f"Unsupported optical source type: {self.source_type}")

        if self.source_type == "incandescent":
            if self.temperature_K is None or self.temperature_K <= 0:
                raise ValueError(
                    "A positive temperature_K is required for an incandescent source."
                )

        if self.source_type in {"led", "laser"}:
            if self.wavelength_nm is None or self.wavelength_nm <= 0:
                raise ValueError(
                    f"A positive wavelength_nm is required for a {self.source_type} source."
                )

        if self.wavelength_min_nm is not None and self.wavelength_min_nm <= 0:
            raise ValueError("wavelength_min_nm must be positive")

        if self.wavelength_max_nm is not None and self.wavelength_max_nm <= 0:
            raise ValueError("wavelength_max_nm must be positive")

        if (
            self.wavelength_min_nm is not None
            and self.wavelength_max_nm is not None
            and self.wavelength_max_nm <= self.wavelength_min_nm
        ):
            raise ValueError(
                "wavelength_max_nm must be greater than wavelength_min_nm"
            )

    @property
    def is_monochromatic(self) -> bool:
        return self.source_type in {"led", "laser"} and self.wavelength_nm is not None

    @property
    def photon_energy_J(self) -> float:
        """Photon energy for a monochromatic source."""
        if not self.is_monochromatic:
            raise ValueError(
                "A single photon energy is only defined for a monochromatic source."
            )

        wavelength_m = self.wavelength_nm * 1e-9
        return PLANCK_J_S * LIGHT_SPEED_M_S / wavelength_m

    @property
    def photon_energy_eV(self) -> float:
        """Photon energy in electronvolts for a monochromatic source."""
        return self.photon_energy_J / ELEMENTARY_CHARGE_C

    @property
    def photon_flux_m2_s(self) -> float:
        """Incident photon flux for a monochromatic source, photons/(m² s)."""
        if not self.enabled:
            return 0.0

        return self.power_density_W_m2 / self.photon_energy_J

    @classmethod
    def incandescent(
        cls,
        power_density_W_m2: float,
        temperature_K: float = 2800.0,
        wavelength_min_nm: float = 350.0,
        wavelength_max_nm: float = 2500.0,
        name: str = "Incandescent lamp",
        spectrum_mode: str = "compact",
    ) -> LightSource:
        return cls(
            name=name,
            source_type="incandescent",
            power_density_W_m2=power_density_W_m2,
            enabled=True,
            spectrum_mode=spectrum_mode,
            temperature_K=temperature_K,
            wavelength_min_nm=wavelength_min_nm,
            wavelength_max_nm=wavelength_max_nm,
        )

    @classmethod
    def led(
        cls,
        wavelength_nm: float,
        power_density_W_m2: float,
        name: str | None = None,
    ) -> LightSource:
        return cls(
            name=name or f"LED {wavelength_nm:g} nm",
            source_type="led",
            power_density_W_m2=power_density_W_m2,
            wavelength_nm=wavelength_nm,
        )

    @classmethod
    def laser(
        cls,
        wavelength_nm: float,
        power_density_W_m2: float,
        name: str | None = None,
    ) -> LightSource:
        return cls(
            name=name or f"Laser {wavelength_nm:g} nm",
            source_type="laser",
            power_density_W_m2=power_density_W_m2,
            wavelength_nm=wavelength_nm,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

@dataclass(frozen=True)
class AbsorbedPhotonFlux:
    incident_flux_m2_s: float
    absorbed_flux_m2_s: float
    transmitted_flux_m2_s: float
    absorption_fraction: float
    transmission_fraction: float
    absorption_coefficient_m_inv: float
    thickness_m: float
    
    @property
    def average_generation_rate_m3_s(self) -> float:
        """
        Average volumetric absorbed-photon generation rate.

        This is the number of absorbed photons per unit volume and
        time. It does not imply unit quantum efficiency for carrier
        generation or charge storage.
        """
        if self.thickness_m <= 0:
            return 0.0

        return self.absorbed_flux_m2_s / self.thickness_m

    def __post_init__(self) -> None:
        if self.incident_flux_m2_s < 0:
            raise ValueError("incident_flux_m2_s cannot be negative.")

        if self.absorbed_flux_m2_s < 0:
            raise ValueError("absorbed_flux_m2_s cannot be negative.")

        if self.transmitted_flux_m2_s < 0:
            raise ValueError("transmitted_flux_m2_s cannot be negative.")

        if not 0.0 <= self.absorption_fraction <= 1.0:
            raise ValueError("absorption_fraction must be in [0, 1].")

        if not 0.0 <= self.transmission_fraction <= 1.0:
            raise ValueError("transmission_fraction must be in [0, 1].")

def beer_lambert_absorption_fraction(
    absorption_coefficient_m_inv: float,
    thickness_m: float,
) -> float:
    if absorption_coefficient_m_inv < 0:
        raise ValueError(
            "absorption_coefficient_m_inv cannot be negative."
        )

    if thickness_m < 0:
        raise ValueError("thickness_m cannot be negative.")

    optical_depth = (
        absorption_coefficient_m_inv * thickness_m
    )

    return -math.expm1(-optical_depth)


def absorbed_photon_flux(
    incident_flux_m2_s: float,
    absorption_coefficient_m_inv: float,
    thickness_m: float,
) -> AbsorbedPhotonFlux:
    if incident_flux_m2_s < 0:
        raise ValueError("incident_flux_m2_s cannot be negative.")

    absorption_fraction = beer_lambert_absorption_fraction(
        absorption_coefficient_m_inv,
        thickness_m,
    )

    transmission_fraction = 1.0 - absorption_fraction

    absorbed = (
        incident_flux_m2_s * absorption_fraction
    )

    transmitted = (
        incident_flux_m2_s * transmission_fraction
    )

    return AbsorbedPhotonFlux(
        incident_flux_m2_s=incident_flux_m2_s,
        absorbed_flux_m2_s=absorbed,
        transmitted_flux_m2_s=transmitted,
        absorption_fraction=absorption_fraction,
        transmission_fraction=transmission_fraction,
        absorption_coefficient_m_inv=absorption_coefficient_m_inv,
        thickness_m=thickness_m,
    )
    
def effective_nc_absorption_coefficient(
    nc_absorption_coefficient_m_inv: float,
    nc_volume_fraction: float,
) -> float:
    """
    First-order effective absorption coefficient for a nanocrystal
    composite layer.

    The matrix is assumed optically transparent and scattering is
    neglected.
    """
    if nc_absorption_coefficient_m_inv < 0:
        raise ValueError(
            "nc_absorption_coefficient_m_inv cannot be negative."
        )

    if not 0.0 <= nc_volume_fraction <= 1.0:
        raise ValueError(
            "nc_volume_fraction must be in [0, 1]."
        )

    return (
        nc_volume_fraction
        * nc_absorption_coefficient_m_inv
    )

def floating_gate_absorbed_photon_flux(
    incident_flux_m2_s: float,
    nc_absorption_coefficient_m_inv: float,
    layer,
) -> AbsorbedPhotonFlux:
    """
    Compute absorbed photon flux in a FloatingGateLayer using a
    first-order volume-fraction effective absorption coefficient.
    """
    layer.validate()

    alpha_eff = effective_nc_absorption_coefficient(
        nc_absorption_coefficient_m_inv,
        layer.nc_volume_fraction,
    )

    thickness_m = layer.thickness_nm * 1.0e-9

    return absorbed_photon_flux(
        incident_flux_m2_s=incident_flux_m2_s,
        absorption_coefficient_m_inv=alpha_eff,
        thickness_m=thickness_m,
    )
    
@dataclass(frozen=True)
class FloatingGateOpticalResult:
    source_name: str
    wavelength_nm: float
    photon_energy_eV: float

    incident_power_density_W_m2: float
    incident_photon_flux_m2_s: float
    average_generation_rate_m3_s: float

    nc_absorption_coefficient_m_inv: float
    effective_absorption_coefficient_m_inv: float

    absorption_fraction: float
    absorbed_photon_flux_m2_s: float
    transmitted_photon_flux_m2_s: float

    alpha_direct_m_inv: float | None = None
    alpha_indirect_m_inv: float | None = None
    alpha_urbach_m_inv: float | None = None

    direct_gap_eV: float | None = None
    indirect_gap_eV: float | None = None

    provenance: Any = None
    
def evaluate_floating_gate_optical_absorption(
    source: LightSource,
    layer,
    optical_model: CompositeGeSnAbsorptionModel | None = None,
) -> FloatingGateOpticalResult:
    """
    End-to-end monochromatic optical absorption evaluation for a
    nanocrystal floating-gate layer.
    """
    if not source.is_monochromatic:
        raise ValueError(
            "End-to-end floating-gate optical evaluation currently "
            "requires a monochromatic LED or laser source."
        )

    layer.validate()

    model = optical_model or CompositeGeSnAbsorptionModel()

    optical_point = model.evaluate(
        layer.nc_material,
        source.wavelength_nm,
    )

    alpha_nc = optical_point.absorption_coefficient_m_inv

    alpha_eff = effective_nc_absorption_coefficient(
        alpha_nc,
        layer.nc_volume_fraction,
    )

    flux_result = floating_gate_absorbed_photon_flux(
        incident_flux_m2_s=source.photon_flux_m2_s,
        nc_absorption_coefficient_m_inv=alpha_nc,
        layer=layer,
    )

    return FloatingGateOpticalResult(
        source_name=source.name,
        wavelength_nm=source.wavelength_nm,
        photon_energy_eV=source.photon_energy_eV,
        incident_power_density_W_m2=source.power_density_W_m2,
        incident_photon_flux_m2_s=source.photon_flux_m2_s,
        nc_absorption_coefficient_m_inv=alpha_nc,
        effective_absorption_coefficient_m_inv=alpha_eff,
        average_generation_rate_m3_s=flux_result.average_generation_rate_m3_s,
        absorption_fraction=flux_result.absorption_fraction,
        absorbed_photon_flux_m2_s=flux_result.absorbed_flux_m2_s,
        transmitted_photon_flux_m2_s=flux_result.transmitted_flux_m2_s,
        alpha_direct_m_inv=optical_point.alpha_direct_m_inv,
        alpha_indirect_m_inv=optical_point.alpha_indirect_m_inv,
        alpha_urbach_m_inv=optical_point.alpha_urbach_m_inv,
        direct_gap_eV=optical_point.direct_gap_eV,
        indirect_gap_eV=optical_point.indirect_gap_eV,
        provenance=optical_point.provenance,
    )
