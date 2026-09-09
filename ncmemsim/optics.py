from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constants import (
    ELEMENTARY_CHARGE_C,
    LIGHT_SPEED_M_S,
    PLANCK_J_S,
)


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
