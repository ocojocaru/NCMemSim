"""Deterministic design-variable and experiment specifications for DTCO.

Phase G1 deliberately defines experiment semantics before implementing the
sweep engine. The classes in this module describe what may vary and how an
experiment is identified; they do not yet mutate devices or execute
simulations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import TYPE_CHECKING, Any, Iterable

from ..hashing import canonical_hash
from ..layers import FloatingGateLayer
from ..materials.provenance import ParameterProvenance

if TYPE_CHECKING:
    from ..device import Device


ScalarValue = int | float | str
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _device_definition_payload(device: "Device") -> dict[str, Any]:
    """Return the full DTCO identity payload for a validated device.

    ``Device.to_dict()`` is retained for backward compatibility and does not
    serialize every material-model parameter. DTCO experiment identity must
    also include the complete material definitions attached to each layer so
    that a physically different material cannot alias the same base-device
    hash merely by retaining the same material name/composition label.
    """

    material_definitions: list[dict[str, Any]] = []
    for layer in device.layers:
        if isinstance(layer, FloatingGateLayer):
            material_definitions.append(
                {
                    "layer_name": layer.name,
                    "matrix_material": layer.matrix_material.to_dict(),
                    "nc_material": layer.nc_material.to_dict(),
                }
            )
        else:
            material_definitions.append(
                {
                    "layer_name": layer.name,
                    "material": layer.material.to_dict(),
                }
            )

    return {
        "device": device.to_dict(),
        "layer_material_definitions": material_definitions,
    }


class BindingScope(str, Enum):
    """Top-level object family addressed by a DTCO parameter binding."""

    DEVICE = "device"
    OPERATING = "operating"
    MODEL = "model"


class DesignVariableRole(str, Enum):
    """Scientific role of a variable in a DTCO experiment."""

    GEOMETRY = "geometry"
    MATERIAL = "material"
    ELECTRICAL = "electrical"
    OPTICAL = "optical"
    MODEL = "model"


@dataclass(frozen=True)
class ParameterBinding:
    """Declarative target for a design variable."""

    scope: BindingScope
    path: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", tuple(self.path))
        if not isinstance(self.scope, BindingScope):
            raise TypeError("scope must be a BindingScope")
        if not self.path:
            raise ValueError("binding path cannot be empty")
        for segment in self.path:
            if not isinstance(segment, str) or not segment.strip():
                raise ValueError("binding path segments must be non-empty strings")
            if segment != segment.strip():
                raise ValueError("binding path segments cannot have outer whitespace")

    def to_dict(self) -> dict[str, Any]:
        return {"scope": self.scope.value, "path": list(self.path)}

    @property
    def binding_id(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class DesignVariable:
    """One explicitly enumerated variable in a deterministic DTCO experiment."""

    name: str
    binding: ParameterBinding
    values: tuple[ScalarValue, ...]
    role: DesignVariableRole
    unit: str | None = None
    provenance: ParameterProvenance | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", tuple(self.values))

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("variable name cannot be empty")
        if self.name != self.name.strip():
            raise ValueError("variable name cannot have outer whitespace")
        if not isinstance(self.binding, ParameterBinding):
            raise TypeError("binding must be a ParameterBinding")
        if not isinstance(self.role, DesignVariableRole):
            raise TypeError("role must be a DesignVariableRole")
        if self.provenance is not None and not isinstance(
            self.provenance, ParameterProvenance
        ):
            raise TypeError("provenance must be ParameterProvenance or None")
        if not self.values:
            raise ValueError("design variable requires at least one value")

        numeric_flags: list[bool] = []
        string_flags: list[bool] = []
        for value in self.values:
            if isinstance(value, bool):
                raise TypeError("boolean design-variable values are not supported")
            is_numeric = isinstance(value, (int, float))
            is_string = isinstance(value, str)
            numeric_flags.append(is_numeric)
            string_flags.append(is_string)
            if not (is_numeric or is_string):
                raise TypeError("design-variable values must be int, float, or str")
            if is_numeric and not math.isfinite(float(value)):
                raise ValueError("numeric design-variable values must be finite")
            if is_string and not value.strip():
                raise ValueError("categorical design-variable values cannot be empty")

        all_numeric = all(numeric_flags)
        all_strings = all(string_flags)
        if not (all_numeric or all_strings):
            raise TypeError(
                "a design-variable domain cannot mix numeric and categorical values"
            )

        if all_numeric:
            if self.unit is None or not self.unit.strip():
                raise ValueError(
                    "numeric design variables require an explicit unit; "
                    "use '1' for dimensionless quantities"
                )
            if self.unit != self.unit.strip():
                raise ValueError("unit cannot have outer whitespace")
            normalized = [float(value) for value in self.values]
        else:
            if self.unit is not None:
                raise ValueError("categorical design variables must use unit=None")
            normalized = list(self.values)

        if len(set(normalized)) != len(normalized):
            raise ValueError("design-variable values must be unique")

    @property
    def is_numeric(self) -> bool:
        return isinstance(self.values[0], (int, float)) and not isinstance(
            self.values[0], bool
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "binding": self.binding.to_dict(),
            "values": list(self.values),
            "role": self.role.value,
            "unit": self.unit,
        }
        if self.provenance is not None:
            data["provenance"] = self.provenance.to_dict()
        return data

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class ExperimentSpec:
    """Immutable identity of a deterministic DTCO experiment definition."""

    name: str
    base_device_hash: str
    variables: tuple[DesignVariable, ...]
    base_device_name: str | None = None
    description: str | None = None
    schema_version: str = "dtco-experiment-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "variables", tuple(self.variables))

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("experiment name cannot be empty")
        if self.name != self.name.strip():
            raise ValueError("experiment name cannot have outer whitespace")
        if not isinstance(self.base_device_hash, str) or not _SHA256_RE.fullmatch(
            self.base_device_hash
        ):
            raise ValueError("base_device_hash must be a lowercase SHA-256 hex digest")
        if self.base_device_name is not None:
            if not self.base_device_name.strip():
                raise ValueError("base_device_name cannot be empty")
            if self.base_device_name != self.base_device_name.strip():
                raise ValueError("base_device_name cannot have outer whitespace")
        if self.description is not None and not self.description.strip():
            raise ValueError("description cannot be empty when provided")
        if self.schema_version != "dtco-experiment-v1":
            raise ValueError("unsupported experiment schema_version")
        if not self.variables:
            raise ValueError("experiment requires at least one design variable")
        for variable in self.variables:
            if not isinstance(variable, DesignVariable):
                raise TypeError("variables must contain DesignVariable instances")

        names = [variable.name for variable in self.variables]
        if len(set(names)) != len(names):
            raise ValueError("design-variable names must be unique")

        binding_ids = [variable.binding.binding_id for variable in self.variables]
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("each design variable must target a unique binding")

    @classmethod
    def from_device(
        cls,
        *,
        name: str,
        device: "Device",
        variables: Iterable[DesignVariable],
        description: str | None = None,
    ) -> "ExperimentSpec":
        device.validate()
        return cls(
            name=name,
            base_device_hash=canonical_hash(_device_definition_payload(device)),
            base_device_name=device.name,
            variables=tuple(variables),
            description=description,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "name": self.name,
            "base_device_hash": self.base_device_hash,
            "base_device_name": self.base_device_name,
            "variables": [variable.to_dict() for variable in self.variables],
        }
        if self.description is not None:
            data["description"] = self.description
        return data

    @property
    def experiment_hash(self) -> str:
        return canonical_hash(self.to_dict())

    @property
    def design_point_count(self) -> int:
        count = 1
        for variable in self.variables:
            count *= len(variable.values)
        return count

    def matches_device(self, device: "Device") -> bool:
        device.validate()
        return (
            canonical_hash(_device_definition_payload(device))
            == self.base_device_hash
        )

    def require_matching_device(self, device: "Device") -> None:
        if not self.matches_device(device):
            raise ValueError("device does not match the experiment base_device_hash")


__all__ = [
    "BindingScope",
    "DesignVariable",
    "DesignVariableRole",
    "ExperimentSpec",
    "ParameterBinding",
    "ScalarValue",
]
