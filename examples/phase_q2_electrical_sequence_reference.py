# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled electrical pulse train; synthetic reference, not multilevel qualification."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncmemsim import DeviceBuilder, DeviceState
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.multilevel_contracts import (
    PulseSequenceEvidence, ElectricalPulseStep, DarkReadoutPolicy,
    ElectricalPulseSequence, ElectricalSequenceExperiment,
)
from ncmemsim.multilevel_execution import ElectricalSequenceResult, run_electrical_sequence


def build_experiment(internal_dt_s=1e-10):
    device = DeviceBuilder.v2(n_fgs=1)
    context = ThermalContext.from_nominal(device).resolve()
    evidence = PulseSequenceEvidence(
        "Q2 synthetic electrical reference", "example code", "synthetic",
        "Assumed initial occupation, pulse voltages/durations and dark read. No measured qualification.",
    )
    initial = DeviceState.empty_for_device(device)
    initial.floating_gates[0].P0[:] = .8
    initial.floating_gates[0].P1[:] = .2
    steps = (
        ElectricalPulseStep("write-1", "program", 2., 1e-8, internal_dt_s),
        ElectricalPulseStep("idle-1", "idle", 0., 2e-9, internal_dt_s),
        ElectricalPulseStep("write-2", "program", 2., 1e-8, internal_dt_s),
        ElectricalPulseStep("erase-1", "erase", -2., 1e-8, internal_dt_s),
    )
    sequence = ElectricalPulseSequence(
        "two writes, idle and erase", steps, DarkReadoutPolicy("dark-0V", 0., evidence), evidence,
    )
    return ElectricalSequenceExperiment.from_state("Q2 controlled reference", context, sequence, initial)


def run_reference():
    return run_electrical_sequence(build_experiment())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    result = (ElectricalSequenceResult.from_json(args.input.read_text(encoding="utf-8"))
              if args.input else run_reference())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.to_dict(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"result_hash": result.contract_hash, "summary": result.summary}, allow_nan=False))
