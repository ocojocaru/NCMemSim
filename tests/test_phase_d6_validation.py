from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ncmemsim import (
    DeviceBuilder,
    DeviceState,
    Simulator,
    build_golden_suite,
    build_reproducibility_manifest,
    compare_golden,
    run_benchmark_suite,
    validate_internal_charge_conservation,
    validate_simulation,
)


def test_reference_devices_pass_physics_validation():
    for n_fgs in (1, 2, 3):
        device = DeviceBuilder.v2(n_fgs)
        sim = Simulator(device)
        state = DeviceState.empty_for_device(device)
        out = sim.relax_voltage(state, 2.0, dwell_time_s=0.0, internal_dt_s=1e-5)
        report = validate_simulation(device, out["state"], out)
        assert report.passed, report.issues


def test_golden_regression_suite_matches_versioned_file():
    expected_path = Path(__file__).parents[1] / "validation" / "golden_reference" / "phase_d6_v0.9.0.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    errors = compare_golden(build_golden_suite(), expected)
    assert errors == []


def test_reproducibility_hashes_are_deterministic_and_config_sensitive():
    device = DeviceBuilder.v2(2)
    a = build_reproducibility_manifest(device, simulation_config={"voltage_V": 2.0})
    b = build_reproducibility_manifest(device, simulation_config={"voltage_V": 2.0})
    c = build_reproducibility_manifest(device, simulation_config={"voltage_V": 3.0})
    assert a["device_hash"] == b["device_hash"]
    assert a["simulation_hash"] == b["simulation_hash"]
    assert a["simulation_hash"] != c["simulation_hash"]
    assert len(a["device_hash"]) == 64
    assert a["schema_version"] == 2


def test_charge_conservation_helper_detects_error():
    assert validate_internal_charge_conservation([1.0, 2.0], [1.5, 1.5]) == []
    issues = validate_internal_charge_conservation([1.0, 2.0], [1.5, 1.6])
    assert issues and issues[0].code == "CHARGE_CONSERVATION"


def test_benchmark_suite_reports_all_supported_fg_counts():
    records = run_benchmark_suite(repeats=1)
    assert [r.n_fgs for r in records] == [1, 2, 3]
    assert all(r.elapsed_s >= 0.0 for r in records)
    assert all(r.peak_memory_bytes > 0 for r in records)
    assert all(np.isfinite(r.qfg_C_m2) for r in records)
