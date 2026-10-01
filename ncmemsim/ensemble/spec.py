# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Stochastic-variable contracts for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from ..dtco.spec import (
    BindingScope,
    ParameterBinding,
    _canonical_binding_unit,
)
from ..hashing import canonical_hash
from ..materials.provenance import ParameterProvenance, ParameterStatus
from .distributions import (
    ConstantDistribution,
    DistributionSpec,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
    distribution_from_dict,
)
from ._serialization import (
    parameter_binding_from_dict,
    parameter_provenance_from_dict,
    strict_fields,
)


_DISTRIBUTION_TYPES = (
    ConstantDistribution,
    NormalDistribution,
    TruncatedNormalDistribution,
    UniformDistribution,
    LogNormalDistribution,
    FiniteDiscreteDistribution,
)


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(
            f"{label} must be nonempty text without outer whitespace"
        )
    return value


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


@dataclass(frozen=True)
class PhysicalDomain:
    """Explicit physical domain for one stochastic variable."""

    lower: float | None = None
    upper: float | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.lower_inclusive, bool):
            raise TypeError("lower_inclusive must be bool")
        if not isinstance(self.upper_inclusive, bool):
            raise TypeError("upper_inclusive must be bool")

        lower = (
            None
            if self.lower is None
            else _number(self.lower, "lower")
        )
        upper = (
            None
            if self.upper is None
            else _number(self.upper, "upper")
        )

        if lower is not None and upper is not None and lower >= upper:
            raise ValueError(
                "physical-domain lower must be strictly less than upper"
            )

        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "PhysicalDomain":
        strict_fields(
            data,
            label="physical-domain",
            required={
                "lower",
                "upper",
                "lower_inclusive",
                "upper_inclusive",
            },
        )

        return cls(
            lower=data["lower"],
            upper=data["upper"],
            lower_inclusive=data["lower_inclusive"],
            upper_inclusive=data["upper_inclusive"],
        )

    def contains(self, value: float) -> bool:
        candidate = _number(value, "value")

        if self.lower is not None:
            if self.lower_inclusive:
                if candidate < self.lower:
                    return False
            elif candidate <= self.lower:
                return False

        if self.upper is not None:
            if self.upper_inclusive:
                if candidate > self.upper:
                    return False
            elif candidate >= self.upper:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "lower_inclusive": self.lower_inclusive,
            "upper_inclusive": self.upper_inclusive,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


def _validate_binding_domain(
    binding: ParameterBinding,
    domain: PhysicalDomain,
) -> None:
    attribute = binding.path[-1]

    if attribute in {
        "nc_volume_fraction",
        "electrically_active_fraction",
        "sn_fraction",
    }:
        if domain.lower is None or domain.upper is None:
            raise ValueError(
                "fraction bindings require a physical domain bounded within [0, 1]"
            )
        if domain.lower < 0.0 or domain.upper > 1.0:
            raise ValueError(
                "fraction physical domain must lie within [0, 1]"
            )
        return

    if attribute in {
        "substrate_doping_m3",
        "temperature_K",
        "thickness_nm",
        "nc_diameter_nm",
        "time_s",
        "internal_dt_s",
        "wavelength_nm",
        "power_density_W_m2",
    }:
        if domain.lower is None:
            raise ValueError(
                "positive-valued binding requires an explicit lower domain bound"
            )

        if domain.lower < 0.0:
            raise ValueError(
                "positive-valued binding physical domain cannot include negatives"
            )

        if domain.lower == 0.0 and domain.lower_inclusive:
            raise ValueError(
                "positive-valued binding physical domain must exclude zero"
            )


@dataclass(frozen=True)
class StochasticVariable:
    """One stochastic variable bound to a stable NCMemSim parameter."""

    name: str
    binding: ParameterBinding
    distribution: DistributionSpec
    unit: str
    physical_domain: PhysicalDomain
    provenance: ParameterProvenance
    applicability: str
    nominal_value: float | None = None
    nominal_value_source: str = "binding_context"
    schema_version: str = "ensemble-variable-v1"

    def __post_init__(self) -> None:
        _text(self.name, "name")

        if not isinstance(self.binding, ParameterBinding):
            raise TypeError("binding must be ParameterBinding")

        if not isinstance(self.distribution, _DISTRIBUTION_TYPES):
            raise TypeError("distribution must be a supported DistributionSpec")

        if not isinstance(self.physical_domain, PhysicalDomain):
            raise TypeError("physical_domain must be PhysicalDomain")

        if not isinstance(self.provenance, ParameterProvenance):
            raise TypeError("provenance must be ParameterProvenance")

        if not isinstance(self.provenance.status, ParameterStatus):
            raise TypeError(
                "provenance.status must be a ParameterStatus"
            )

        _text(self.provenance.source, "provenance.source")
        _text(self.applicability, "applicability")
        _text(self.nominal_value_source, "nominal_value_source")

        if self.schema_version != "ensemble-variable-v1":
            raise ValueError("unsupported stochastic-variable schema_version")

        expected_unit = _canonical_binding_unit(self.binding)

        if (
            self.binding.scope is BindingScope.MODEL
            or expected_unit is None
            or self.binding.path[-1] == "grid_points"
        ):
            raise ValueError(
                "K1 requires a supported numeric DEVICE/OPERATING binding"
            )

        if self.unit != expected_unit:
            raise ValueError(
                f"canonical unit must be {expected_unit!r}"
            )

        _validate_binding_domain(
            self.binding,
            self.physical_domain,
        )

        if self.nominal_value is not None:
            nominal = _number(self.nominal_value, "nominal_value")

            if not self.physical_domain.contains(nominal):
                raise ValueError(
                    "nominal_value must lie inside physical_domain"
                )

            object.__setattr__(self, "nominal_value", nominal)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "StochasticVariable":
        strict_fields(
            data,
            label="stochastic-variable",
            required={
                "schema_version",
                "name",
                "binding",
                "distribution",
                "unit",
                "physical_domain",
                "provenance",
                "applicability",
                "nominal_value",
                "nominal_value_source",
            },
        )

        return cls(
            name=data["name"],
            binding=parameter_binding_from_dict(
                data["binding"]
            ),
            distribution=distribution_from_dict(
                data["distribution"]
            ),
            unit=data["unit"],
            physical_domain=PhysicalDomain.from_dict(
                data["physical_domain"]
            ),
            provenance=parameter_provenance_from_dict(
                data["provenance"]
            ),
            applicability=data["applicability"],
            nominal_value=data["nominal_value"],
            nominal_value_source=data["nominal_value_source"],
            schema_version=data["schema_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "binding": self.binding.to_dict(),
            "distribution": self.distribution.to_dict(),
            "unit": self.unit,
            "physical_domain": self.physical_domain.to_dict(),
            "provenance": self.provenance.to_dict(),
            "applicability": self.applicability,
            "nominal_value": self.nominal_value,
            "nominal_value_source": self.nominal_value_source,
        }

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


__all__ = [
    "PhysicalDomain",
    "StochasticVariable",
]
