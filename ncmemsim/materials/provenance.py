from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any


class ParameterStatus(str, Enum):
    LITERATURE = "literature"
    LITERATURE_FITTED = "literature_fitted"
    CALIBRATED = "calibrated"
    ASSUMED = "assumed"
    ESTIMATED = "estimated"
    FITTED = "fitted"
    DERIVED = "derived"


@dataclass(frozen=True)
class ParameterProvenance:
    source: str
    status: ParameterStatus
    doi: str | None = None
    notes: str | None = None
    parameter_set: str = "default-v1"

    reported_uncertainty: float | None = None
    uncertainty_unit: str | None = None

    def __post_init__(self) -> None:
        if self.reported_uncertainty is not None:
            if (
                not math.isfinite(self.reported_uncertainty)
                or self.reported_uncertainty < 0
            ):
                raise ValueError(
                    "reported_uncertainty must be finite and non-negative."
                )

        if self.uncertainty_unit is not None:
            if not self.uncertainty_unit.strip():
                raise ValueError(
                    "uncertainty_unit cannot be empty."
                )

            if self.reported_uncertainty is None:
                raise ValueError(
                    "uncertainty_unit requires reported_uncertainty."
                )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value

        if self.reported_uncertainty is None:
            data.pop("reported_uncertainty")

        if self.uncertainty_unit is None:
            data.pop("uncertainty_unit")

        return data


@dataclass(frozen=True)
class MaterialProperty:
    value: float
    unit: str
    provenance: ParameterProvenance
    symbol: str | None = None

    def __float__(self) -> float:
        return float(self.value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "symbol": self.symbol,
            "provenance": self.provenance.to_dict(),
        }
