"""Serial propagation of exact sample manifests through isolated candidates."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import json
import platform
import re
from typing import Any, Callable
import numpy as np
from .._version import __version__
from ..device import Device
from ..hashing import canonical_hash
from .binding import apply_device_bindings
from .operating import OperatingProtocol, apply_operating_bindings
from .sampling import SampleManifest
from .spec import BindingScope, ScalarValue, _device_definition_payload, _operating_definition_payload
from .sweep import _json_snapshot
import math

_DIGEST = re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class SamplePoint:
    """An ordered assignment tied to the exact sample manifest."""

    manifest_hash: str
    index: int
    values_by_name: tuple[tuple[str, ScalarValue], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values_by_name", tuple(
            (name, value) for name, value in self.values_by_name
        ))
        if not isinstance(self.manifest_hash, str) or not _DIGEST.fullmatch(
            self.manifest_hash
        ):
            raise ValueError("manifest_hash must be a lowercase SHA-256 digest")
        if type(self.index) is not int or self.index < 0:
            raise ValueError("point index must be a nonnegative integer")
        if not self.values_by_name:
            raise ValueError("point requires assignments")
        names = []
        for name, value in self.values_by_name:
            if not isinstance(name, str) or not name or name != name.strip():
                raise ValueError("assignment names must be non-empty without outer whitespace")
            if type(value) is not float:
                raise TypeError("sample assignments must be exact manifest floats")
            if isinstance(value, str) and (not value or value != value.strip()):
                raise ValueError("categorical assignments cannot have outer whitespace")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("numeric assignments must be finite")
            names.append(name)
        if len(set(names)) != len(names):
            raise ValueError("assignment names must be unique")

    @property
    def assignments(self) -> dict[str, ScalarValue]:
        return dict(self.values_by_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-sample-point-v1",
            "manifest_hash": self.manifest_hash,
            "index": self.index,
            "assignments": [
                {"name": name, "value": value} for name, value in self.values_by_name
            ],
        }

    @property
    def point_hash(self) -> str:
        return canonical_hash(self.to_dict())

@dataclass(frozen=True)
class SamplePointResult:
    """A success snapshot or a failure with the stage at which it occurred."""

    point: SamplePoint
    status: str
    output_json: str | None = None
    failure_stage: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.point, SamplePoint):
            raise TypeError("point must be a SamplePoint")
        if self.status == "success":
            if any(v is not None for v in (
                self.failure_stage, self.error_type, self.error_message
            )):
                raise ValueError("successful points cannot contain failure details")
            payload = json.loads(self.output_json) if self.output_json is not None else None
            if type(payload) is not dict:
                raise TypeError("successful output must be a JSON object")
            object.__setattr__(self, "output_json", _json_snapshot(payload))
        elif self.status == "failed":
            if self.output_json is not None:
                raise ValueError("failed points cannot contain output")
            if self.failure_stage not in ("application", "evaluation", "serialization"):
                raise ValueError("invalid failure stage")
            if not isinstance(self.error_type, str) or not self.error_type:
                raise ValueError("failed points require error_type")
            if not isinstance(self.error_message, str):
                raise TypeError("failed points require a string error_message")
        else:
            raise ValueError("status must be success or failed")

    @property
    def output(self) -> dict[str, Any] | None:
        return json.loads(self.output_json) if self.output_json is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "point": self.point.to_dict(),
            "point_hash": self.point.point_hash,
            "status": self.status,
            "output": self.output,
            "failure": None if self.status == "success" else {
                "stage": self.failure_stage,
                "type": self.error_type,
                "message": self.error_message,
            },
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class PropagationResult:
    """Ordered successes/failures linked to manifest, nominal baseline and evaluator."""
    manifest: SampleManifest
    study_json: str
    points: tuple[SamplePointResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, SampleManifest):
            raise TypeError("manifest must be SampleManifest")
        manifest_hash = self.manifest.manifest_hash
        study = json.loads(self.study_json)
        if type(study) is not dict:
            raise TypeError("study must be a JSON object")
        object.__setattr__(self, "study_json", _json_snapshot(study))
        if study.get("schema_version") != "dtco-propagation-v1" or study.get("manifest_hash") != manifest_hash:
            raise ValueError("study identity mismatch")
        if study.get("execution") != "serial-isolated" or study.get("ordering") != "manifest-order":
            raise ValueError("unsupported propagation policy")
        if set(study) != {"schema_version", "manifest_hash", "nominal", "evaluation", "execution", "ordering", "runtime"}:
            raise ValueError("study fields mismatch")
        runtime = study["runtime"]
        if type(runtime) is not dict or set(runtime) != {"python", "python_implementation", "numpy", "ncmemsim"} or not all(isinstance(v, str) and v for v in runtime.values()):
            raise ValueError("study requires runtime provenance")
        nominal = study.get("nominal")
        evaluation = study.get("evaluation")
        if type(nominal) is not dict or type(nominal.get("device")) is not dict:
            raise ValueError("study requires a nominal device definition")
        if type(evaluation) is not dict or type(evaluation.get("parameters")) is not dict:
            raise ValueError("study requires evaluator identity and parameters")
        label = evaluation.get("id")
        if not isinstance(label, str) or not label or label != label.strip():
            raise ValueError("invalid evaluator id")
        points = tuple(self.points)
        if len(points) != self.manifest.spec.sample_count:
            raise ValueError("every manifest sample must have a result")
        names = tuple(v.name for v in self.manifest.spec.variations)
        for i, result in enumerate(points):
            if not isinstance(result, SamplePointResult):
                raise TypeError("points must be SamplePointResult")
            if result.point.index != i or result.point.manifest_hash != manifest_hash:
                raise ValueError("sample order or manifest identity mismatch")
            if result.point.values_by_name != tuple(zip(names, self.manifest.values[i])):
                raise ValueError("assignments differ from exact manifest")
        object.__setattr__(self, "points", points)

    @property
    def nominal_hash(self) -> str:
        return canonical_hash(json.loads(self.study_json)["nominal"])

    @property
    def study_hash(self) -> str:
        return canonical_hash(json.loads(self.study_json))

    @property
    def success_count(self) -> int:
        return sum(p.status == "success" for p in self.points)

    @property
    def failure_count(self) -> int:
        return len(self.points) - self.success_count

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "dtco-propagation-result-v1",
                "study": json.loads(self.study_json), "study_hash": self.study_hash,
                "nominal_hash": self.nominal_hash, "manifest": self.manifest.to_dict(),
                "points": [p.to_dict() for p in self.points],
                "success_count": self.success_count, "failure_count": self.failure_count}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


SampleEvaluator = Callable[[Device, OperatingProtocol | None, SamplePoint], dict[str, Any]]


def propagate_samples(
    manifest: SampleManifest,
    base_device: Device,
    evaluator: SampleEvaluator,
    *,
    evaluation_id: str,
    evaluation_parameters: dict[str, Any] | None = None,
    base_protocol: OperatingProtocol | None = None,
) -> PropagationResult:
    """Use stored values without sampling, serially and without dropping failures.

    Setup/context errors fail before callbacks. Ordinary per-sample application,
    evaluation and JSON serialization errors become ordered failure records.
    Interrupts propagate. Callbacks must create fresh simulator/state objects and
    declare all scientific settings through evaluation_id/parameters.
    """
    if not isinstance(manifest, SampleManifest):
        raise TypeError("manifest must be SampleManifest")
    if not isinstance(base_device, Device):
        raise TypeError("base_device must be Device")
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    if not isinstance(evaluation_id, str) or not evaluation_id or evaluation_id != evaluation_id.strip():
        raise ValueError("evaluation_id must be nonempty without outer whitespace")
    parameters = {} if evaluation_parameters is None else evaluation_parameters
    if type(parameters) is not dict:
        raise TypeError("evaluation_parameters must be a JSON object")
    evaluation = json.loads(_json_snapshot({"id": evaluation_id, "parameters": parameters}))
    device, protocol = deepcopy(base_device), deepcopy(base_protocol)
    device.validate()
    nominal = {"device": _device_definition_payload(device),
               "operating": None if protocol is None else _operating_definition_payload(protocol)}
    for variation in manifest.spec.variations:
        variation.validate_context(device, protocol)
    manifest_hash = manifest.manifest_hash
    study_json = _json_snapshot({"schema_version": "dtco-propagation-v1",
        "manifest_hash": manifest_hash, "nominal": nominal,
        "evaluation": evaluation, "execution": "serial-isolated", "ordering": "manifest-order",
        "runtime": {"python": platform.python_version(),
                    "python_implementation": platform.python_implementation(),
                    "numpy": np.__version__, "ncmemsim": __version__}})
    names = tuple(v.name for v in manifest.spec.variations)
    results = []
    for index, values in enumerate(manifest.values):
        point = SamplePoint(manifest_hash, index, tuple(zip(names, values)))
        stage = "application"
        try:
            device_assignments = []
            operating_assignments = []
            for variation, value in zip(manifest.spec.variations, values):
                target = device_assignments if variation.binding.scope is BindingScope.DEVICE else operating_assignments
                target.append((variation.binding, value))
            candidate = apply_device_bindings(device, device_assignments)
            candidate_protocol = None if protocol is None else apply_operating_bindings(protocol, operating_assignments)
            stage = "evaluation"
            output = evaluator(candidate, candidate_protocol, point)
            stage = "serialization"
            if type(output) is not dict:
                raise TypeError("evaluator must return a finite JSON object")
            result = SamplePointResult(point, "success", output_json=_json_snapshot(output))
        except Exception as exc:
            result = SamplePointResult(point, "failed", failure_stage=stage,
                error_type=f"{type(exc).__module__}.{type(exc).__qualname__}", error_message=str(exc))
        results.append(result)
    return PropagationResult(manifest, study_json, tuple(results))


__all__ = ["SamplePoint", "SamplePointResult", "PropagationResult", "propagate_samples"]
