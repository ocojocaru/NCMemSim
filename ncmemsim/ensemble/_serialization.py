"""Strict private deserialization helpers for Phase K."""

from __future__ import annotations

from typing import Any

from ..dtco.spec import BindingScope, ParameterBinding
from ..materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def strict_fields(
    data: dict[str, Any],
    *,
    label: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    if not isinstance(data, dict):
        raise TypeError(f"{label} data must be a dict")

    optional = optional or set()
    actual = set(data)

    missing = required - actual
    if missing:
        raise ValueError(
            f"missing {label} fields: "
            + ", ".join(sorted(map(str, missing)))
        )

    unknown = actual - required - optional
    if unknown:
        raise ValueError(
            f"unknown {label} fields: "
            + ", ".join(sorted(map(str, unknown)))
        )


def parameter_binding_from_dict(
    data: dict[str, Any],
) -> ParameterBinding:
    strict_fields(
        data,
        label="parameter-binding",
        required={"scope", "path"},
    )

    scope = data["scope"]
    if not isinstance(scope, str):
        raise TypeError("parameter-binding scope must be text")

    try:
        binding_scope = BindingScope(scope)
    except ValueError as exc:
        raise ValueError(
            f"unsupported parameter-binding scope {scope!r}"
        ) from exc

    path = data["path"]
    if not isinstance(path, list):
        raise TypeError("parameter-binding path must be a list")

    return ParameterBinding(
        scope=binding_scope,
        path=tuple(path),
    )


def parameter_provenance_from_dict(
    data: dict[str, Any],
) -> ParameterProvenance:
    strict_fields(
        data,
        label="parameter-provenance",
        required={
            "source",
            "status",
            "doi",
            "notes",
            "parameter_set",
        },
        optional={
            "reported_uncertainty",
            "uncertainty_unit",
        },
    )

    status = data["status"]
    if not isinstance(status, str):
        raise TypeError("parameter-provenance status must be text")

    try:
        parameter_status = ParameterStatus(status)
    except ValueError as exc:
        raise ValueError(
            f"unsupported parameter-provenance status {status!r}"
        ) from exc

    return ParameterProvenance(
        source=data["source"],
        status=parameter_status,
        doi=data["doi"],
        notes=data["notes"],
        parameter_set=data["parameter_set"],
        reported_uncertainty=data.get(
            "reported_uncertainty"
        ),
        uncertainty_unit=data.get(
            "uncertainty_unit"
        ),
    )


__all__ = [
    "parameter_binding_from_dict",
    "parameter_provenance_from_dict",
    "strict_fields",
]
