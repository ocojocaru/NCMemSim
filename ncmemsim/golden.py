from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .builder import DeviceBuilder
from .retention import RetentionConfig
from .simulator import Simulator
from .state import DeviceState


def _round(value: Any, digits: int = 14) -> Any:
    if isinstance(value, np.ndarray):
        return [_round(v, digits) for v in value.tolist()]
    if isinstance(value, (np.floating, float)):
        return round(float(value), digits)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (list, tuple)):
        return [_round(v, digits) for v in value]
    return value


def reference_case(n_fgs: int) -> dict[str, Any]:
    device = DeviceBuilder.v2(n_fgs)
    simulator = Simulator(device)
    state = DeviceState.empty_for_device(device)
    out = simulator.relax_voltage(state, gate_voltage_V=2.0, dwell_time_s=2e-5, internal_dt_s=1e-5)
    return {
        "device": device.name,
        "n_fgs": n_fgs,
        "qfg_C_m2": _round(out["qfg_C_m2"]),
        "qfg_by_fg_C_m2": _round(out["qfg_by_fg_C_m2"]),
        "delta_vfb_V": _round(out["delta_vfb_V"]),
        "local_fields_V_m": _round(out["electrostatic_local_field_by_fg_V_m"]),
        "mean_occupation_by_fg": _round(out["mean_occupation_by_fg"]),
        "transport_transmission": _round(out["transport_transmission_by_link"]),
    }


def retention_reference_case() -> dict[str, Any]:
    device = DeviceBuilder.v2(3)
    simulator = Simulator(device)
    state = DeviceState.empty_for_device(device)
    programmed = simulator.relax_voltage(state, 4.0, dwell_time_s=5e-5, internal_dt_s=1e-5)["state"]
    result = simulator.simulate_retention(
        programmed,
        RetentionConfig(total_time_s=1e-3, initial_dt_s=1e-7, maximum_dt_s=1e-4, output_points=9),
    )
    return {
        "device": device.name,
        "time_s": _round(result.time_s),
        "qfg_C_m2": _round(result.qfg_C_m2),
        "delta_vfb_V": _round(result.delta_vfb_V),
        "final_occupation_by_fg": _round(result.mean_occupation_by_fg[-1]),
    }


def build_golden_suite() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "cases": {f"v2_{n}fg": reference_case(n) for n in (1, 2, 3)},
        "retention": retention_reference_case(),
    }


def write_golden_suite(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_golden_suite(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def compare_golden(actual: dict[str, Any], expected: dict[str, Any], rtol: float = 1e-10, atol: float = 1e-13) -> list[str]:
    errors: list[str] = []

    def walk(a: Any, e: Any, path: str) -> None:
        if isinstance(e, dict):
            if not isinstance(a, dict):
                errors.append(f"{path}: type mismatch")
                return
            for key in e:
                if key not in a:
                    errors.append(f"{path}.{key}: missing")
                else:
                    walk(a[key], e[key], f"{path}.{key}")
        elif isinstance(e, list):
            try:
                aa = np.asarray(a, dtype=float)
                ee = np.asarray(e, dtype=float)
                if aa.shape != ee.shape or not np.allclose(aa, ee, rtol=rtol, atol=atol):
                    errors.append(f"{path}: numeric mismatch")
            except (TypeError, ValueError):
                if a != e:
                    errors.append(f"{path}: value mismatch")
        elif isinstance(e, (int, float)):
            if not np.isclose(float(a), float(e), rtol=rtol, atol=atol):
                errors.append(f"{path}: {a} != {e}")
        elif a != e:
            errors.append(f"{path}: {a!r} != {e!r}")

    walk(actual, expected, "root")
    return errors
