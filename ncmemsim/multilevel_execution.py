# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned electrical pulse-train execution and static partial-result verification."""
from __future__ import annotations

from dataclasses import dataclass as _dataclass
import hashlib as _hashlib
import math as _math
import numpy as _np

from .multilevel_contracts import (
    ElectricalSequenceExperiment as _Experiment, _Archive, _canonical, _keys,
    _load, _match, _number, _text,
)
from .thermal_reporting import _restore_state, _state_payload
from .spectral_reporting import _charge
from .ensemble.execution import _runtime

__all__ = ["ElectricalSequenceResult", "run_electrical_sequence"]


def _hash(raw):
    return _hashlib.sha256(_canonical(raw).encode("utf-8")).hexdigest()


def _state(raw, device):
    result = _restore_state(_load(_canonical(raw)), device)
    _number(result.time_s, "state time", nonnegative=True)
    for gate in result.floating_gates:
        if gate.fg_id is not None and type(gate.fg_id) is not int:
            raise ValueError("integer floating-gate identity required")
        if type(gate.metadata) is not dict:
            raise ValueError("floating-gate metadata dictionary required")
        for key in ("z_center_nm", "local_field_V_m", "local_potential_V"):
            if getattr(gate, key) is not None:
                _number(getattr(gate, key), key)
    return result


def _observables(state, context, voltage):
    device, physics, config = context.device, context.physics, context.simulation_config
    charge = _charge(state, device, physics)
    electro = physics.electrostatics.evaluate(
        device, voltage, float(charge.sum()) if len(charge) == 1 else charge,
        config.qfix_C_m2, config.qit_C_m2,
    )
    return {"delta_vfb_V": float(electro.delta_vfb_V),
            "delta_vfb_by_fg_V": electro.delta_vfb_by_fg_V.tolist(),
            "qfg_by_fg_C_m2": charge.tolist(),
            "mean_occupation_by_fg": state.mean_normalized_occupations.tolist()}


def _compare_observables(stored, rebuilt):
    for key, expected in rebuilt.items():
        values = stored[key]
        if type(expected) is list:
            if type(values) is not list or len(values) != len(expected):
                raise ValueError("incomplete per-FG read observation")
            pairs = zip(values, expected, strict=True)
        else:
            pairs = ((values, expected),)
        atol = 1e-20 if key == "qfg_by_fg_C_m2" else 1e-14
        for value, reference in pairs:
            value = _number(value, key)
            if not _math.isclose(value, reference, rel_tol=1e-12, abs_tol=atol):
                raise ValueError("read observable inconsistent with its original stored state: " + key)


def _read_check(raw, source_raw, experiment):
    _keys(raw, ("source_state_hash", "state", "delta_vfb_V", "delta_vfb_by_fg_V",
                "qfg_by_fg_C_m2", "mean_occupation_by_fg", "max_probability_change"))
    if raw["source_state_hash"] != _hash(source_raw):
        raise ValueError("read source-state hash mismatch")
    device = experiment.context.device
    source, read = _state(source_raw, device), _state(raw["state"], device)
    if source.time_s != read.time_s:
        raise ValueError("zero-dwell read advanced time")
    _match(source.metadata, read.metadata)
    differences = []
    for a, b in zip(source.floating_gates, read.floating_gates, strict=True):
        for key in ("fg_id", "layer_name", "z_center_nm", "metadata"):
            _match(getattr(a, key), getattr(b, key))
        for key in ("P0", "P1", "P2"):
            differences.append(float(_np.max(_np.abs(getattr(a, key) - getattr(b, key)))))
    maximum = max(differences)
    tolerance = experiment.sequence.readout.to_dict()["probability_audit_atol"]
    if maximum > tolerance:
        raise ValueError("zero-dwell read probability change exceeds declared audit tolerance")
    _match(raw["max_probability_change"], maximum)
    expected = _observables(read, experiment.context, experiment.sequence.readout.read_voltage_V)
    _compare_observables(raw, expected)


def _perform_read(simulator, source_raw, experiment):
    device = experiment.context.device
    source = _state(source_raw, device)
    out = simulator.relax_voltage(
        source, experiment.sequence.readout.read_voltage_V, dwell_time_s=0.0,
        internal_dt_s=experiment.sequence.steps[0].internal_dt_s,
        light_source=None, occupancy_integrator="backward_euler",
    )
    simulator._require_context()
    read_raw = _state_payload(out["state"], device)
    source = _state(source_raw, device)
    read = _state(read_raw, device)
    maximum = max(float(_np.max(_np.abs(getattr(a, key) - getattr(b, key))))
                  for a, b in zip(source.floating_gates, read.floating_gates, strict=True)
                  for key in ("P0", "P1", "P2"))
    raw = {"source_state_hash": _hash(source_raw), "state": read_raw,
           **{key: out[key].tolist() if hasattr(out[key], "tolist") else out[key]
              for key in ("delta_vfb_V", "delta_vfb_by_fg_V", "qfg_by_fg_C_m2", "mean_occupation_by_fg")},
           "max_probability_change": maximum}
    _read_check(raw, source_raw, experiment)
    return raw


def _projection(raw):
    _keys(raw, ("schema_version", "experiment", "experiment_hash", "runtime",
                "initial_read", "steps", "failure", "summary"))
    if raw["schema_version"] != "electrical-sequence-result-v1":
        raise ValueError("unsupported electrical sequence result version")
    experiment = _Experiment.from_dict(raw["experiment"])
    if raw["experiment_hash"] != experiment.contract_hash:
        raise ValueError("electrical sequence source hash mismatch")
    _keys(raw["runtime"], tuple(_runtime()))
    for value in raw["runtime"].values():
        _text(value, "runtime version")
    if type(raw["steps"]) is not list or len(raw["steps"]) > len(experiment.sequence.steps):
        raise ValueError("bounded ordered completed-step list required")
    device = experiment.context.device
    previous = _load(experiment.initial_state_json)
    reads = []
    if raw["initial_read"] is not None:
        _read_check(raw["initial_read"], previous, experiment)
        reads.append(raw["initial_read"])
    if raw["steps"] and raw["initial_read"] is None:
        raise ValueError("steps require a completed initial read")
    for index, event in enumerate(raw["steps"]):
        _keys(event, ("step_index", "step_id", "initial_state", "final_state", "read"))
        step = experiment.sequence.steps[index]
        if type(event["step_index"]) is not int or event["step_index"] != index or event["step_id"] != step.step_id:
            raise ValueError("completed step identity/order mismatch")
        _match(event["initial_state"], previous)
        final = _state(event["final_state"], device)
        if final.time_s != previous["time_s"] + step.duration_s:
            raise ValueError("physical step clock differs from declared duration")
        if event["read"] is not None:
            _read_check(event["read"], event["final_state"], experiment)
            reads.append(event["read"])
        elif index != len(raw["steps"]) - 1:
            raise ValueError("execution continued after an uncompleted read")
        previous = event["final_state"]
    failure = raw["failure"]
    count = len(raw["steps"])
    attempted_steps = count
    attempted_reads = len(reads)
    if failure is None:
        if count != len(experiment.sequence.steps) or len(reads) != count + 1:
            raise ValueError("success requires all physical steps and all reads")
    else:
        _keys(failure, ("stage", "step_index", "exception_type", "message"))
        for key in ("stage", "exception_type", "message"):
            _text(failure[key], key)
        stage, index = failure["stage"], failure["step_index"]
        if stage in ("setup", "initial_read"):
            if index is not None or count or reads:
                raise ValueError("inconsistent setup/initial-read failure prefix")
            attempted_reads = int(stage == "initial_read")
        elif stage == "step":
            if type(index) is not int or index != count or count >= len(experiment.sequence.steps) or len(reads) != count + 1:
                raise ValueError("inconsistent physical-step failure prefix")
            attempted_steps += 1
        elif stage == "read":
            if type(index) is not int or index != count - 1 or count < 1 or len(reads) != count or raw["steps"][-1]["read"] is not None:
                raise ValueError("inconsistent post-step read failure prefix")
            attempted_reads += 1
        else:
            raise ValueError("unsupported sequence failure stage")
    return {"status": "completed" if failure is None else "failed",
            "requested_step_count": len(experiment.sequence.steps),
            "attempted_step_count": attempted_steps, "completed_step_count": count,
            "requested_read_count": len(experiment.sequence.steps) + 1,
            "attempted_read_count": attempted_reads, "completed_read_count": len(reads),
            "initial_time_s": _load(experiment.initial_state_json)["time_s"],
            "final_time_s": previous["time_s"],
            "elapsed_physical_time_s": previous["time_s"] - _load(experiment.initial_state_json)["time_s"],
            "read_delta_vfb_V": [read["delta_vfb_V"] for read in reads],
            "weight_evaluation": "not_performed", "experimental_qualification": False}


@_dataclass(frozen=True)
class ElectricalSequenceResult(_Archive):
    """Original physical/read states and validated static summaries, without replay."""
    record_json: str

    def __post_init__(self):
        raw = _load(self.record_json)
        summary = _projection(raw)
        _match(raw["summary"], summary)
        object.__setattr__(self, "record_json", _canonical(raw))

    def to_dict(self):
        return _load(self.record_json)

    @property
    def summary(self):
        return self.to_dict()["summary"]

    @property
    def final_state(self):
        raw = self.to_dict()
        experiment = _Experiment.from_dict(raw["experiment"])
        state = raw["steps"][-1]["final_state"] if raw["steps"] else raw["experiment"]["initial_state"]
        return _state(state, experiment.context.device)

    @classmethod
    def from_dict(cls, raw):
        return cls(_canonical(raw))


def run_electrical_sequence(experiment):
    """Execute an isolated request; preserve the physical prefix on step/read failure."""
    if type(experiment) is not _Experiment:
        raise ValueError("owned electrical sequence experiment required")
    experiment = _Experiment.from_dict(experiment.to_dict())
    raw = {"schema_version": "electrical-sequence-result-v1", "experiment": experiment.to_dict(),
           "experiment_hash": experiment.contract_hash, "runtime": _runtime(),
           "initial_read": None, "steps": [], "failure": None, "summary": None}
    stage, index = "setup", None
    try:
        simulator = experiment.context.create_simulator()
        stage = "initial_read"
        current = _load(experiment.initial_state_json)
        raw["initial_read"] = _perform_read(simulator, current, experiment)
        for index, step in enumerate(experiment.sequence.steps):
            stage = "step"
            out = simulator.relax_voltage(
                _state(current, simulator.device), step.gate_voltage_V,
                dwell_time_s=step.duration_s, internal_dt_s=step.internal_dt_s,
                light_source=None, occupancy_integrator="backward_euler",
            )
            simulator._require_context()
            final = _state_payload(out["state"], simulator.device)
            _state(final, simulator.device)
            if final["time_s"] != current["time_s"] + step.duration_s:
                raise ValueError("solver returned an inconsistent physical step clock")
            event = {"step_index": index, "step_id": step.step_id,
                     "initial_state": current, "final_state": final, "read": None}
            raw["steps"].append(event)
            current = final
            stage = "read"
            event["read"] = _perform_read(simulator, current, experiment)
    except Exception as exc:
        raw["failure"] = {"stage": stage, "step_index": index,
                          "exception_type": type(exc).__module__ + "." + type(exc).__qualname__,
                          "message": str(exc).strip() or type(exc).__name__}
    raw["summary"] = _projection(raw)
    return ElectricalSequenceResult.from_dict(raw)
