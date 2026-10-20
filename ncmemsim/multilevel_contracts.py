# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned electrical sequence declarations; no simulation or weight evaluation."""
from __future__ import annotations

from dataclasses import dataclass as _dataclass
import hashlib as _hashlib
import json as _json
import math as _math

from .temperature_context import ResolvedThermalContext as _ResolvedThermalContext
from .state import DeviceState as _DeviceState
from .thermal_reporting import _restore_state, _state_payload

__all__ = [
    "PulseSequenceEvidence", "ElectricalPulseStep", "DarkReadoutPolicy",
    "WeightReferenceMapping", "ElectricalPulseSequence", "ElectricalSequenceExperiment",
]


def _text(value, name):
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(name + " must be nonempty trimmed text")


def _number(value, name, *, positive=False, nonnegative=False):
    if type(value) not in (int, float):
        raise ValueError(name + " must be a real number, not boolean or text")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(name + " must be finite") from exc
    if not _math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(name + " is outside its finite domain")
    return value


def _digest(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(name + " must be a lowercase SHA-256 digest")


def _keys(raw, keys):
    if type(raw) is not dict or set(raw) != set(keys):
        raise ValueError("unsupported multilevel archive fields")


def _canonical(raw):
    try:
        return _json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("finite JSON-compatible multilevel data required") from exc


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate multilevel JSON key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("nonfinite multilevel JSON value: " + value)


def _load(text):
    if type(text) is not str:
        raise ValueError("multilevel JSON text required")
    raw = _json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)
    _canonical(raw)
    return raw


def _match(raw, expected):
    if _canonical(raw) != _canonical(expected):
        raise ValueError("inconsistent multilevel schema, units, conventions or projections")


class _Archive:
    def to_json(self):
        return _canonical(self.to_dict())

    @property
    def contract_hash(self):
        return _hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(_load(text))


@_dataclass(frozen=True)
class PulseSequenceEvidence(_Archive):
    """Source declarations are provenance, not experimental certification."""
    source: str
    locator: str
    data_kind: str
    notes: str

    def __post_init__(self):
        for name in ("source", "locator", "data_kind", "notes"):
            _text(getattr(self, name), name)
        if self.data_kind not in ("synthetic", "literature", "measured_declaration"):
            raise ValueError("unsupported source declaration kind")

    def to_dict(self):
        return {"schema_version": "pulse-sequence-evidence-v1", "source": self.source,
                "locator": self.locator, "data_kind": self.data_kind, "notes": self.notes,
                "experimental_qualification": False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "source", "locator", "data_kind", "notes", "experimental_qualification"))
        obj = cls(*(raw[k] for k in ("source", "locator", "data_kind", "notes")))
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class ElectricalPulseStep(_Archive):
    """One dark constant-voltage segment; role does not assert update direction."""
    step_id: str
    role: str
    gate_voltage_V: float
    duration_s: float
    internal_dt_s: float

    def __post_init__(self):
        _text(self.step_id, "step_id")
        _text(self.role, "role")
        if self.role not in ("program", "erase", "idle"):
            raise ValueError("unsupported electrical step role")
        object.__setattr__(self, "gate_voltage_V", _number(self.gate_voltage_V, "gate voltage"))
        for name in ("duration_s", "internal_dt_s"):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))
        if self.internal_dt_s > self.duration_s:
            raise ValueError("timestep must resolve the declared segment")
        if not _math.isfinite(self.duration_s / self.internal_dt_s):
            raise ValueError("unrepresentable integration subdivision count")

    def to_dict(self):
        return {"schema_version": "electrical-pulse-step-v1", "step_id": self.step_id,
                "role": self.role, "gate_voltage_V": self.gate_voltage_V,
                "duration_s": self.duration_s, "internal_dt_s": self.internal_dt_s,
                "voltage_unit": "V", "time_unit": "s", "illumination": "dark",
                "waveform": "constant_voltage", "occupancy_integrator": "backward_euler"}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "step_id", "role", "gate_voltage_V", "duration_s",
                    "internal_dt_s", "voltage_unit", "time_unit", "illumination",
                    "waveform", "occupancy_integrator"))
        obj = cls(*(raw[k] for k in ("step_id", "role", "gate_voltage_V", "duration_s", "internal_dt_s")))
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class DarkReadoutPolicy(_Archive):
    """Common static signed delta-VFB readout; original state evidence is retained."""
    condition_id: str
    read_voltage_V: float
    evidence: PulseSequenceEvidence

    def __post_init__(self):
        _text(self.condition_id, "condition_id")
        object.__setattr__(self, "read_voltage_V", _number(self.read_voltage_V, "read voltage"))
        if type(self.evidence) is not PulseSequenceEvidence:
            raise ValueError("typed readout evidence required")

    def to_dict(self):
        return {"schema_version": "dark-readout-policy-v1", "condition_id": self.condition_id,
                "read_voltage_V": self.read_voltage_V, "evidence": self.evidence.to_dict(),
                "read_dwell_time_s": 0.0, "illumination": "dark", "observable": "delta_vfb_V",
                "observable_unit": "V", "sampling": "initial_and_after_each_completed_step",
                "state_policy": "retain_original_states_and_audit_zero_dwell_read",
                "probability_audit_atol": 1e-12, "probability_audit_rtol": 0.0}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "condition_id", "read_voltage_V", "evidence",
                    "read_dwell_time_s", "illumination", "observable", "observable_unit",
                    "sampling", "state_policy", "probability_audit_atol", "probability_audit_rtol"))
        obj = cls(raw["condition_id"], raw["read_voltage_V"], PulseSequenceEvidence.from_dict(raw["evidence"]))
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class WeightReferenceMapping(_Archive):
    """Declared fixed reference pair; no normalization or calibration is executed."""
    name: str
    context_hash: str
    readout_hash: str
    low_readout_V: float
    high_readout_V: float
    minimum_span_V: float
    low_preparation: str
    high_preparation: str
    applicability: str
    evidence: PulseSequenceEvidence

    def __post_init__(self):
        for name in ("name", "low_preparation", "high_preparation", "applicability"):
            _text(getattr(self, name), name)
        for name in ("context_hash", "readout_hash"):
            _digest(getattr(self, name), name)
        for name in ("low_readout_V", "high_readout_V"):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        object.__setattr__(self, "minimum_span_V", _number(self.minimum_span_V, "minimum span", positive=True))
        span = _number(self.high_readout_V - self.low_readout_V, "reference span", positive=True)
        if span < self.minimum_span_V:
            raise ValueError("reference span below its declared minimum")
        if type(self.evidence) is not PulseSequenceEvidence:
            raise ValueError("typed reference evidence required")

    def to_dict(self):
        return {"schema_version": "weight-reference-mapping-v1", "name": self.name,
                "context_hash": self.context_hash, "readout_hash": self.readout_hash,
                "low_readout_V": self.low_readout_V, "high_readout_V": self.high_readout_V,
                "minimum_span_V": self.minimum_span_V, "low_preparation": self.low_preparation,
                "high_preparation": self.high_preparation, "applicability": self.applicability,
                "evidence": self.evidence.to_dict(), "formula": "(R-R_low)/(R_high-R_low)",
                "input_observable": "delta_vfb_V", "input_unit": "V", "weight_unit": "1",
                "clipping": "none", "meaning": "readout_derived_proxy_not_conductance"}

    @classmethod
    def from_dict(cls, raw):
        fields = ("name", "context_hash", "readout_hash", "low_readout_V", "high_readout_V",
                  "minimum_span_V", "low_preparation", "high_preparation", "applicability")
        _keys(raw, ("schema_version", *fields, "evidence", "formula", "input_observable",
                    "input_unit", "weight_unit", "clipping", "meaning"))
        obj = cls(*(raw[k] for k in fields), PulseSequenceEvidence.from_dict(raw["evidence"]))
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class ElectricalPulseSequence(_Archive):
    """Finite ordered declaration with no implicit reset, repeat expansion or execution."""
    name: str
    steps: tuple[ElectricalPulseStep, ...]
    readout: DarkReadoutPolicy
    evidence: PulseSequenceEvidence

    def __post_init__(self):
        _text(self.name, "sequence name")
        if type(self.steps) is not tuple or not self.steps or any(type(s) is not ElectricalPulseStep for s in self.steps):
            raise ValueError("nonempty immutable tuple of typed electrical steps required")
        if len({s.step_id for s in self.steps}) != len(self.steps):
            raise ValueError("duplicate sequence step identity")
        if type(self.readout) is not DarkReadoutPolicy or type(self.evidence) is not PulseSequenceEvidence:
            raise ValueError("typed readout and sequence evidence required")
        try:
            total = _math.fsum(s.duration_s for s in self.steps)
        except OverflowError as exc:
            raise ValueError("unrepresentable total sequence duration") from exc
        _number(total, "total duration", positive=True)
        clock = 0.0
        for step in self.steps:
            next_clock = _number(clock + step.duration_s, "sequence clock", positive=True)
            if next_clock <= clock:
                raise ValueError("step duration cannot advance the binary64 sequence clock")
            clock = next_clock

    def to_dict(self):
        return {"schema_version": "electrical-pulse-sequence-v1", "name": self.name,
                "steps": [s.to_dict() for s in self.steps], "readout": self.readout.to_dict(),
                "evidence": self.evidence.to_dict(), "total_duration_s": _math.fsum(s.duration_s for s in self.steps),
                "state_semantics": "continue_each_step_from_previous_final_state",
                "read_count_if_complete": len(self.steps) + 1, "feedback": "open_loop"}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "name", "steps", "readout", "evidence",
                    "total_duration_s", "state_semantics", "read_count_if_complete", "feedback"))
        if type(raw["steps"]) is not list or type(raw["read_count_if_complete"]) is not int:
            raise ValueError("archived step list and integer read count required")
        obj = cls(raw["name"], tuple(ElectricalPulseStep.from_dict(s) for s in raw["steps"]),
                  DarkReadoutPolicy.from_dict(raw["readout"]), PulseSequenceEvidence.from_dict(raw["evidence"]))
        _match(raw, obj.to_dict())
        return obj


@_dataclass(frozen=True)
class ElectricalSequenceExperiment(_Archive):
    """Owned Q1 electrical request. Context restoration is static, never a solver run."""
    name: str
    context: _ResolvedThermalContext
    sequence: ElectricalPulseSequence
    initial_state_json: str
    weight_reference: WeightReferenceMapping | None = None

    def __post_init__(self):
        _text(self.name, "experiment name")
        if type(self.context) is not _ResolvedThermalContext or type(self.sequence) is not ElectricalPulseSequence:
            raise ValueError("typed resolved electrical context and sequence required")
        context = _ResolvedThermalContext.from_dict(self.context.to_dict())
        sequence = ElectricalPulseSequence.from_dict(self.sequence.to_dict())
        raw = _load(self.initial_state_json)
        _keys(raw, ("floating_gates", "time_s", "metadata"))
        clock = _number(raw["time_s"], "initial time", nonnegative=True)
        # Inherited state validation accepts broad NumPy input types. Q archives
        # additionally require explicit finite numeric probability coordinates.
        if type(raw["floating_gates"]) is not list or type(raw["metadata"]) is not dict:
            raise ValueError("archived gate list and state metadata dictionary required")
        for gate in raw["floating_gates"]:
            _keys(gate, ("P0", "P1", "P2", "fg_id", "layer_name", "z_center_nm",
                         "local_field_V_m", "local_potential_V", "metadata"))
            if type(gate["metadata"]) is not dict:
                raise ValueError("floating-gate metadata dictionary required")
            if gate["fg_id"] is not None and type(gate["fg_id"]) is not int:
                raise ValueError("integer floating-gate identity required")
            for key in ("z_center_nm", "local_field_V_m", "local_potential_V"):
                if gate[key] is not None:
                    _number(gate[key], key)
            for key in ("P0", "P1", "P2"):
                if type(gate[key]) is not list:
                    raise ValueError("archived probability list required")
                for value in gate[key]:
                    _number(value, "probability", nonnegative=True)
        state = _restore_state(raw, context.device)
        for step in sequence.steps:
            next_clock = _number(clock + step.duration_s, "absolute sequence clock", positive=True)
            if next_clock <= clock:
                raise ValueError("duration cannot advance the absolute initial-state clock")
            clock = next_clock
        reference = self.weight_reference
        if reference is not None:
            if type(reference) is not WeightReferenceMapping:
                raise ValueError("typed weight reference required")
            if reference.context_hash != context.context_hash or reference.readout_hash != sequence.readout.contract_hash:
                raise ValueError("weight references belong to a different context or readout")
        object.__setattr__(self, "context", context)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "initial_state_json", _canonical(_state_payload(state, context.device)))

    @classmethod
    def from_state(cls, name, context, sequence, initial_state, weight_reference=None):
        if type(context) is not _ResolvedThermalContext or type(initial_state) is not _DeviceState:
            raise ValueError("typed context and initial DeviceState required")
        return cls(name, context, sequence, _canonical(_state_payload(initial_state, context.device)), weight_reference)

    @property
    def initial_state(self):
        return _restore_state(_load(self.initial_state_json), self.context.device)

    def to_dict(self):
        return {"schema_version": "electrical-sequence-experiment-v1", "name": self.name,
                "context": self.context.to_dict(), "context_hash": self.context.context_hash,
                "sequence": self.sequence.to_dict(), "sequence_hash": self.sequence.contract_hash,
                "initial_state": _load(self.initial_state_json),
                "weight_reference": None if self.weight_reference is None else self.weight_reference.to_dict(),
                "scope": "electrical_dark_sequence_declaration", "experimental_qualification": False}

    @classmethod
    def from_dict(cls, raw):
        _keys(raw, ("schema_version", "name", "context", "context_hash", "sequence",
                    "sequence_hash", "initial_state", "weight_reference", "scope", "experimental_qualification"))
        reference = None if raw["weight_reference"] is None else WeightReferenceMapping.from_dict(raw["weight_reference"])
        obj = cls(raw["name"], _ResolvedThermalContext.from_dict(raw["context"]),
                  ElectricalPulseSequence.from_dict(raw["sequence"]), _canonical(raw["initial_state"]), reference)
        _match(raw, obj.to_dict())
        return obj
