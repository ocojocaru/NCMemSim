"""Typed, independent bounded variation assumptions; no sampling in H1."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math
from typing import Any
from ..device import Device
from ..hashing import canonical_hash
from .spec import BindingScope, ParameterBinding, _canonical_binding_unit
from .binding import apply_device_binding
from .operating import OperatingProtocol, apply_operating_binding


class VariationKind(str, Enum):
    FABRICATION = "fabrication"
    PARAMETER_ESTIMATION = "parameter_estimation"


def _text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be nonempty text without outer whitespace")


def _number(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric, excluding bool")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _bounds(instance: Any) -> None:
    for field in ("lower", "upper"):
        object.__setattr__(instance, field, _number(getattr(instance, field), field))
    if instance.lower >= instance.upper:
        raise ValueError("lower must be strictly less than upper")


@dataclass(frozen=True)
class UniformVariation:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        _bounds(self)

    def to_dict(self) -> dict[str, Any]:
        return {"family": "uniform", "lower": self.lower, "upper": self.upper}


@dataclass(frozen=True)
class TruncatedNormalVariation:
    """Mean/std of the underlying normal, before truncation to [lower, upper]."""
    lower: float
    upper: float
    mean: float
    standard_deviation: float

    def __post_init__(self) -> None:
        _bounds(self)
        for field in ("mean", "standard_deviation"):
            object.__setattr__(self, field, _number(getattr(self, field), field))
        if self.standard_deviation <= 0:
            raise ValueError("standard_deviation must be strictly positive")

    def to_dict(self) -> dict[str, Any]:
        return {"family": "truncated_normal", "lower": self.lower,
                "upper": self.upper, "mean": self.mean,
                "standard_deviation": self.standard_deviation}


@dataclass(frozen=True)
class VariationProvenance:
    """Declared source and applicability; neither implies measured calibration."""
    source: str
    applicability: str
    notes: str | None = None

    def __post_init__(self) -> None:
        _text(self.source, "source")
        _text(self.applicability, "applicability")
        if self.notes is not None:
            _text(self.notes, "notes")

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "applicability": self.applicability,
                "notes": self.notes}


@dataclass(frozen=True)
class VariationDefinition:
    name: str
    binding: ParameterBinding
    distribution: UniformVariation | TruncatedNormalVariation
    unit: str
    kind: VariationKind
    provenance: VariationProvenance

    def __post_init__(self) -> None:
        _text(self.name, "name")
        if not isinstance(self.binding, ParameterBinding):
            raise TypeError("binding must be ParameterBinding")
        if not isinstance(self.distribution, (UniformVariation, TruncatedNormalVariation)):
            raise TypeError("unsupported distribution")
        if not isinstance(self.kind, VariationKind):
            raise TypeError("kind must be VariationKind")
        if not isinstance(self.provenance, VariationProvenance):
            raise TypeError("provenance must be VariationProvenance")
        expected = _canonical_binding_unit(self.binding)
        path = self.binding.path
        if self.binding.scope is BindingScope.MODEL or expected is None or path[-1] == "grid_points":
            raise ValueError("H1 requires a supported continuous DEVICE/OPERATING binding")
        if self.unit != expected:
            raise ValueError(f"canonical unit must be {expected!r}")
        lower, upper = self.distribution.lower, self.distribution.upper
        attribute = path[-1]
        if attribute in {"nc_volume_fraction", "electrically_active_fraction", "sn_fraction"}:
            if lower < 0 or upper > 1:
                raise ValueError("fraction bounds must lie within [0, 1]")
        elif attribute in {"substrate_doping_m3", "temperature_K", "thickness_nm",
                           "nc_diameter_nm", "time_s", "internal_dt_s",
                           "wavelength_nm", "power_density_W_m2"} and lower <= 0:
            raise ValueError("binding bounds must be strictly positive")

    def validate_context(self, device: Device, protocol: OperatingProtocol | None = None) -> None:
        """Validate both endpoints on isolated nominal copies, without executing physics.

        This does not validate combinations of multiple variations or guarantee
        successful numerical evaluation. Every future candidate must be validated.
        """
        for value in (self.distribution.lower, self.distribution.upper):
            if self.binding.scope is BindingScope.DEVICE:
                apply_device_binding(device, self.binding, value)
            else:
                device.validate()
                if protocol is None:
                    raise ValueError("OPERATING variation requires a nominal protocol")
                apply_operating_binding(protocol, self.binding, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "name": self.name,
                "binding": self.binding.to_dict(), "distribution": self.distribution.to_dict(),
                "unit": self.unit, "kind": self.kind.value,
                "provenance": self.provenance.to_dict()}

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())
