"""Dependence contracts for Phase K ensemble sampling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..hashing import canonical_hash
from ._serialization import strict_fields


DEPENDENCE_SCHEMA_VERSION = "ensemble-dependence-v1"


@dataclass(frozen=True)
class IndependentDependence:
    """Explicit independent-sampling dependence contract."""

    kind: str = "independent"
    schema_version: str = DEPENDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.kind != "independent":
            raise ValueError(
                f"unsupported dependence kind {self.kind!r}"
            )

        if self.schema_version != DEPENDENCE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported dependence schema_version"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "IndependentDependence":
        strict_fields(
            data,
            label="dependence-specification",
            required={
                "schema_version",
                "kind",
            },
        )

        return cls(
            kind=data["kind"],
            schema_version=data["schema_version"],
        )

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


DependenceSpec = IndependentDependence


def dependence_from_dict(
    data: dict[str, Any],
) -> DependenceSpec:
    """Restore one supported Phase K dependence specification."""

    if not isinstance(data, dict):
        raise TypeError(
            "dependence specification data must be a dict"
        )

    if "kind" not in data:
        raise ValueError(
            "missing dependence-specification fields: kind"
        )

    kind = data["kind"]

    if not isinstance(kind, str):
        raise TypeError(
            "dependence specification kind must be text"
        )

    if kind == "independent":
        return IndependentDependence.from_dict(data)

    raise ValueError(
        f"unsupported dependence kind {kind!r}"
    )


__all__ = [
    "DEPENDENCE_SCHEMA_VERSION",
    "DependenceSpec",
    "IndependentDependence",
    "dependence_from_dict",
]
