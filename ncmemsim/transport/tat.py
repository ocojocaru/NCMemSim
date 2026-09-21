"""Compact trap-assisted-tunnelling kernel for Phase J2.

The kernel evaluates the conditional sequential path selected in J1.  It is
deliberately independent of reservoir occupation, current density and the
transport network; those integration concerns remain later Phase J work.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

import numpy as np

from ..hashing import canonical_hash
from .traps import TrapAssistedTransportSpec, TrapSpecies


ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837139e-31
REDUCED_PLANCK_J_S = 1.054571817e-34


class TATRateStatus(str, Enum):
    """Outcome of a compact TAT evaluation."""

    DISABLED = "disabled"
    ZERO_DENSITY = "zero_density"
    EVALUATED = "evaluated"
    TRANSMISSION_UNDERFLOW = "transmission_underflow"


def _positive(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric, excluding bool")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{field} must be finite and strictly positive")
    return result


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric, excluding bool")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _linear_positive_sqrt_integral(length_m: float, start_J: float, end_J: float) -> float:
    """Integrate ``sqrt(max(U(s), 0))`` for a linear barrier exactly."""

    if start_J == end_J:
        return length_m * math.sqrt(max(start_J, 0.0))
    primitive_start = (2.0 / 3.0) * max(start_J, 0.0) ** 1.5
    primitive_end = (2.0 / 3.0) * max(end_J, 0.0) ** 1.5
    return length_m * (primitive_end - primitive_start) / (end_J - start_J)


def linear_wkb_transmission(
    length_m: float,
    start_barrier_J: float,
    end_barrier_J: float,
    effective_mass_m0: float,
) -> tuple[float, float]:
    """Return transmission and nonnegative WKB exponent for a linear barrier.

    Regions at or below the tunnelling energy have zero action.  Exponential
    underflow is returned as an exact zero while the finite exponent remains
    available to diagnostics.
    """

    length = _positive(length_m, "length_m")
    start = _finite(start_barrier_J, "start_barrier_J")
    end = _finite(end_barrier_J, "end_barrier_J")
    mass_ratio = _positive(effective_mass_m0, "effective_mass_m0")
    integral = _linear_positive_sqrt_integral(length, start, end)
    exponent = (
        2.0
        * math.sqrt(2.0 * mass_ratio * ELECTRON_MASS_KG)
        * integral
        / REDUCED_PLANCK_J_S
    )
    if not math.isfinite(exponent):
        raise ArithmeticError("non-finite WKB exponent")
    transmission = math.exp(-exponent) if exponent < 746.0 else 0.0
    return transmission, exponent


@dataclass(frozen=True)
class TATBarrierProfile:
    """Two linear WKB legs measured relative to the representative trap."""

    link_length_m: float
    trap_position_m: float
    electric_field_V_m: float
    effective_mass_m0: float
    entry_start_barrier_J: float
    trap_barrier_J: float
    exit_end_barrier_J: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_length_m": self.link_length_m,
            "trap_position_m": self.trap_position_m,
            "electric_field_V_m": self.electric_field_V_m,
            "effective_mass_m0": self.effective_mass_m0,
            "entry_start_barrier_J": self.entry_start_barrier_J,
            "trap_barrier_J": self.trap_barrier_J,
            "exit_end_barrier_J": self.exit_end_barrier_J,
        }


@dataclass(frozen=True)
class TATRateComponent:
    """Immutable component diagnostics for one trap population."""

    species_name: str
    species_hash: str
    barrier_profile: TATBarrierProfile
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
            "barrier_profile": self.barrier_profile.to_dict(),
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
class TATRateEvaluation:
    """Mechanism-level result with separately observable species rates."""

    enabled: bool
    configuration_hash: str
    components: tuple[TATRateComponent, ...]
    total_rate_Hz: float
    status: TATRateStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "configuration_hash": self.configuration_hash,
            "components": [item.to_dict() for item in self.components],
            "total_rate_Hz": self.total_rate_Hz,
            "status": self.status.value,
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class TATRateBatch:
    """Broadcast-shaped collection returned by the array entry point."""

    shape: tuple[int, ...]
    evaluations: tuple[TATRateEvaluation, ...]

    def __post_init__(self) -> None:
        if type(self.shape) is not tuple or any(type(value) is not int or value < 0 for value in self.shape):
            raise TypeError("shape must be a tuple of nonnegative integers")
        if type(self.evaluations) is not tuple or any(
            not isinstance(value, TATRateEvaluation) for value in self.evaluations
        ):
            raise TypeError("evaluations must be a tuple of TATRateEvaluation")
        expected = math.prod(self.shape) if self.shape else 1
        if len(self.evaluations) != expected:
            raise ValueError("evaluation count does not match broadcast shape")

    @property
    def total_rates_Hz(self) -> np.ndarray:
        """Return an independent array; mutating it cannot alter this result."""

        return np.asarray([item.total_rate_Hz for item in self.evaluations], dtype=float).reshape(self.shape)


def build_tat_barrier_profile(
    species: TrapSpecies,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> TATBarrierProfile:
    """Build the directed, trap-referenced two-leg barrier profile.

    Positive field points from source to destination and lowers electron
    potential energy by ``q F s``.  At the trap the barrier relative to the
    trap level is its positive conduction-band depth.  The same level defines
    both legs, so reversing field and mirroring position swaps the two actions.
    """

    if not isinstance(species, TrapSpecies):
        raise TypeError("species must be TrapSpecies")
    length = _positive(link_length_m, "link_length_m")
    field = _finite(electric_field_V_m, "electric_field_V_m")
    mass = _positive(effective_mass_m0, "effective_mass_m0")
    x = species.position_fraction * length
    depth = species.energy_depth_J
    return TATBarrierProfile(
        link_length_m=length,
        trap_position_m=x,
        electric_field_V_m=field,
        effective_mass_m0=mass,
        entry_start_barrier_J=depth + ELEMENTARY_CHARGE_C * field * x,
        trap_barrier_J=depth,
        exit_end_barrier_J=depth - ELEMENTARY_CHARGE_C * field * (length - x),
    )


def evaluate_tat_species(
    species: TrapSpecies,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> TATRateComponent:
    """Evaluate one conditional sequential two-step WKB contribution."""

    profile = build_tat_barrier_profile(
        species,
        link_length_m=link_length_m,
        electric_field_V_m=electric_field_V_m,
        effective_mass_m0=effective_mass_m0,
    )
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
    optical_depth = species.density_m3 * species.capture_cross_section_m2 * profile.link_length_m
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
    return TATRateComponent(
        species_name=species.name,
        species_hash=species.species_hash,
        barrier_profile=profile,
        entry_wkb_exponent=entry_exponent,
        exit_wkb_exponent=exit_exponent,
        entry_transmission=entry_t,
        exit_transmission=exit_t,
        entry_rate_Hz=entry_rate,
        exit_rate_Hz=exit_rate,
        active_probability=active,
        rate_Hz=rate,
        status=status,
    )


def evaluate_trap_assisted_transport(
    specification: TrapAssistedTransportSpec,
    *,
    link_length_m: float,
    electric_field_V_m: float,
    effective_mass_m0: float,
) -> TATRateEvaluation:
    """Evaluate all configured species without attaching them to an engine."""

    if not isinstance(specification, TrapAssistedTransportSpec):
        raise TypeError("specification must be TrapAssistedTransportSpec")
    # Geometry is validated even for disabled specifications so a call never
    # silently accepts a malformed link context.
    length = _positive(link_length_m, "link_length_m")
    field = _finite(electric_field_V_m, "electric_field_V_m")
    mass = _positive(effective_mass_m0, "effective_mass_m0")
    if not specification.enabled:
        return TATRateEvaluation(
            enabled=False,
            configuration_hash=specification.configuration_hash,
            components=(),
            total_rate_Hz=0.0,
            status=TATRateStatus.DISABLED,
        )
    components = tuple(
        evaluate_tat_species(
            species,
            link_length_m=length,
            electric_field_V_m=field,
            effective_mass_m0=mass,
        )
        for species in specification.species
    )
    total = math.fsum(item.rate_Hz for item in components)
    status = (
        TATRateStatus.TRANSMISSION_UNDERFLOW
        if total == 0.0 and any(item.status is TATRateStatus.TRANSMISSION_UNDERFLOW for item in components)
        else TATRateStatus.EVALUATED
    )
    return TATRateEvaluation(True, specification.configuration_hash, components, total, status)


def evaluate_trap_assisted_transport_array(
    specification: TrapAssistedTransportSpec,
    *,
    link_length_m,
    electric_field_V_m,
    effective_mass_m0,
) -> TATRateBatch:
    """Broadcast geometry/field/mass arrays through the scalar reference kernel."""

    raw = tuple(
        np.asarray(value)
        for value in (link_length_m, electric_field_V_m, effective_mass_m0)
    )
    if any(value.dtype.kind == "b" for value in raw):
        raise TypeError("array inputs must be numeric, excluding bool")
    lengths, fields, masses = np.broadcast_arrays(*raw)
    evaluations = tuple(
        evaluate_trap_assisted_transport(
            specification,
            link_length_m=float(length),
            electric_field_V_m=float(field),
            effective_mass_m0=float(mass),
        )
        for length, field, mass in zip(lengths.flat, fields.flat, masses.flat)
    )
    return TATRateBatch(tuple(lengths.shape), evaluations)


__all__ = [
    "TATRateStatus",
    "TATBarrierProfile",
    "TATRateComponent",
    "TATRateEvaluation",
    "TATRateBatch",
    "linear_wkb_transmission",
    "build_tat_barrier_profile",
    "evaluate_tat_species",
    "evaluate_trap_assisted_transport",
    "evaluate_trap_assisted_transport_array",
]
