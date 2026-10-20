# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic three-level electrical preparation with a common dark readout."""
from __future__ import annotations
import argparse
from dataclasses import replace
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
from ncmemsim.multilevel_analysis import MultilevelPreparation, MultilevelStudyPlan, MultilevelStudyResult, run_multilevel_study


def build_plan(internal_dt_s=1e-9):
    device = DeviceBuilder.v2(n_fgs=1)
    context = ThermalContext.from_nominal(device).resolve()
    evidence = PulseSequenceEvidence(
        "Q3 synthetic electrical reference", "example code", "synthetic",
        "Assumed pulse histories and deterministic 1 mV minimum separation, not measured noise or capacity.",
    )
    readout = DarkReadoutPolicy("common-dark-0V", 0., evidence)
    initial = DeviceState.empty_for_device(device)
    levels = []
    # Positive programming adds electron occupation and makes signed delta-VFB
    # more negative in this context. Longer preparation is therefore declared first.
    for label, duration in (("L0", 1e-6), ("L1", 5e-7), ("L2", 1e-7)):
        seq = ElectricalPulseSequence(label + " preparation", (
            ElectricalPulseStep("write", "program", 6., duration, internal_dt_s),
        ), readout, evidence)
        exp = ElectricalSequenceExperiment.from_state(label, context, seq, initial)
        levels.append(MultilevelPreparation(label, exp, 0.))
    return MultilevelStudyPlan("Q3 controlled three-level separation", tuple(levels), .001, "deterministic", evidence)


def run_reference():
    return run_multilevel_study(build_plan())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    result = MultilevelStudyResult.from_json(args.input.read_text(encoding="utf-8")) if args.input else run_reference()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.to_dict(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"result_hash": result.contract_hash, "summary": result.summary}, allow_nan=False))
