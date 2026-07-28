from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

class ParameterStatus(str, Enum):
    LITERATURE = "literature"
    CALIBRATED = "calibrated"
    ASSUMED = "assumed"
    ESTIMATED = "estimated"
    FITTED = "fitted"

@dataclass(frozen=True)
class ParameterProvenance:
    source: str
    status: ParameterStatus
    doi: str | None = None
    notes: str | None = None
    parameter_set: str = "default-v1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
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
