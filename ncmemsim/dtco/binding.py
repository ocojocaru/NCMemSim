"""Controlled application of DTCO device bindings.

Phase G1b applies only ``BindingScope.DEVICE`` bindings. The base device is
never mutated: a deep copy is created, bindings are resolved through a strict
allow-list, and the resulting device is validated before it is returned.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping

from ..device import Device
from ..layers import FloatingGateLayer
from .spec import BindingScope, ExperimentSpec, ParameterBinding, ScalarValue


class BindingApplicationError(ValueError):
    """Raised when a DTCO binding cannot be applied safely."""


_DEVICE_ATTRIBUTES = {
    "gate_work_function_eV",
    "substrate_doping_m3",
    "temperature_K",
}

_LAYER_ATTRIBUTES = {
    "thickness_nm",
}

_FLOATING_GATE_ATTRIBUTES = {
    "thickness_nm",
    "nc_diameter_nm",
    "nc_volume_fraction",
    "electrically_active_fraction",
    "grid_points",
}


def _coerce_for_target(current: object, value: ScalarValue, *, label: str) -> object:
    if isinstance(current, bool):
        raise BindingApplicationError(f"{label} targets an unsupported boolean field")

    if isinstance(current, int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise BindingApplicationError(
                f"{label} requires an integer value, got {type(value).__name__}"
            )
        return value

    if isinstance(current, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BindingApplicationError(
                f"{label} requires a numeric value, got {type(value).__name__}"
            )
        return float(value)

    if isinstance(current, str):
        if not isinstance(value, str):
            raise BindingApplicationError(
                f"{label} requires a string value, got {type(value).__name__}"
            )
        return value

    raise BindingApplicationError(
        f"{label} targets unsupported field type {type(current).__name__}"
    )


def _resolve_device_target(
    device: Device,
    binding: ParameterBinding,
) -> tuple[object, str]:
    if binding.scope is not BindingScope.DEVICE:
        raise BindingApplicationError(
            "G1b supports only BindingScope.DEVICE bindings"
        )

    path = binding.path

    if len(path) == 1:
        attribute = path[0]
        if attribute not in _DEVICE_ATTRIBUTES:
            raise BindingApplicationError(
                f"unsupported device binding path: {path!r}"
            )
        return device, attribute

    if len(path) == 3 and path[0] == "layers":
        layer_name = path[1]
        attribute = path[2]

        try:
            layer = device.get_layer(layer_name)
        except KeyError as exc:
            raise BindingApplicationError(
                f"unknown layer in binding: {layer_name!r}"
            ) from exc

        allowed = (
            _FLOATING_GATE_ATTRIBUTES
            if isinstance(layer, FloatingGateLayer)
            else _LAYER_ATTRIBUTES
        )
        if attribute not in allowed:
            raise BindingApplicationError(
                f"unsupported attribute {attribute!r} for layer {layer_name!r}"
            )
        return layer, attribute

    raise BindingApplicationError(f"unsupported device binding path: {path!r}")


def _apply_binding_in_place(
    device: Device,
    binding: ParameterBinding,
    value: ScalarValue,
) -> None:
    target, attribute = _resolve_device_target(device, binding)
    current = getattr(target, attribute)
    label = ".".join(binding.path)
    safe_value = _coerce_for_target(current, value, label=label)
    setattr(target, attribute, safe_value)


def apply_device_binding(
    base_device: Device,
    binding: ParameterBinding,
    value: ScalarValue,
) -> Device:
    """Apply one device binding to a validated deep copy of ``base_device``."""

    return apply_device_bindings(base_device, ((binding, value),))


def apply_device_bindings(
    base_device: Device,
    assignments: Iterable[tuple[ParameterBinding, ScalarValue]],
) -> Device:
    """Apply multiple device bindings atomically to one validated deep copy."""

    base_device.validate()
    items = tuple(assignments)

    binding_ids: set[str] = set()
    for binding, _ in items:
        if not isinstance(binding, ParameterBinding):
            raise TypeError("assignments must use ParameterBinding instances")
        if binding.binding_id in binding_ids:
            raise BindingApplicationError("duplicate binding assignment")
        binding_ids.add(binding.binding_id)

    candidate = deepcopy(base_device)

    try:
        for binding, value in items:
            _apply_binding_in_place(candidate, binding, value)
        candidate.validate()
    except BindingApplicationError:
        raise
    except (TypeError, ValueError, AttributeError) as exc:
        raise BindingApplicationError(
            f"device validation failed after binding application: {exc}"
        ) from exc

    return candidate


def apply_experiment_design_point(
    spec: ExperimentSpec,
    base_device: Device,
    values_by_name: Mapping[str, ScalarValue],
) -> Device:
    """Apply one complete device-only experiment point to a deep copy."""

    if not isinstance(spec, ExperimentSpec):
        raise TypeError("spec must be an ExperimentSpec")

    spec.require_matching_device(base_device)

    expected_names = tuple(variable.name for variable in spec.variables)
    provided_names = tuple(values_by_name.keys())

    missing = [name for name in expected_names if name not in values_by_name]
    extra = [name for name in provided_names if name not in expected_names]
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing!r}")
        if extra:
            details.append(f"extra={extra!r}")
        raise BindingApplicationError(
            "design-point assignments must match experiment variables exactly: "
            + ", ".join(details)
        )

    assignments: list[tuple[ParameterBinding, ScalarValue]] = []
    for variable in spec.variables:
        if variable.binding.scope is not BindingScope.DEVICE:
            raise BindingApplicationError(
                "G1b experiment application supports only device-scope variables"
            )

        value = values_by_name[variable.name]
        if value not in variable.values:
            raise BindingApplicationError(
                f"value {value!r} is outside declared domain for "
                f"{variable.name!r}"
            )

        assignments.append((variable.binding, value))

    return apply_device_bindings(base_device, assignments)


__all__ = [
    "BindingApplicationError",
    "apply_device_binding",
    "apply_device_bindings",
    "apply_experiment_design_point",
]
