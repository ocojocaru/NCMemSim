"""Controlled DTCO bindings for electrical and optical operating conditions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import math
from typing import Iterable, TypeAlias

from ..electro_optical_program_protocol import ElectroOpticalProgramPulseReadProtocol
from ..program_protocol import ProgramPulseReadProtocol
from .spec import BindingScope, ParameterBinding, ScalarValue


OperatingProtocol: TypeAlias = (
    ProgramPulseReadProtocol | ElectroOpticalProgramPulseReadProtocol
)


class OperatingBindingError(ValueError):
    """Raised when an operating-condition binding cannot be applied safely."""


def _numeric(value: ScalarValue, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperatingBindingError(f"{label} requires a numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise OperatingBindingError(f"{label} must be finite")
    return result


def _electrical_protocol(
    protocol: OperatingProtocol,
) -> ProgramPulseReadProtocol:
    if isinstance(protocol, ProgramPulseReadProtocol):
        return protocol
    if isinstance(protocol, ElectroOpticalProgramPulseReadProtocol):
        return protocol.electrical_protocol
    raise TypeError(
        "protocol must be ProgramPulseReadProtocol or "
        "ElectroOpticalProgramPulseReadProtocol"
    )


def _replace_electrical_protocol(
    protocol: OperatingProtocol,
    electrical: ProgramPulseReadProtocol,
) -> OperatingProtocol:
    if isinstance(protocol, ProgramPulseReadProtocol):
        return electrical
    return replace(protocol, electrical_protocol=electrical)


def _apply_one(
    protocol: OperatingProtocol,
    binding: ParameterBinding,
    value: ScalarValue,
) -> OperatingProtocol:
    if binding.scope is not BindingScope.OPERATING:
        raise OperatingBindingError(
            "operating application requires BindingScope.OPERATING"
        )

    path = binding.path
    electrical_fields = {
        ("program", "voltage_V"): "program_voltage_V",
        ("program", "time_s"): "programming_time_s",
        ("read", "voltage_V"): "read_voltage_V",
        ("program", "internal_dt_s"): "program_internal_dt_s",
    }

    if path in electrical_fields:
        numeric = _numeric(value, label=".".join(path))
        electrical = replace(
            _electrical_protocol(protocol),
            **{electrical_fields[path]: numeric},
        )
        return _replace_electrical_protocol(protocol, electrical)

    if path == ("optical", "wavelength_nm"):
        if not isinstance(protocol, ElectroOpticalProgramPulseReadProtocol):
            raise OperatingBindingError(
                "optical bindings require ElectroOpticalProgramPulseReadProtocol"
            )
        if protocol.light_source.source_type not in {"led", "laser"}:
            raise OperatingBindingError(
                "wavelength binding requires an LED or laser light source"
            )
        wavelength_nm = _numeric(value, label="optical.wavelength_nm")
        if wavelength_nm <= 0.0:
            raise OperatingBindingError(
                "optical.wavelength_nm must be strictly positive"
            )
        source = replace(protocol.light_source, wavelength_nm=wavelength_nm)
        return replace(protocol, light_source=source)

    if path == ("optical", "power_density_W_m2"):
        if not isinstance(protocol, ElectroOpticalProgramPulseReadProtocol):
            raise OperatingBindingError(
                "optical bindings require ElectroOpticalProgramPulseReadProtocol"
            )
        power = _numeric(value, label="optical.power_density_W_m2")
        if power <= 0.0:
            raise OperatingBindingError(
                "optical.power_density_W_m2 must be strictly positive"
            )
        source = replace(protocol.light_source, power_density_W_m2=power)
        return replace(protocol, light_source=source)

    raise OperatingBindingError(
        f"unsupported operating binding path: {path!r}"
    )


def apply_operating_binding(
    base_protocol: OperatingProtocol,
    binding: ParameterBinding,
    value: ScalarValue,
) -> OperatingProtocol:
    """Apply one operating binding by reconstructing frozen dataclasses."""

    return apply_operating_bindings(base_protocol, ((binding, value),))


def apply_operating_bindings(
    base_protocol: OperatingProtocol,
    assignments: Iterable[tuple[ParameterBinding, ScalarValue]],
) -> OperatingProtocol:
    """Apply several operating bindings atomically to an immutable baseline."""

    if not isinstance(
        base_protocol,
        (ProgramPulseReadProtocol, ElectroOpticalProgramPulseReadProtocol),
    ):
        raise TypeError(
            "base_protocol must be ProgramPulseReadProtocol or "
            "ElectroOpticalProgramPulseReadProtocol"
        )

    items = tuple(assignments)
    seen: set[str] = set()
    for binding, _ in items:
        if not isinstance(binding, ParameterBinding):
            raise TypeError("assignments must use ParameterBinding instances")
        if binding.binding_id in seen:
            raise OperatingBindingError("duplicate operating binding assignment")
        seen.add(binding.binding_id)

    candidate: OperatingProtocol = deepcopy(base_protocol)
    try:
        for binding, value in items:
            candidate = _apply_one(candidate, binding, value)
    except OperatingBindingError:
        raise
    except (TypeError, ValueError, AttributeError) as exc:
        raise OperatingBindingError(
            f"operating validation failed after binding application: {exc}"
        ) from exc

    return candidate


__all__ = [
    "OperatingBindingError",
    "OperatingProtocol",
    "apply_operating_binding",
    "apply_operating_bindings",
]
