"""Controlled local sensitivity contracts for Phase J5 transport validation.

The analysis is deliberately local and one-at-a-time.  It records normalized
secants around one declared operating context; it is not a fitted covariance,
global sensitivity index, manufacturing distribution or calibration result.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from typing import Any

from ..hashing import canonical_hash
from .barrier_corrections import (
    ImageForceBarrierSpec,
    evaluate_trap_assisted_transport_with_barrier_correction,
)
from .traps import TrapAssistedTransportSpec, TrapSpecies


class TransportSensitivityParameter(str, Enum):
    """Parameters audited by the first J5 local sensitivity contract."""

    ENERGY_DEPTH_J = "energy_depth_J"
    DENSITY_M3 = "density_m3"
    CAPTURE_CROSS_SECTION_M2 = "capture_cross_section_m2"
    ATTEMPT_FREQUENCY_HZ = "attempt_frequency_Hz"
    IMAGE_FORCE_RELATIVE_PERMITTIVITY = "image_force_relative_permittivity"


class TransportIdentifiabilityStatus(str, Enum):
    """Interpretation of one local rate sensitivity."""

    LOCALLY_INFORMATIVE = "locally_informative"
    STRUCTURALLY_CONFOUNDED = "structurally_confounded"
    NONPOSITIVE_RESPONSE = "nonpositive_response"


_UNITS = {
    TransportSensitivityParameter.ENERGY_DEPTH_J: "J",
    TransportSensitivityParameter.DENSITY_M3: "m^-3",
    TransportSensitivityParameter.CAPTURE_CROSS_SECTION_M2: "m^2",
    TransportSensitivityParameter.ATTEMPT_FREQUENCY_HZ: "Hz",
    TransportSensitivityParameter.IMAGE_FORCE_RELATIVE_PERMITTIVITY: "1",
}


@dataclass(frozen=True)
class TransportSensitivityEntry:
    """One dimensionless log-secant with its three evaluated rates."""

    parameter: TransportSensitivityParameter
    unit: str
    lower_value: float
    nominal_value: float
    upper_value: float
    lower_rate_Hz: float
    nominal_rate_Hz: float
    upper_rate_Hz: float
    normalized_log_secant: float | None
    identifiability_status: TransportIdentifiabilityStatus
    confounded_group: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.parameter, TransportSensitivityParameter):
            raise TypeError("parameter must be TransportSensitivityParameter")
        if self.unit != _UNITS[self.parameter]:
            raise ValueError("unit does not match sensitivity parameter")
        for field in ("lower_value", "nominal_value", "upper_value"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{field} must be finite and strictly positive")
            object.__setattr__(self, field, value)
        if not self.lower_value < self.nominal_value < self.upper_value:
            raise ValueError("sensitivity values must strictly bracket nominal")
        for field in ("lower_rate_Hz", "nominal_rate_Hz", "upper_rate_Hz"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{field} must be finite and nonnegative")
            object.__setattr__(self, field, value)
        if self.normalized_log_secant is not None:
            slope = float(self.normalized_log_secant)
            if not math.isfinite(slope):
                raise ValueError("normalized_log_secant must be finite or None")
            object.__setattr__(self, "normalized_log_secant", slope)
        if not isinstance(self.identifiability_status, TransportIdentifiabilityStatus):
            raise TypeError("identifiability_status must be TransportIdentifiabilityStatus")
        if self.identifiability_status is TransportIdentifiabilityStatus.STRUCTURALLY_CONFOUNDED:
            if type(self.confounded_group) is not str or not self.confounded_group:
                raise ValueError("structurally confounded entries require a group")
        elif self.confounded_group is not None:
            raise ValueError("only structurally confounded entries may name a group")

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter.value,
            "unit": self.unit,
            "lower_value": self.lower_value,
            "nominal_value": self.nominal_value,
            "upper_value": self.upper_value,
            "lower_rate_Hz": self.lower_rate_Hz,
            "nominal_rate_Hz": self.nominal_rate_Hz,
            "upper_rate_Hz": self.upper_rate_Hz,
            "normalized_log_secant": self.normalized_log_secant,
            "identifiability_status": self.identifiability_status.value,
            "confounded_group": self.confounded_group,
        }


@dataclass(frozen=True)
class TransportSensitivityResult:
    """Immutable audit of one-species local TAT rate sensitivity."""

    tat_configuration_hash: str
    correction_configuration_hash: str
    link_length_m: float
    electric_field_V_m: float
    effective_mass_m0: float
    relative_step: float
    entries: tuple[TransportSensitivityEntry, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("tat_configuration_hash", "correction_configuration_hash"):
            value = getattr(self, field)
            if type(value) is not str or len(value) != 64:
                raise ValueError(f"{field} must be a SHA-256 digest")
        length = float(self.link_length_m)
        field = float(self.electric_field_V_m)
        mass = float(self.effective_mass_m0)
        step = float(self.relative_step)
        if not math.isfinite(length) or length <= 0.0:
            raise ValueError("link_length_m must be finite and positive")
        if not math.isfinite(field):
            raise ValueError("electric_field_V_m must be finite")
        if not math.isfinite(mass) or mass <= 0.0:
            raise ValueError("effective_mass_m0 must be finite and positive")
        if not math.isfinite(step) or not 0.0 < step < 1.0:
            raise ValueError("relative_step must lie strictly between zero and one")
        object.__setattr__(self, "link_length_m", length)
        object.__setattr__(self, "electric_field_V_m", field)
        object.__setattr__(self, "effective_mass_m0", mass)
        object.__setattr__(self, "relative_step", step)
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "limitations", tuple(self.limitations))
        if not self.entries:
            raise ValueError("sensitivity result requires entries")
        parameters = [entry.parameter for entry in self.entries]
        if len(parameters) != len(set(parameters)):
            raise ValueError("sensitivity parameters must be unique")
        if not self.limitations or any(
            type(item) is not str or not item or item != item.strip()
            for item in self.limitations
        ):
            raise ValueError("limitations must contain nonempty text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "transport-local-sensitivity-v1",
            "tat_configuration_hash": self.tat_configuration_hash,
            "correction_configuration_hash": self.correction_configuration_hash,
            "context": {
                "link_length_m": self.link_length_m,
                "electric_field_V_m": self.electric_field_V_m,
                "effective_mass_m0": self.effective_mass_m0,
                "relative_step": self.relative_step,
            },
            "entries": [entry.to_dict() for entry in self.entries],
            "limitations": list(self.limitations),
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _rate(
    specification: TrapAssistedTransportSpec,
    correction: ImageForceBarrierSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> float:
    return evaluate_trap_assisted_transport_with_barrier_correction(
        specification,
        correction,
        link_length_m=link_length_m,
        electric_field_V_m=electric_field_V_m,
        effective_mass_m0=effective_mass_m0,
    ).total_rate_Hz


def analyze_tat_local_sensitivity(
    specification: TrapAssistedTransportSpec,
    correction: ImageForceBarrierSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
    relative_step: float = 0.10,
) -> TransportSensitivityResult:
    """Evaluate deterministic one-at-a-time normalized rate secants.

    The initial contract requires one enabled positive-density species.  A
    multi-species aggregate cannot attribute a local response uniquely and is
    rejected instead of returning a misleading sensitivity.
    """

    if not isinstance(specification, TrapAssistedTransportSpec):
        raise TypeError("specification must be TrapAssistedTransportSpec")
    if not isinstance(correction, ImageForceBarrierSpec):
        raise TypeError("correction must be ImageForceBarrierSpec")
    if not specification.enabled or len(specification.species) != 1:
        raise ValueError("J5 local sensitivity requires one enabled trap species")
    step = float(relative_step)
    if not math.isfinite(step) or not 0.0 < step < 1.0:
        raise ValueError("relative_step must lie strictly between zero and one")

    species = specification.species[0]
    nominal_rate = _rate(
        specification,
        correction,
        link_length_m=link_length_m,
        electric_field_V_m=electric_field_V_m,
        effective_mass_m0=effective_mass_m0,
    )
    parameters = [
        TransportSensitivityParameter.ENERGY_DEPTH_J,
        TransportSensitivityParameter.DENSITY_M3,
        TransportSensitivityParameter.CAPTURE_CROSS_SECTION_M2,
        TransportSensitivityParameter.ATTEMPT_FREQUENCY_HZ,
    ]
    if correction.enabled:
        parameters.append(
            TransportSensitivityParameter.IMAGE_FORCE_RELATIVE_PERMITTIVITY
        )

    entries = []
    active_group = "density_m3*capture_cross_section_m2*link_length_m"
    for parameter in parameters:
        if parameter is TransportSensitivityParameter.IMAGE_FORCE_RELATIVE_PERMITTIVITY:
            nominal_value = correction.relative_permittivity
        else:
            nominal_value = float(getattr(species, parameter.value))
        lower_value = nominal_value * (1.0 - step)
        upper_value = nominal_value * (1.0 + step)

        def evaluated(value: float) -> float:
            if parameter is TransportSensitivityParameter.IMAGE_FORCE_RELATIVE_PERMITTIVITY:
                changed_correction = replace(correction, relative_permittivity=value)
                changed_specification = specification
            else:
                changed_species: TrapSpecies = replace(species, **{parameter.value: value})
                changed_specification = replace(specification, species=(changed_species,))
                changed_correction = correction
            return _rate(
                changed_specification,
                changed_correction,
                link_length_m=link_length_m,
                electric_field_V_m=electric_field_V_m,
                effective_mass_m0=effective_mass_m0,
            )

        lower_rate = evaluated(lower_value)
        upper_rate = evaluated(upper_value)
        if min(lower_rate, nominal_rate, upper_rate) <= 0.0:
            slope = None
            status = TransportIdentifiabilityStatus.NONPOSITIVE_RESPONSE
            group = None
        else:
            slope = math.log(upper_rate / lower_rate) / math.log(
                upper_value / lower_value
            )
            if parameter in {
                TransportSensitivityParameter.DENSITY_M3,
                TransportSensitivityParameter.CAPTURE_CROSS_SECTION_M2,
            }:
                status = TransportIdentifiabilityStatus.STRUCTURALLY_CONFOUNDED
                group = active_group
            else:
                status = TransportIdentifiabilityStatus.LOCALLY_INFORMATIVE
                group = None
        entries.append(
            TransportSensitivityEntry(
                parameter,
                _UNITS[parameter],
                lower_value,
                nominal_value,
                upper_value,
                lower_rate,
                nominal_rate,
                upper_rate,
                slope,
                status,
                group,
            )
        )

    return TransportSensitivityResult(
        specification.configuration_hash,
        correction.configuration_hash,
        link_length_m,
        electric_field_V_m,
        effective_mass_m0,
        step,
        tuple(entries),
        (
            "Local one-at-a-time secants do not establish global sensitivity.",
            "Trap density and capture cross section are structurally confounded through active optical depth.",
            "A conditional compact rate does not identify a fabricated-device defect population.",
            "No entry is an experimental calibration or manufacturing-yield estimate.",
        ),
    )


__all__ = [
    "TransportSensitivityParameter",
    "TransportIdentifiabilityStatus",
    "TransportSensitivityEntry",
    "TransportSensitivityResult",
    "analyze_tat_local_sensitivity",
]
