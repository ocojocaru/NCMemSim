"""Isolated MODEL realization/execution with separate Phase L archives."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Callable

from ..device import Device
from ..dtco.binding import BindingApplicationError, apply_device_bindings
from ..dtco.operating import OperatingBindingError, apply_operating_bindings
from ..dtco.spec import BindingScope, _device_definition_payload, _operating_definition_payload
from ..hashing import canonical_hash
from ..transport.integration import AdvancedTransportSpec
from ..transport.traps import TrapParameterStatus
from ._serialization import strict_fields, parameter_binding_from_dict
from .execution import _runtime, _error_type, _FAILURE_CATEGORY_BY_STAGE
from .model_contracts import TransportModelContext, TrapDensityVariable, _density_target
from .model_sampling import ModelSampleManifest, ModelSamplingSpec, _snapshot, _strict_json
from .realization import RealizationAssignment
from .sampling import EnsembleSample


def _require_baseline(spec: ModelSamplingSpec, device: Device, protocol: Any) -> None:
    if not isinstance(device, Device):
        raise TypeError("base_device must be Device")
    device.validate()
    study = spec.study
    if canonical_hash(_device_definition_payload(device)) != study.base_device_hash:
        raise ValueError("device differs from MODEL study baseline")
    if study.base_operating_hash is None:
        if protocol is not None:
            raise ValueError("unexpected operating protocol")
    else:
        if protocol is None:
            raise ValueError("operating protocol is required")
        payload = _operating_definition_payload(protocol)
        if payload["kind"] != study.base_operating_kind or canonical_hash(payload) != study.base_operating_hash:
            raise ValueError("operating protocol differs from MODEL study baseline")


def _require_sample(spec: ModelSamplingSpec, sample: EnsembleSample) -> None:
    if not isinstance(spec, ModelSamplingSpec) or not isinstance(sample, EnsembleSample):
        raise TypeError("MODEL sampling spec and EnsembleSample are required")
    if (sample.sampling_spec_hash != spec.definition_hash or sample.variable_names != spec.variable_names
            or sample.sample_index >= spec.sample_count):
        raise ValueError("sample does not belong to MODEL sampling specification")


def _assignments(spec: ModelSamplingSpec, sample: EnsembleSample) -> tuple[RealizationAssignment, ...]:
    return tuple(RealizationAssignment(v.name, v.binding, v.unit, value)
                 for v, value in zip(spec.study.variables, sample.values, strict=True))


def _validate_domains(spec: ModelSamplingSpec, sample: EnsembleSample) -> None:
    for variable, value in zip(spec.study.variables, sample.values, strict=True):
        if not variable.physical_domain.contains(value):
            raise ValueError(f"sample value outside physical domain for {variable.name!r}")


def _realize_model(context: TransportModelContext, assignments: tuple[RealizationAssignment, ...]) -> TransportModelContext:
    densities = {_density_target(a.binding): a.value for a in assignments if a.binding.scope is BindingScope.MODEL}
    # Rebuild all species/specifications before validating enabled configurations.
    # This supports simultaneous changes without invalid intermediate states.
    attachments = []
    for attachment in context.advanced_transport.attachments:
        species = []
        for original in attachment.specification.species:
            density = densities.get((attachment.link_id, original.name), original.density_m3)
            if density == original.density_m3:
                species.append(replace(original))
            else:
                species.append(replace(original, density_m3=density, parameter_status=TrapParameterStatus.ASSUMED,
                    source=original.source + " | Phase L assigned stochastic density; distribution provenance in study"))
        species = tuple(species)
        attachments.append(replace(attachment, specification=replace(attachment.specification, species=species)))
    return TransportModelContext(AdvancedTransportSpec(tuple(attachments)))


@dataclass(frozen=True)
class AppliedModelRealization:
    """Independent device/protocol plus reconstructed immutable transport inputs."""

    sample: EnsembleSample
    device: Device
    operating_protocol: Any
    model_context: TransportModelContext
    assignments: tuple[RealizationAssignment, ...]

    def context_payload(self) -> dict[str, Any]:
        return {"device": _device_definition_payload(self.device),
                "operating": None if self.operating_protocol is None else _operating_definition_payload(self.operating_protocol),
                "model": self.model_context.to_dict()}


def apply_model_sample_to_context(spec: ModelSamplingSpec, sample: EnsembleSample,
                                  base_device: Device, base_operating_protocol: Any = None) -> AppliedModelRealization:
    """Apply stored values; never draw, clip, discard or mutate nominal inputs."""
    _require_sample(spec, sample)
    _require_baseline(spec, base_device, base_operating_protocol)
    _validate_domains(spec, sample)
    assignments = _assignments(spec, sample)
    device = apply_device_bindings(deepcopy(base_device), tuple((a.binding, a.value) for a in assignments
                                                              if a.binding.scope is BindingScope.DEVICE))
    operating = deepcopy(base_operating_protocol)
    if operating is not None:
        operating = apply_operating_bindings(operating, tuple((a.binding, a.value) for a in assignments
                                                            if a.binding.scope is BindingScope.OPERATING))
    model = _realize_model(spec.study.model_context, assignments)
    return AppliedModelRealization(sample, device, operating, model, assignments)


def _identity(manifest: ModelSampleManifest, sample: EnsembleSample, execution_hash: str) -> str:
    return canonical_hash({"schema_version": "model-realization-id-v1", "manifest_hash": manifest.manifest_hash,
                           "sample_id": sample.sample_id, "sample_hash": sample.sample_hash, "execution_hash": execution_hash})


@dataclass(frozen=True)
class ModelExecutionPoint:
    """Immutable JSON snapshot retaining attempted values even on failure."""

    record_json: str

    def __post_init__(self) -> None:
        data = _strict_json(self.record_json)
        strict_fields(data, label="MODEL execution point", required={"schema_version", "realization_id", "sample_id",
            "sample_hash", "sample_index", "assignments", "status", "context", "context_hash", "output",
            "failure_stage", "failure_category", "error_type", "error_message"})
        if data["schema_version"] != "model-execution-point-v1":
            raise ValueError("unsupported MODEL execution point schema")
        if type(data["assignments"]) is not list:
            raise TypeError("assignments must be a list")
        for assignment in data["assignments"]:
            strict_fields(assignment, label="MODEL assignment", required={"variable_name", "binding", "binding_id", "unit", "value"})
            parsed = RealizationAssignment(assignment["variable_name"], parameter_binding_from_dict(assignment["binding"]),
                                          assignment["unit"], assignment["value"])
            if parsed.binding.binding_id != assignment["binding_id"]:
                raise ValueError("MODEL assignment binding identity mismatch")
        context = data["context"]
        if context is None:
            if data["context_hash"] is not None:
                raise ValueError("unexpected context hash")
        else:
            strict_fields(context, label="realized MODEL context", required={"device", "operating", "model"})
            TransportModelContext.from_dict(context["model"])
            if type(context["device"]) is not dict or (context["operating"] is not None and type(context["operating"]) is not dict):
                raise ValueError("invalid realized device/operating payload")
            if canonical_hash(context) != data["context_hash"]:
                raise ValueError("realized context integrity mismatch")
        if data["status"] == "success":
            if context is None or type(data["output"]) is not dict:
                raise ValueError("successful MODEL point requires context and JSON object output")
            if any(data[key] is not None for key in ("failure_stage", "failure_category", "error_type", "error_message")):
                raise ValueError("success cannot contain failure details")
        elif data["status"] == "failed":
            stage = data["failure_stage"]
            if stage not in _FAILURE_CATEGORY_BY_STAGE or data["failure_category"] != _FAILURE_CATEGORY_BY_STAGE[stage]:
                raise ValueError("invalid MODEL failure accounting")
            if data["output"] is not None or any(type(data[k]) is not str or not data[k] for k in ("error_type", "error_message")):
                raise ValueError("invalid MODEL failure details")
            if (context is not None) != (stage in {"workflow", "serialization"}):
                raise ValueError("failure stage/context mismatch")
        else:
            raise ValueError("unsupported MODEL point status")
        object.__setattr__(self, "record_json", _snapshot(data))

    @property
    def status(self) -> str:
        return self.to_dict()["status"]

    @property
    def failure_stage(self) -> str | None:
        return self.to_dict()["failure_stage"]

    def to_dict(self) -> dict[str, Any]:
        return _strict_json(self.record_json)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelExecutionPoint:
        return cls(_snapshot(data))


@dataclass(frozen=True)
class ModelExecutionResult:
    """Separate execution archive; K4 statistics integration remains L4."""

    manifest: ModelSampleManifest
    execution_json: str
    points: tuple[ModelExecutionPoint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ModelSampleManifest):
            raise TypeError("manifest must be ModelSampleManifest")
        object.__setattr__(self, "points", tuple(self.points))
        execution = _strict_json(self.execution_json)
        strict_fields(execution, label="MODEL execution", required={"schema_version", "manifest_hash", "nominal",
            "evaluation_id", "workflow_context", "runtime", "ordering"})
        if (execution["schema_version"] != "model-execution-v1" or execution["manifest_hash"] != self.manifest.manifest_hash
                or execution["ordering"] != "serial-manifest-order"):
            raise ValueError("MODEL execution schema/manifest/order mismatch")
        if type(execution["evaluation_id"]) is not str or not execution["evaluation_id"].strip():
            raise ValueError("evaluation_id must be nonempty text")
        if type(execution["workflow_context"]) is not dict or not execution["workflow_context"]:
            raise ValueError("explicit workflow context is required")
        if type(execution["runtime"]) is not dict or set(execution["runtime"]) != set(_runtime()) or any(
                type(v) is not str or not v for v in execution["runtime"].values()):
            raise ValueError("invalid execution runtime")
        nominal = execution["nominal"]
        strict_fields(nominal, label="nominal MODEL context", required={"device", "operating", "model"})
        study = self.manifest.sampling_spec.study
        if (canonical_hash(nominal["device"]) != study.base_device_hash
                or nominal["model"] != study.model_context.to_dict()):
            raise ValueError("nominal device/model does not match MODEL study")
        if study.base_operating_hash is None:
            if nominal["operating"] is not None:
                raise ValueError("unexpected nominal operating context")
        elif (type(nominal["operating"]) is not dict or canonical_hash(nominal["operating"]) != study.base_operating_hash
              or nominal["operating"].get("kind") != study.base_operating_kind):
            raise ValueError("nominal operating identity mismatch")
        if len(self.points) != len(self.manifest.samples):
            raise ValueError("every attempted sample requires one execution point")
        digest = canonical_hash(execution)
        for sample, point in zip(self.manifest.samples, self.points, strict=True):
            if not isinstance(point, ModelExecutionPoint):
                raise TypeError("points must be ModelExecutionPoint")
            data = point.to_dict()
            if (data["sample_index"] != sample.sample_index or type(data["sample_index"]) is not int
                    or data["sample_id"] != sample.sample_id or data["sample_hash"] != sample.sample_hash
                    or data["realization_id"] != _identity(self.manifest, sample, digest)
                    or data["assignments"] != [a.to_dict() for a in _assignments(self.manifest.sampling_spec, sample)]):
                raise ValueError("execution point differs from authoritative sample")
            if data["context"] is not None:
                _validate_domains(self.manifest.sampling_spec, sample)
                expected_model = _realize_model(study.model_context, _assignments(self.manifest.sampling_spec, sample))
                if data["context"]["model"] != expected_model.to_dict():
                    raise ValueError("realized MODEL configuration differs from sample")
        object.__setattr__(self, "execution_json", _snapshot(execution))

    @property
    def success_count(self) -> int:
        return sum(p.status == "success" for p in self.points)

    @property
    def failure_count(self) -> int:
        return len(self.points) - self.success_count

    def _payload(self) -> dict[str, Any]:
        return {"schema_version": "model-execution-result-v1", "manifest": self.manifest.to_dict(),
                "execution": _strict_json(self.execution_json), "points": [p.to_dict() for p in self.points],
                "success_count": self.success_count, "failure_count": self.failure_count}

    @property
    def result_hash(self) -> str:
        return canonical_hash(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_hash": self.result_hash}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelExecutionResult:
        strict_fields(data, label="MODEL result", required={"schema_version", "manifest", "execution", "points",
                                                             "success_count", "failure_count", "result_hash"})
        if data["schema_version"] != "model-execution-result-v1" or type(data["points"]) is not list:
            raise ValueError("unsupported MODEL result schema")
        result = cls(ModelSampleManifest.from_dict(data["manifest"]), _snapshot(data["execution"]),
                     tuple(ModelExecutionPoint.from_dict(p) for p in data["points"]))
        if (type(data["success_count"]) is not int or type(data["failure_count"]) is not int
                or data["success_count"] != result.success_count or data["failure_count"] != result.failure_count
                or data["result_hash"] != result.result_hash):
            raise ValueError("MODEL result integrity/count mismatch")
        return result

    def to_json(self) -> str:
        return _snapshot(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> ModelExecutionResult:
        return cls.from_dict(_strict_json(text))


def execute_model_sample_manifest(manifest: ModelSampleManifest, base_device: Device,
                                  evaluator: Callable[[AppliedModelRealization, dict[str, Any]], dict[str, Any]], *,
                                  evaluation_id: str, workflow_context: dict[str, Any],
                                  base_operating_protocol: Any = None) -> ModelExecutionResult:
    """Execute stored values with caller-declared physics/engine/protocol settings.

    The callback must construct its solver using the realized model configuration.
    Its hidden closure state cannot be inferred or certified by this orchestrator.
    """
    if not isinstance(manifest, ModelSampleManifest) or not callable(evaluator):
        raise TypeError("MODEL manifest and callable evaluator are required")
    if type(evaluation_id) is not str or not evaluation_id or evaluation_id != evaluation_id.strip():
        raise ValueError("evaluation_id must be nonempty text without outer whitespace")
    if type(workflow_context) is not dict or not workflow_context:
        raise ValueError("explicit nonempty workflow_context is required")
    workflow_json = _snapshot(workflow_context)
    device, protocol = deepcopy(base_device), deepcopy(base_operating_protocol)
    spec = manifest.sampling_spec
    _require_baseline(spec, device, protocol)
    execution_json = _snapshot({"schema_version": "model-execution-v1", "manifest_hash": manifest.manifest_hash,
        "nominal": {"device": _device_definition_payload(device),
                    "operating": None if protocol is None else _operating_definition_payload(protocol),
                    "model": spec.study.model_context.to_dict()},
        "evaluation_id": evaluation_id, "workflow_context": _strict_json(workflow_json),
        "runtime": _runtime(), "ordering": "serial-manifest-order"})
    digest = canonical_hash(_strict_json(execution_json))
    points = []
    for sample in manifest.samples:
        record = {"schema_version": "model-execution-point-v1", "realization_id": _identity(manifest, sample, digest),
                  "sample_id": sample.sample_id, "sample_hash": sample.sample_hash, "sample_index": sample.sample_index,
                  "assignments": [a.to_dict() for a in _assignments(spec, sample)], "status": "failed",
                  "context": None, "context_hash": None, "output": None,
                  "failure_stage": None, "failure_category": None, "error_type": None, "error_message": None}
        stage = "sample-domain-validation"
        try:
            _validate_domains(spec, sample)
            stage = "realization-construction"
            realization = apply_model_sample_to_context(spec, sample, device, protocol)
            record["context"] = _strict_json(_snapshot(realization.context_payload()))
            record["context_hash"] = canonical_hash(record["context"])
            stage = "workflow"
            output = evaluator(realization, _strict_json(workflow_json))
            stage = "serialization"
            if type(output) is not dict:
                raise TypeError("evaluator must return a JSON object")
            record["output"] = _strict_json(_snapshot(output))
            record["status"] = "success"
        except Exception as exc:
            if isinstance(exc, (BindingApplicationError, OperatingBindingError)) and stage == "realization-construction":
                stage = "binding"
            record.update(failure_stage=stage, failure_category=_FAILURE_CATEGORY_BY_STAGE[stage],
                          error_type=_error_type(exc), error_message=str(exc) or type(exc).__name__)
        points.append(ModelExecutionPoint.from_dict(record))
    return ModelExecutionResult(manifest, execution_json, tuple(points))


__all__ = ["AppliedModelRealization", "apply_model_sample_to_context", "ModelExecutionPoint",
           "ModelExecutionResult", "execute_model_sample_manifest"]
