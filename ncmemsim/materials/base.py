from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping
from .provenance import MaterialProperty

@dataclass(frozen=True)
class Material:
    name: str
    eps_r: float
    electron_affinity_eV: float | None = None
    bandgap_eV: float | None = None
    electron_effective_mass_m0: float | None = None
    hole_effective_mass_m0: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    properties: Mapping[str, MaterialProperty] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.eps_r <= 0:
            raise ValueError("eps_r must be positive")

    def property_manifest(self) -> dict[str, Any]:
        return {key: prop.to_dict() for key, prop in self.properties.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "eps_r": self.eps_r,
            "electron_affinity_eV": self.electron_affinity_eV,
            "bandgap_eV": self.bandgap_eV,
            "electron_effective_mass_m0": self.electron_effective_mass_m0,
            "hole_effective_mass_m0": self.hole_effective_mass_m0,
            "metadata": self.metadata,
            "properties": self.property_manifest(),
        }

@dataclass(frozen=True)
class NanocrystalMaterial:
    name: str
    sn_fraction: float
    eps_r_nc: float
    effective_mass_m0: float
    phi_barrier_prog_eV: float
    phi_barrier_erase_eV: float
    bandgap_eV: float | None = None
    electron_affinity_eV: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    properties: Mapping[str, MaterialProperty] = field(default_factory=dict)
    model_name: str = "NanocrystalMaterial"
    model_version: str = "default-v1"

    def __post_init__(self) -> None:
        if not 0 <= self.sn_fraction <= 1:
            raise ValueError("sn_fraction must be in [0,1]")
        vals=(self.eps_r_nc,self.effective_mass_m0,self.phi_barrier_prog_eV,self.phi_barrier_erase_eV)
        if min(vals) <= 0:
            raise ValueError("physical parameters must be positive")

    def property_manifest(self) -> dict[str, Any]:
        return {key: prop.to_dict() for key, prop in self.properties.items()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "sn_fraction": self.sn_fraction,
            "eps_r_nc": self.eps_r_nc,
            "effective_mass_m0": self.effective_mass_m0,
            "phi_barrier_prog_eV": self.phi_barrier_prog_eV,
            "phi_barrier_erase_eV": self.phi_barrier_erase_eV,
            "bandgap_eV": self.bandgap_eV,
            "electron_affinity_eV": self.electron_affinity_eV,
            "metadata": self.metadata,
            "properties": self.property_manifest(),
        }
