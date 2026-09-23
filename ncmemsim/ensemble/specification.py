"""Immutable ensemble-study identity contracts for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

from ..device import Device
from ..dtco.spec import (
    BindingScope,
    _device_definition_payload,
    _operating_definition_payload,
)
from ..hashing import canonical_hash
from .spec import StochasticVariable
from ._serialization import strict_fields


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(
            f"{label} must be nonempty text without outer whitespace"
        )
    return value


@dataclass(frozen=True)
class EnsembleSpec:
    """Immutable identity of a stochastic Phase K study definition."""

    name: str
    base_device_hash: str
    variables: tuple[StochasticVariable, ...]
    base_device_name: str | None = None
    description: str | None = None
    base_operating_hash: str | None = None
    base_operating_kind: str | None = None
    schema_version: str = "ensemble-spec-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "variables", tuple(self.variables))

        _text(self.name, "name")

        if not isinstance(self.base_device_hash, str) or not _SHA256_RE.fullmatch(
            self.base_device_hash
        ):
            raise ValueError(
                "base_device_hash must be a lowercase SHA-256 hex digest"
            )

        if self.base_device_name is not None:
            _text(self.base_device_name, "base_device_name")

        if self.description is not None:
            _text(self.description, "description")

        if self.schema_version != "ensemble-spec-v1":
            raise ValueError("unsupported ensemble schema_version")

        if not self.variables:
            raise ValueError(
                "ensemble specification requires at least one stochastic variable"
            )

        for variable in self.variables:
            if not isinstance(variable, StochasticVariable):
                raise TypeError(
                    "variables must contain StochasticVariable instances"
                )

        names = [variable.name for variable in self.variables]
        if len(set(names)) != len(names):
            raise ValueError(
                "stochastic-variable names must be unique"
            )

        binding_ids = [
            variable.binding.binding_id
            for variable in self.variables
        ]
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError(
                "each stochastic variable must target a unique binding"
            )

        if (self.base_operating_hash is None) != (
            self.base_operating_kind is None
        ):
            raise ValueError(
                "base_operating_hash and base_operating_kind "
                "must be supplied together"
            )

        if self.base_operating_hash is not None:
            if (
                not isinstance(self.base_operating_hash, str)
                or not _SHA256_RE.fullmatch(self.base_operating_hash)
            ):
                raise ValueError(
                    "base_operating_hash must be a lowercase "
                    "SHA-256 hex digest"
                )

            _text(
                self.base_operating_kind,
                "base_operating_kind",
            )

        has_operating_variable = any(
            variable.binding.scope is BindingScope.OPERATING
            for variable in self.variables
        )

        if has_operating_variable and self.base_operating_hash is None:
            raise ValueError(
                "ensemble specifications with operating-scope variables "
                "require an operating baseline identity"
            )

    @classmethod
    def from_device(
        cls,
        *,
        name: str,
        device: Device,
        variables: Iterable[StochasticVariable],
        description: str | None = None,
        operating_protocol: Any | None = None,
    ) -> "EnsembleSpec":
        device.validate()

        base_operating_hash = None
        base_operating_kind = None

        if operating_protocol is not None:
            operating_payload = _operating_definition_payload(
                operating_protocol
            )
            base_operating_hash = canonical_hash(operating_payload)
            base_operating_kind = operating_payload["kind"]

        return cls(
            name=name,
            base_device_hash=canonical_hash(
                _device_definition_payload(device)
            ),
            variables=tuple(variables),
            base_device_name=device.name,
            description=description,
            base_operating_hash=base_operating_hash,
            base_operating_kind=base_operating_kind,
        )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "EnsembleSpec":
        strict_fields(
            data,
            label="ensemble-specification",
            required={
                "schema_version",
                "name",
                "base_device_hash",
                "base_device_name",
                "variables",
            },
            optional={
                "description",
                "base_operating_hash",
                "base_operating_kind",
            },
        )

        variables = data["variables"]
        if not isinstance(variables, list):
            raise TypeError(
                "ensemble-specification variables must be a list"
            )

        return cls(
            name=data["name"],
            base_device_hash=data["base_device_hash"],
            variables=tuple(
                StochasticVariable.from_dict(variable)
                for variable in variables
            ),
            base_device_name=data["base_device_name"],
            description=data.get("description"),
            base_operating_hash=data.get(
                "base_operating_hash"
            ),
            base_operating_kind=data.get(
                "base_operating_kind"
            ),
            schema_version=data["schema_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "name": self.name,
            "base_device_hash": self.base_device_hash,
            "base_device_name": self.base_device_name,
            "variables": [
                variable.to_dict()
                for variable in self.variables
            ],
        }

        if self.description is not None:
            data["description"] = self.description

        if self.base_operating_hash is not None:
            data["base_operating_hash"] = self.base_operating_hash
            data["base_operating_kind"] = self.base_operating_kind

        return data

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(
            variable.name
            for variable in self.variables
        )

    def matches_device(self, device: Device) -> bool:
        device.validate()

        return (
            canonical_hash(_device_definition_payload(device))
            == self.base_device_hash
        )

    def require_matching_device(self, device: Device) -> None:
        if not self.matches_device(device):
            raise ValueError(
                "device does not match ensemble base_device_hash"
            )

    def matches_operating(self, operating_protocol: Any) -> bool:
        if self.base_operating_hash is None:
            return False

        payload = _operating_definition_payload(
            operating_protocol
        )

        return (
            payload["kind"] == self.base_operating_kind
            and canonical_hash(payload)
            == self.base_operating_hash
        )

    def require_matching_operating(
        self,
        operating_protocol: Any,
    ) -> None:
        if self.base_operating_hash is None:
            raise ValueError(
                "ensemble specification has no operating baseline identity"
            )

        if not self.matches_operating(operating_protocol):
            raise ValueError(
                "operating protocol does not match ensemble "
                "base_operating_hash"
            )


__all__ = [
    "EnsembleSpec",
]
