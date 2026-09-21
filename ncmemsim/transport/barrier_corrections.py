"""Opt-in compact barrier corrections for Phase J3.

The module applies the classical Schottky image-force peak lowering to the
source and destination interface heights of the isolated J2 TAT profile.  It
does not change the existing J2 evaluator or attach a mechanism to the
transport network.  The unmodified profile remains part of every diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from ..hashing import canonical_hash
from .tat import (
    ELEMENTARY_CHARGE_C,
    TATBarrierProfile,
    TATRateStatus,
    build_tat_barrier_profile,
    linear_wkb_transmission,
)
from .traps import TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies


VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12


class BarrierCorrectionStatus(str, Enum):
    """Outcome of one interface-height correction."""

    DISABLED = "disabled"
    ZERO_FIELD = "zero_field"
    APPLIED = "applied"
    BARRIER_SUPPRESSED = "barrier_suppressed"


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric, excluding bool")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _positive(value: Any, field: str) -> float:
    result = _finite(value, field)
    if result <= 0.0:
        raise ValueError(f"{field} must be strictly positive")
    return result


def _optional_text(value: Any, field: str) -> str:
    if type(value) is not str or value != value.strip():
        raise ValueError(f"{field} must be text without outer whitespace")
    return value


@dataclass(frozen=True)
class ImageForceBarrierSpec:
    """Configuration for the symmetric two-interface Schottky correction.

    ``relative_permittivity`` is the effective image-force permittivity, which
    is not silently equated with a static dielectric constant.  Enabled
    configurations require explicit provenance and applicability text.
    """

    enabled: bool = False
    relative_permittivity: float = 1.0
    parameter_status: TrapParameterStatus = TrapParameterStatus.ASSUMED
    source: str = ""
    applicability: str = ""

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise TypeError("enabled must be bool")
        object.__setattr__(self, "relative_permittivity", _positive(
            self.relative_permittivity, "relative_permittivity"
        ))
        if not isinstance(self.parameter_status, TrapParameterStatus):
            raise TypeError("parameter_status must be TrapParameterStatus")
        source = _optional_text(self.source, "source")
        applicability = _optional_text(self.applicability, "applicability")
        if self.enabled and (not source or not applicability):
            raise ValueError("enabled correction requires source and applicability")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "enabled": self.enabled,
            "relative_permittivity": self.relative_permittivity,
            "parameter_status": self.parameter_status.value,
            "source": self.source,
            "applicability": self.applicability,
        }

    @property
    def configuration_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class BarrierHeightCorrection:
    """One corrected interface height with its unmodified value retained."""

    unmodified_barrier_J: float
    lowering_J: float
    corrected_barrier_J: float
    status: BarrierCorrectionStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "unmodified_barrier_J": self.unmodified_barrier_J,
            "lowering_J": self.lowering_J,
            "corrected_barrier_J": self.corrected_barrier_J,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class CorrectedTATBarrierProfile:
    """Unmodified J2 profile plus explicit interface corrections."""

    unmodified_profile: TATBarrierProfile
    correction_configuration_hash: str
    source_interface: BarrierHeightCorrection
    destination_interface: BarrierHeightCorrection

    @property
    def corrected_profile(self) -> TATBarrierProfile:
        raw = self.unmodified_profile
        return TATBarrierProfile(
            link_length_m=raw.link_length_m,
            trap_position_m=raw.trap_position_m,
            electric_field_V_m=raw.electric_field_V_m,
            effective_mass_m0=raw.effective_mass_m0,
            entry_start_barrier_J=self.source_interface.corrected_barrier_J,
            trap_barrier_J=raw.trap_barrier_J,
            exit_end_barrier_J=self.destination_interface.corrected_barrier_J,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "unmodified_profile": self.unmodified_profile.to_dict(),
            "corrected_profile": self.corrected_profile.to_dict(),
            "correction_configuration_hash": self.correction_configuration_hash,
            "source_interface": self.source_interface.to_dict(),
            "destination_interface": self.destination_interface.to_dict(),
        }


@dataclass(frozen=True)
class CorrectedTATRateComponent:
    """One J3 species contribution with raw and corrected barriers."""

    species_name: str
    species_hash: str
    barrier_diagnostics: CorrectedTATBarrierProfile
    entry_wkb_exponent: float
    exit_wkb_exponent: float
    entry_transmission: float
    exit_transmission: float
    entry_rate_Hz: float
    exit_rate_Hz: float
    active_probability: float
    rate_Hz: float
    status: TATRateStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_name": self.species_name,
            "species_hash": self.species_hash,
            "barrier_diagnostics": self.barrier_diagnostics.to_dict(),
            "entry_wkb_exponent": self.entry_wkb_exponent,
            "exit_wkb_exponent": self.exit_wkb_exponent,
            "entry_transmission": self.entry_transmission,
            "exit_transmission": self.exit_transmission,
            "entry_rate_Hz": self.entry_rate_Hz,
            "exit_rate_Hz": self.exit_rate_Hz,
            "active_probability": self.active_probability,
            "rate_Hz": self.rate_Hz,
            "status": self.status.value,
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class CorrectedTATRateEvaluation:
    """Mechanism result for the isolated J3 correction-aware evaluator."""

    enabled: bool
    tat_configuration_hash: str
    correction_configuration_hash: str
    components: tuple[CorrectedTATRateComponent, ...]
    total_rate_Hz: float
    status: TATRateStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "tat_configuration_hash": self.tat_configuration_hash,
            "correction_configuration_hash": self.correction_configuration_hash,
            "components": [item.to_dict() for item in self.components],
            "total_rate_Hz": self.total_rate_Hz,
            "status": self.status.value,
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


def image_force_barrier_lowering_J(
    electric_field_V_m: float,
    relative_permittivity: float,
) -> float:
    """Return classical Schottky image-force peak lowering in joules.

    The energy form is ``sqrt(q**3 * abs(F) / (4*pi*epsilon_0*epsilon_r))``.
    It is even in field and exactly zero at zero field.
    """

    field = _finite(electric_field_V_m, "electric_field_V_m")
    permittivity = _positive(relative_permittivity, "relative_permittivity")
    lowering = math.sqrt(
        ELEMENTARY_CHARGE_C ** 3
        * abs(field)
        / (4.0 * math.pi * VACUUM_PERMITTIVITY_F_M * permittivity)
    )
    if not math.isfinite(lowering):
        raise ArithmeticError("non-finite image-force barrier lowering")
    return lowering


def apply_image_force_barrier_correction(
    unmodified_barrier_J: float,
    *,
    electric_field_V_m: float,
    specification: ImageForceBarrierSpec,
) -> BarrierHeightCorrection:
    """Correct one effective interface height without hiding the raw value."""

    barrier = _finite(unmodified_barrier_J, "unmodified_barrier_J")
    field = _finite(electric_field_V_m, "electric_field_V_m")
    if not isinstance(specification, ImageForceBarrierSpec):
        raise TypeError("specification must be ImageForceBarrierSpec")
    if not specification.enabled:
        return BarrierHeightCorrection(
            barrier, 0.0, barrier, BarrierCorrectionStatus.DISABLED
        )
    lowering = image_force_barrier_lowering_J(
        field, specification.relative_permittivity
    )
    corrected = barrier - lowering
    if lowering == 0.0:
        status = BarrierCorrectionStatus.ZERO_FIELD
    elif corrected <= 0.0:
        status = BarrierCorrectionStatus.BARRIER_SUPPRESSED
    else:
        status = BarrierCorrectionStatus.APPLIED
    return BarrierHeightCorrection(barrier, lowering, corrected, status)


def build_corrected_tat_barrier_profile(
    species: TrapSpecies,
    correction: ImageForceBarrierSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> CorrectedTATBarrierProfile:
    """Apply the symmetric interface correction to a raw J2 profile."""

    if not isinstance(correction, ImageForceBarrierSpec):
        raise TypeError("correction must be ImageForceBarrierSpec")
    raw = build_tat_barrier_profile(
        species,
        link_length_m=link_length_m,
        electric_field_V_m=electric_field_V_m,
        effective_mass_m0=effective_mass_m0,
    )
    source = apply_image_force_barrier_correction(
        raw.entry_start_barrier_J,
        electric_field_V_m=raw.electric_field_V_m,
        specification=correction,
    )
    destination = apply_image_force_barrier_correction(
        raw.exit_end_barrier_J,
        electric_field_V_m=raw.electric_field_V_m,
        specification=correction,
    )
    return CorrectedTATBarrierProfile(
        raw, correction.configuration_hash, source, destination
    )


def evaluate_tat_species_with_barrier_correction(
    species: TrapSpecies,
    correction: ImageForceBarrierSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> CorrectedTATRateComponent:
    """Evaluate one J2 pathway using the explicitly corrected endpoints."""

    diagnostics = build_corrected_tat_barrier_profile(
        species,
        correction,
        link_length_m=link_length_m,
        electric_field_V_m=electric_field_V_m,
        effective_mass_m0=effective_mass_m0,
    )
    profile = diagnostics.corrected_profile
    x = profile.trap_position_m
    entry_t, entry_exponent = linear_wkb_transmission(
        x,
        profile.entry_start_barrier_J,
        profile.trap_barrier_J,
        profile.effective_mass_m0,
    )
    exit_t, exit_exponent = linear_wkb_transmission(
        profile.link_length_m - x,
        profile.trap_barrier_J,
        profile.exit_end_barrier_J,
        profile.effective_mass_m0,
    )
    entry_rate = species.attempt_frequency_Hz * entry_t
    exit_rate = species.attempt_frequency_Hz * exit_t
    optical_depth = (
        species.density_m3
        * species.capture_cross_section_m2
        * profile.link_length_m
    )
    active = 1.0 if math.isinf(optical_depth) else -math.expm1(-optical_depth)
    if species.density_m3 == 0.0:
        status = TATRateStatus.ZERO_DENSITY
        rate = 0.0
        active = 0.0
    elif entry_rate == 0.0 or exit_rate == 0.0:
        status = TATRateStatus.TRANSMISSION_UNDERFLOW
        rate = 0.0
    else:
        status = TATRateStatus.EVALUATED
        slow, fast = sorted((entry_rate, exit_rate))
        rate = active * slow / (1.0 + slow / fast)
    return CorrectedTATRateComponent(
        species.name,
        species.species_hash,
        diagnostics,
        entry_exponent,
        exit_exponent,
        entry_t,
        exit_t,
        entry_rate,
        exit_rate,
        active,
        rate,
        status,
    )


def evaluate_trap_assisted_transport_with_barrier_correction(
    specification: TrapAssistedTransportSpec,
    correction: ImageForceBarrierSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> CorrectedTATRateEvaluation:
    """Evaluate the isolated J3 path without transport-engine attachment."""

    if not isinstance(specification, TrapAssistedTransportSpec):
        raise TypeError("specification must be TrapAssistedTransportSpec")
    if not isinstance(correction, ImageForceBarrierSpec):
        raise TypeError("correction must be ImageForceBarrierSpec")
    # Validate context for disabled paths through the existing profile builder.
    if not specification.enabled:
        if specification.species:
            build_tat_barrier_profile(
                specification.species[0],
                link_length_m=link_length_m,
                electric_field_V_m=electric_field_V_m,
                effective_mass_m0=effective_mass_m0,
            )
        else:
            _positive(link_length_m, "link_length_m")
            _finite(electric_field_V_m, "electric_field_V_m")
            _positive(effective_mass_m0, "effective_mass_m0")
        return CorrectedTATRateEvaluation(
            False,
            specification.configuration_hash,
            correction.configuration_hash,
            (),
            0.0,
            TATRateStatus.DISABLED,
        )
    components = tuple(
        evaluate_tat_species_with_barrier_correction(
            species,
            correction,
            link_length_m=link_length_m,
            electric_field_V_m=electric_field_V_m,
            effective_mass_m0=effective_mass_m0,
        )
        for species in specification.species
    )
    total = math.fsum(item.rate_Hz for item in components)
    status = (
        TATRateStatus.TRANSMISSION_UNDERFLOW
        if total == 0.0
        and any(
            item.status is TATRateStatus.TRANSMISSION_UNDERFLOW
            for item in components
        )
        else TATRateStatus.EVALUATED
    )
    return CorrectedTATRateEvaluation(
        True,
        specification.configuration_hash,
        correction.configuration_hash,
        components,
        total,
        status,
    )


__all__ = [
    "BarrierCorrectionStatus",
    "ImageForceBarrierSpec",
    "BarrierHeightCorrection",
    "CorrectedTATBarrierProfile",
    "CorrectedTATRateComponent",
    "CorrectedTATRateEvaluation",
    "image_force_barrier_lowering_J",
    "apply_image_force_barrier_correction",
    "build_corrected_tat_barrier_profile",
    "evaluate_tat_species_with_barrier_correction",
    "evaluate_trap_assisted_transport_with_barrier_correction",
]
