# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Acceptance checks for the controlled Phase T3 reference population."""

import json
import math

import pytest

from examples.phase_t3_finite_confinement_reference import run_reference
from ncmemsim.hashing import canonical_hash


@pytest.fixture(scope="module")
def report():
    return run_reference()


def test_one_input_changes_per_sweep(report):
    sweeps = report["single_carrier_sweeps"]
    assert set(sweeps) == {"radius_m", "depth_J", "inside_mass_m0", "outside_mass_m0"}
    for axis, rows in sweeps.items():
        requests = [row["finite"]["request"] for row in rows]
        assert len({request[axis] for request in requests}) == 3
        assert all(
            {key for key in requests[0] if request[key] != requests[0][key]} == {axis}
            for request in requests[1:]
        )
        for row in rows:
            finite = row["finite"]
            if finite["status"] == "bound":
                assert 0 < finite["energy_J"] < row["infinite_energy_J"]
                assert math.isclose(finite["inside_probability"] + finite["outside_probability"], 1)
            else:
                assert finite["status"] == "no_bound_state"
                assert finite["energy_J"] is None


def test_controlled_trends_and_infinite_limit(report):
    sweeps = report["single_carrier_sweeps"]
    for axis in ("radius_m", "inside_mass_m0", "outside_mass_m0"):
        energies = [row["finite"]["energy_J"] for row in sweeps[axis]]
        assert energies[0] > energies[1] > energies[2] > 0
    shallow, nominal, deep = sweeps["depth_J"]
    assert shallow["finite"]["status"] == "no_bound_state"
    assert shallow["infinite_energy_J"] == nominal["infinite_energy_J"] == deep["infinite_energy_J"]
    assert nominal["finite"]["energy_J"] < deep["finite"]["energy_J"]
    assert deep["finite"]["energy_J"] / deep["infinite_energy_J"] > 0.98
    assert deep["finite"]["outside_probability"] < nominal["finite"]["outside_probability"]


def test_pair_retains_unavailable_correction(report):
    assert report["pair_counts"] == {"attempted": 3, "available": 2, "unavailable": 1}
    unavailable, *available = report["pairs"]
    assert unavailable["electron"]["finite"]["status"] == "bound"
    assert unavailable["hole"]["finite"]["status"] == "no_bound_state"
    assert unavailable["finite_kinetic_sum_J"] is None
    assert unavailable["infinite_kinetic_sum_J"] > 0
    for pair in available:
        assert pair["status"] == "available"
        assert pair["finite_kinetic_sum_J"] == sum(
            pair[carrier]["finite"]["energy_J"] for carrier in ("electron", "hole")
        )
        assert 0 < pair["finite_kinetic_sum_J"] < pair["infinite_kinetic_sum_J"]


def test_reference_is_reproducible_strict_json(report):
    assert json.loads(json.dumps(report, allow_nan=False)) == report == run_reference()
    payload = {key: value for key, value in report.items() if key != "reference_hash"}
    assert report["reference_hash"] == canonical_hash(payload)
