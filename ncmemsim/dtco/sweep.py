"""Serial deterministic Cartesian exploration with isolated point evaluation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import product
import json
import math
import re
from typing import Any, Callable, Iterator

from ..device import Device
from ..hashing import canonical_hash
from .binding import apply_experiment_design_point
from .operating import OperatingProtocol, apply_experiment_point
from .spec import BindingScope, ExperimentSpec, ScalarValue

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _json_snapshot(value: Any) -> str:
    """Reject lossy coercion, non-finite values and non-JSON scientific objects."""
    def check(item: Any) -> None:
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("JSON numbers must be finite")
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise TypeError("JSON object keys must be strings")
                check(child)
            return
        raise TypeError(f"unsupported JSON value type: {type(item).__name__}")

    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class SweepPoint:
    """An ordered assignment tied to the exact experiment definition."""

    experiment_hash: str
    index: int
    values_by_name: tuple[tuple[str, ScalarValue], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values_by_name", tuple(
            (name, value) for name, value in self.values_by_name
        ))
        if not isinstance(self.experiment_hash, str) or not _DIGEST.fullmatch(
            self.experiment_hash
        ):
            raise ValueError("experiment_hash must be a lowercase SHA-256 digest")
        if type(self.index) is not int or self.index < 0:
            raise ValueError("point index must be a nonnegative integer")
        if not self.values_by_name:
            raise ValueError("point requires assignments")
        names = []
        for name, value in self.values_by_name:
            if not isinstance(name, str) or not name or name != name.strip():
                raise ValueError("assignment names must be non-empty without outer whitespace")
            if type(value) not in (int, float, str):
                raise TypeError("assignment values must be int, float, or str")
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
            "schema_version": "dtco-point-v1",
            "experiment_hash": self.experiment_hash,
            "index": self.index,
            "assignments": [
                {"name": name, "value": value} for name, value in self.values_by_name
            ],
        }

    @property
    def point_hash(self) -> str:
        return canonical_hash(self.to_dict())


def iter_cartesian_points(spec: ExperimentSpec) -> Iterator[SweepPoint]:
    """Generate lazily; last declared axis varies fastest, without sorting."""
    if not isinstance(spec, ExperimentSpec):
        raise TypeError("spec must be an ExperimentSpec")
    experiment_hash = spec.experiment_hash
    names = tuple(variable.name for variable in spec.variables)
    for index, values in enumerate(product(*(v.values for v in spec.variables))):
        yield SweepPoint(experiment_hash, index, tuple(zip(names, values)))


@dataclass(frozen=True)
class SweepPointResult:
    """A success snapshot or a failure with the stage at which it occurred."""

    point: SweepPoint
    status: str
    output_json: str | None = None
    failure_stage: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.point, SweepPoint):
            raise TypeError("point must be a SweepPoint")
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
class SweepResult:
    """Serializable ordered results and the declared evaluation identity."""

    experiment_json: str
    evaluation_json: str
    points: tuple[SweepPointResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))
        experiment = json.loads(self.experiment_json)
        evaluation = json.loads(self.evaluation_json)
        if type(experiment) is not dict or type(evaluation) is not dict:
            raise TypeError("experiment and evaluation must be JSON objects")
        object.__setattr__(self, "experiment_json", _json_snapshot(experiment))
        object.__setattr__(self, "evaluation_json", _json_snapshot(evaluation))
        variables = experiment.get("variables")
        if not isinstance(variables, list) or not variables:
            raise ValueError("experiment requires variable definitions")
        expected_count = math.prod(len(v["values"]) for v in variables)
        if len(self.points) != expected_count:
            raise ValueError("sweep must contain every declared Cartesian point")
        evaluation_id = evaluation.get("id")
        if (
            not isinstance(evaluation_id, str)
            or not evaluation_id
            or evaluation_id != evaluation_id.strip()
            or type(evaluation.get("parameters")) is not dict
        ):
            raise ValueError("evaluation requires an explicit id and parameters object")
        expected_values = product(*(v["values"] for v in variables))
        names = tuple(v["name"] for v in variables)
        for index, result in enumerate(self.points):
            if not isinstance(result, SweepPointResult):
                raise TypeError("points must contain SweepPointResult instances")
            if result.point.index != index or result.point.experiment_hash != self.experiment_hash:
                raise ValueError("point order or experiment identity differs")
            if result.point.values_by_name != tuple(zip(names, next(expected_values))):
                raise ValueError("point assignments differ from declared Cartesian order")

    @property
    def experiment_hash(self) -> str:
        return canonical_hash(json.loads(self.experiment_json))

    @property
    def success_count(self) -> int:
        return sum(point.status == "success" for point in self.points)

    @property
    def failure_count(self) -> int:
        return len(self.points) - self.success_count

    @property
    def sweep_hash(self) -> str:
        """Definition identity, independent of outputs or failure messages."""
        return canonical_hash({
            "schema_version": "dtco-sweep-v1",
            "experiment": json.loads(self.experiment_json),
            "evaluation": json.loads(self.evaluation_json),
            "ordering": "declared-last-axis-fastest",
            "execution": "serial-isolated",
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "dtco-sweep-result-v1",
            "sweep_hash": self.sweep_hash,
            "experiment_hash": self.experiment_hash,
            "experiment": json.loads(self.experiment_json),
            "evaluation": json.loads(self.evaluation_json),
            "points": [point.to_dict() for point in self.points],
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @property
    def result_hash(self) -> str:
        return canonical_hash(self.to_dict())


Evaluator = Callable[[Device, OperatingProtocol | None, SweepPoint], dict[str, Any]]


def run_cartesian_sweep(
    spec: ExperimentSpec,
    base_device: Device,
    evaluator: Evaluator,
    *,
    evaluation_id: str,
    evaluation_parameters: dict[str, Any] | None = None,
    base_protocol: OperatingProtocol | None = None,
) -> SweepResult:
    """Evaluate every point serially, collecting ordinary point exceptions.

    Setup errors fail before evaluation. KeyboardInterrupt and SystemExit propagate.
    The evaluator must build fresh simulation/state objects for each candidate and
    return a finite JSON object. Its scientific settings must be declared in
    evaluation_parameters; callback code is identified by evaluation_id.
    """
    if not isinstance(spec, ExperimentSpec):
        raise TypeError("spec must be an ExperimentSpec")
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    if not isinstance(evaluation_id, str) or not evaluation_id or evaluation_id != evaluation_id.strip():
        raise ValueError("evaluation_id must be non-empty without outer whitespace")
    parameters = {} if evaluation_parameters is None else evaluation_parameters
    if type(parameters) is not dict:
        raise TypeError("evaluation_parameters must be a JSON object")
    evaluation_json = _json_snapshot({"id": evaluation_id, "parameters": parameters})
    experiment_json = _json_snapshot(spec.to_dict())
    if any(v.binding.scope is BindingScope.MODEL for v in spec.variables):
        raise ValueError("BindingScope.MODEL application remains deferred")
    if spec.base_operating_hash is None and base_protocol is not None:
        raise ValueError("base_protocol requires an operating identity in the experiment")
    if spec.base_operating_hash is not None and base_protocol is None:
        raise ValueError("experiment requires its operating baseline")

    device = deepcopy(base_device)
    protocol = deepcopy(base_protocol)
    spec.require_matching_device(device)
    if protocol is not None:
        spec.require_matching_operating(protocol)

    results = []
    for point in iter_cartesian_points(spec):
        stage = "application"
        try:
            if protocol is None:
                candidate = apply_experiment_design_point(spec, device, point.assignments)
                candidate_protocol = None
            else:
                applied = apply_experiment_point(spec, device, protocol, point.assignments)
                candidate = applied.device
                candidate_protocol = applied.operating_protocol
            stage = "evaluation"
            output = evaluator(candidate, candidate_protocol, point)
            stage = "serialization"
            if type(output) is not dict:
                raise TypeError("evaluator must return a JSON object")
            snapshot = _json_snapshot(output)
            result = SweepPointResult(point, "success", output_json=snapshot)
        except Exception as exc:
            result = SweepPointResult(
                point, "failed", failure_stage=stage,
                error_type=f"{type(exc).__module__}.{type(exc).__qualname__}",
                error_message=str(exc),
            )
        results.append(result)
    return SweepResult(experiment_json, evaluation_json, tuple(results))


__all__ = [
    "SweepPoint", "SweepPointResult", "SweepResult",
    "iter_cartesian_points", "run_cartesian_sweep",
]
