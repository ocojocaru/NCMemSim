from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .device import Device
from .state import DeviceState


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def raise_for_errors(self) -> None:
        errors = [i for i in self.issues if i.severity == "error"]
        if errors:
            text = "; ".join(f"{i.code}: {i.message}" for i in errors)
            raise ValueError(text)


def validate_probabilities(state: DeviceState, atol: float = 1e-10) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for fg in state.floating_gates:
        arrays = (fg.P0, fg.P1, fg.P2)
        if any(np.any(~np.isfinite(a)) for a in arrays):
            issues.append(ValidationIssue("STATE_NONFINITE", f"{fg.layer_name} contains non-finite probabilities"))
            continue
        if any(np.any((a < -atol) | (a > 1.0 + atol)) for a in arrays):
            issues.append(ValidationIssue("STATE_RANGE", f"{fg.layer_name} probabilities leave [0, 1]"))
        total = fg.P0 + fg.P1 + fg.P2
        if not np.allclose(total, 1.0, rtol=0.0, atol=atol):
            issues.append(ValidationIssue("STATE_NORMALIZATION", f"{fg.layer_name}: P0+P1+P2 != 1"))
    return issues


def validate_device_physics(device: Device) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for layer in device.layers:
        if not np.isfinite(layer.thickness_nm) or layer.thickness_nm <= 0.0:
            issues.append(ValidationIssue("LAYER_THICKNESS", f"{layer.name} has invalid thickness"))
        eps = float(layer.eps_r)
        if not np.isfinite(eps) or eps < 1.0:
            issues.append(ValidationIssue("PERMITTIVITY", f"{layer.name} has eps_r < 1 or non-finite"))
    for fg in device.floating_gates():
        for label, value in (
            ("program barrier", fg.nc_material.phi_barrier_prog_eV),
            ("erase barrier", fg.nc_material.phi_barrier_erase_eV),
            ("effective mass", fg.nc_material.effective_mass_m0),
        ):
            if not np.isfinite(value) or value <= 0.0:
                issues.append(ValidationIssue("NC_PARAMETER", f"{fg.name} has invalid {label}"))
    return issues


def validate_field_profile(profile, applied_voltage_V: float, atol_V: float = 1e-9) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    z = np.asarray(profile.z_nm, dtype=float)
    v = np.asarray(profile.potential_V, dtype=float)
    e = np.asarray(profile.electric_field_V_m, dtype=float)
    if np.any(~np.isfinite(z)) or np.any(~np.isfinite(v)) or np.any(~np.isfinite(e)):
        issues.append(ValidationIssue("FIELD_NONFINITE", "Field profile contains non-finite values"))
    if z.size < 2 or np.any(np.diff(z) <= 0.0):
        issues.append(ValidationIssue("FIELD_GRID", "Field-profile grid is not strictly increasing"))
    if v.size and not np.isclose(v[-1] - v[0], applied_voltage_V, rtol=0.0, atol=atol_V):
        issues.append(ValidationIssue("POTENTIAL_DROP", "Integrated potential drop does not match applied voltage"))
    return issues


def validate_internal_charge_conservation(before_C_m2: Iterable[float], after_C_m2: Iterable[float], atol: float = 1e-15) -> list[ValidationIssue]:
    before = float(np.sum(np.asarray(tuple(before_C_m2), dtype=float)))
    after = float(np.sum(np.asarray(tuple(after_C_m2), dtype=float)))
    if not np.isclose(before, after, rtol=1e-10, atol=atol):
        return [ValidationIssue("CHARGE_CONSERVATION", f"Internal transfer changed total charge by {after-before:.6e} C/m^2")]
    return []


def validate_simulation(device: Device, state: DeviceState, output: dict | None = None) -> ValidationReport:
    issues = validate_device_physics(device) + validate_probabilities(state)
    if output is not None and output.get("field_profile") is not None:
        gate_voltage = float(output.get("field_profile").potential_V[-1] - output.get("field_profile").potential_V[0])
        issues += validate_field_profile(output["field_profile"], gate_voltage)
    return ValidationReport(tuple(issues))
