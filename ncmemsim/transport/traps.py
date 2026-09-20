"""Immutable trap contracts for the opt-in Phase J transport models.

J1 defines configuration, units and provenance only.  It intentionally does
not evaluate a trap-assisted rate or alter the existing transport engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from typing import Any

from ..hashing import canonical_hash


class TrapCarrier(str, Enum):
    """Carrier supported by a trap population."""

    ELECTRON = "electron"


class TrapEnergyReference(str, Enum):
    """Reference and sign convention for the trap energy."""

    CONDUCTION_BAND_DEPTH = "conduction_band_depth"


class TrapParameterStatus(str, Enum):
    """Evidence status of the supplied trap parameters."""

    ASSUMED = "assumed"
    LITERATURE = "literature"
    FITTED = "fitted"
    CALIBRATED = "calibrated"


class TrapAssistedModel(str, Enum):
    """Selected compact model family; numerical evaluation starts in J2."""

    SEQUENTIAL_TWO_STEP_WKB = "sequential_two_step_wkb"


def _text(value: Any, field: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field} must be nonempty text without outer whitespace")


def _number(value: Any, field: str, *, allow_zero: bool) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric, excluding bool")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    if result < 0 or (not allow_zero and result == 0):
        relation = "nonnegative" if allow_zero else "strictly positive"
        raise ValueError(f"{field} must be {relation}")
    return result


@dataclass(frozen=True)
class TrapSpecies:
    """One homogeneous electron-trap population in canonical SI units.

    ``energy_depth_J`` is ``E_C - E_trap`` and is therefore strictly positive
    for a localized level below the local conduction-band edge.  J1 supports
    volume density only.  ``position_fraction`` is the representative trap
    position measured from the source end of the directed link and lies in
    ``(0, 1)``.  Cross section and attempt frequency are recorded for the
    selected J2 kinetic contract; J1 does not consume them.
    """

    name: str
    energy_depth_J: float
    position_fraction: float
    density_m3: float
    capture_cross_section_m2: float
    attempt_frequency_Hz: float
    parameter_status: TrapParameterStatus
    source: str
    applicability: str
    carrier: TrapCarrier = TrapCarrier.ELECTRON
    energy_reference: TrapEnergyReference = TrapEnergyReference.CONDUCTION_BAND_DEPTH

    def __post_init__(self) -> None:
        for field in ("name", "source", "applicability"):
            _text(getattr(self, field), field)
        object.__setattr__(self, "energy_depth_J", _number(
            self.energy_depth_J, "energy_depth_J", allow_zero=False
        ))
        object.__setattr__(self, "position_fraction", _number(
            self.position_fraction, "position_fraction", allow_zero=False
        ))
        if self.position_fraction >= 1:
            raise ValueError("position_fraction must lie strictly between 0 and 1")
        object.__setattr__(self, "density_m3", _number(
            self.density_m3, "density_m3", allow_zero=True
        ))
        object.__setattr__(self, "capture_cross_section_m2", _number(
            self.capture_cross_section_m2, "capture_cross_section_m2", allow_zero=False
        ))
        object.__setattr__(self, "attempt_frequency_Hz", _number(
            self.attempt_frequency_Hz, "attempt_frequency_Hz", allow_zero=False
        ))
        if not isinstance(self.parameter_status, TrapParameterStatus):
            raise TypeError("parameter_status must be TrapParameterStatus")
        if not isinstance(self.carrier, TrapCarrier):
            raise TypeError("carrier must be TrapCarrier")
        if not isinstance(self.energy_reference, TrapEnergyReference):
            raise TypeError("energy_reference must be TrapEnergyReference")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "name": self.name,
            "energy_depth_J": self.energy_depth_J,
            "position_fraction": self.position_fraction,
            "density_m3": self.density_m3,
            "capture_cross_section_m2": self.capture_cross_section_m2,
            "attempt_frequency_Hz": self.attempt_frequency_Hz,
            "parameter_status": self.parameter_status.value,
            "source": self.source,
            "applicability": self.applicability,
            "carrier": self.carrier.value,
            "energy_reference": self.energy_reference.value,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TrapSpecies":
        if type(value) is not dict or set(value) != {
            "schema_version", "name", "energy_depth_J", "position_fraction", "density_m3",
            "capture_cross_section_m2", "attempt_frequency_Hz",
            "parameter_status", "source", "applicability", "carrier",
            "energy_reference",
        } or value.get("schema_version") != 1:
            raise ValueError("unsupported trap-species schema")
        return cls(
            name=value["name"],
            energy_depth_J=value["energy_depth_J"],
            position_fraction=value["position_fraction"],
            density_m3=value["density_m3"],
            capture_cross_section_m2=value["capture_cross_section_m2"],
            attempt_frequency_Hz=value["attempt_frequency_Hz"],
            parameter_status=TrapParameterStatus(value["parameter_status"]),
            source=value["source"],
            applicability=value["applicability"],
            carrier=TrapCarrier(value["carrier"]),
            energy_reference=TrapEnergyReference(value["energy_reference"]),
        )

    @property
    def species_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class TrapAssistedTransportSpec:
    """Opt-in configuration for the first compact TAT implementation.

    The specification is inert in J1.  Enabling it only validates that a
    positive-density population is present; engine integration starts in J4.
    """

    enabled: bool = False
    species: tuple[TrapSpecies, ...] = ()
    model: TrapAssistedModel = TrapAssistedModel.SEQUENTIAL_TWO_STEP_WKB

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be bool")
        if type(self.species) is not tuple or any(
            not isinstance(item, TrapSpecies) for item in self.species
        ):
            raise TypeError("species must be a tuple of TrapSpecies")
        if not isinstance(self.model, TrapAssistedModel):
            raise TypeError("model must be TrapAssistedModel")
        names = [item.name for item in self.species]
        if len(names) != len(set(names)):
            raise ValueError("trap species names must be unique")
        if self.enabled and not any(item.density_m3 > 0 for item in self.species):
            raise ValueError("enabled TAT requires a positive-density trap species")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "enabled": self.enabled,
            "model": self.model.value,
            "species": [item.to_dict() for item in self.species],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TrapAssistedTransportSpec":
        if type(value) is not dict or set(value) != {
            "schema_version", "enabled", "model", "species"
        } or value.get("schema_version") != 1:
            raise ValueError("unsupported trap-assisted transport schema")
        if type(value["species"]) is not list:
            raise TypeError("species must be a JSON array")
        return cls(
            enabled=value["enabled"],
            model=TrapAssistedModel(value["model"]),
            species=tuple(TrapSpecies.from_dict(item) for item in value["species"]),
        )

    @property
    def configuration_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_json(self) -> str:
        value = {**self.to_dict(), "configuration_hash": self.configuration_hash}
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_json(cls, value: str) -> "TrapAssistedTransportSpec":
        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, item in items:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = item
            return result

        def constant(value: str) -> None:
            raise ValueError(f"non-finite JSON constant: {value}")

        data = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
        if type(data) is not dict or "configuration_hash" not in data:
            raise ValueError("configuration_hash is required")
        digest = data.pop("configuration_hash")
        result = cls.from_dict(data)
        if type(digest) is not str or digest != result.configuration_hash:
            raise ValueError("trap-assisted configuration hash mismatch")
        return result


__all__ = [
    "TrapCarrier",
    "TrapEnergyReference",
    "TrapParameterStatus",
    "TrapAssistedModel",
    "TrapSpecies",
    "TrapAssistedTransportSpec",
]
