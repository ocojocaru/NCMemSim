"""Serial isolated execution of Phase K ensemble realizations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import platform
from typing import Any, Callable

import numpy as np

from .._version import __version__
from ..device import Device
from ..dtco.binding import BindingApplicationError
from ..dtco.operating import (
    OperatingBindingError,
    OperatingProtocol,
)
from ..dtco.spec import (
    _device_definition_payload,
    _operating_definition_payload,
)
from ..dtco.sweep import _json_snapshot
from ..hashing import canonical_hash
from .realization import (
    AppliedRealization,
    RealizationAssignment,
    RealizationIdentity,
    apply_sample_to_context,
    validate_sample_domain,
)
from .sampling import SampleManifest


EXECUTION_SCHEMA_VERSION = "ensemble-execution-v1"

_FAILURE_STAGES = {
    "sample-domain-validation",
    "binding",
    "realization-construction",
    "workflow",
    "serialization",
}

_FAILURE_CATEGORY_BY_STAGE = {
    "sample-domain-validation": "sample-domain-invalid",
    "binding": "binding-application",
    "realization-construction": "realization-invalid",
    "workflow": "workflow-execution",
    "serialization": "output-serialization",
}


def _label(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(
            f"{field} must be nonempty text without outer whitespace"
        )

    return value


def _runtime() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "numpy": np.__version__,
        "ncmemsim": __version__,
    }


def _error_type(exc: Exception) -> str:
    return (
        f"{type(exc).__module__}."
        f"{type(exc).__qualname__}"
    )


@dataclass(frozen=True)
class RealizationExecutionPoint:
    """Success or isolated failure for one exact ensemble sample."""

    identity: RealizationIdentity
    status: str
    assignments: tuple[RealizationAssignment, ...] = ()
    realized_device_hash: str | None = None
    realized_operating_hash: str | None = None
    realized_context_json: str | None = None
    output_json: str | None = None
    failure_stage: str | None = None
    failure_category: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.identity,
            RealizationIdentity,
        ):
            raise TypeError(
                "identity must be RealizationIdentity"
            )

        assignments = tuple(
            self.assignments
        )

        if any(
            not isinstance(
                item,
                RealizationAssignment,
            )
            for item in assignments
        ):
            raise TypeError(
                "assignments must contain "
                "RealizationAssignment instances"
            )

        object.__setattr__(
            self,
            "assignments",
            assignments,
        )

        context = None

        if self.realized_context_json is not None:
            context = json.loads(
                self.realized_context_json
            )

            if (
                type(context) is not dict
                or set(context)
                != {"device", "operating"}
                or type(context["device"])
                is not dict
            ):
                raise ValueError(
                    "invalid realized context"
                )

            object.__setattr__(
                self,
                "realized_context_json",
                _json_snapshot(context),
            )

            if self.realized_device_hash is None:
                raise ValueError(
                    "realized context requires device hash"
                )

            if (
                canonical_hash(
                    context["device"]
                )
                != self.realized_device_hash
            ):
                raise ValueError(
                    "realized device hash "
                    "does not match context"
                )

            if context["operating"] is None:
                if (
                    self.realized_operating_hash
                    is not None
                ):
                    raise ValueError(
                        "unexpected realized operating hash"
                    )

            else:
                if (
                    type(context["operating"])
                    is not dict
                ):
                    raise TypeError(
                        "realized operating context "
                        "must be an object or null"
                    )

                if (
                    self.realized_operating_hash
                    is None
                ):
                    raise ValueError(
                        "realized operating context "
                        "requires hash"
                    )

                if (
                    canonical_hash(
                        context["operating"]
                    )
                    != self.realized_operating_hash
                ):
                    raise ValueError(
                        "realized operating hash "
                        "does not match context"
                    )

        if self.status == "success":
            if not assignments:
                raise ValueError(
                    "successful execution requires assignments"
                )

            if (
                self.realized_context_json is None
                or self.realized_device_hash is None
            ):
                raise ValueError(
                    "successful execution requires "
                    "realized context"
                )

            if any(
                value is not None
                for value in (
                    self.failure_stage,
                    self.failure_category,
                    self.error_type,
                    self.error_message,
                )
            ):
                raise ValueError(
                    "successful execution cannot "
                    "contain failure details"
                )

            if self.output_json is None:
                raise ValueError(
                    "successful execution requires output"
                )

            output = json.loads(
                self.output_json
            )

            if type(output) is not dict:
                raise TypeError(
                    "successful output must be a JSON object"
                )

            object.__setattr__(
                self,
                "output_json",
                _json_snapshot(output),
            )

        elif self.status == "failed":
            if self.output_json is not None:
                raise ValueError(
                    "failed execution cannot contain output"
                )

            if (
                self.failure_stage
                not in _FAILURE_STAGES
            ):
                raise ValueError(
                    "invalid execution failure stage"
                )

            expected_category = (
                _FAILURE_CATEGORY_BY_STAGE[
                    self.failure_stage
                ]
            )

            if (
                self.failure_category
                != expected_category
            ):
                raise ValueError(
                    "failure category does not match "
                    "failure stage"
                )

            _label(
                self.error_type,
                "error_type",
            )

            if not isinstance(
                self.error_message,
                str,
            ):
                raise TypeError(
                    "failed execution requires "
                    "string error_message"
                )

            constructed = (
                self.failure_stage
                in {"workflow", "serialization"}
            )

            if constructed:
                if (
                    not assignments
                    or self.realized_context_json
                    is None
                    or self.realized_device_hash
                    is None
                ):
                    raise ValueError(
                        "post-construction failure "
                        "requires realized context"
                    )

            else:
                if (
                    assignments
                    or self.realized_context_json
                    is not None
                    or self.realized_device_hash
                    is not None
                    or self.realized_operating_hash
                    is not None
                ):
                    raise ValueError(
                        "pre-construction failure "
                        "cannot expose partial realization"
                    )

        else:
            raise ValueError(
                "status must be success or failed"
            )

    @property
    def output(self) -> dict[str, Any] | None:
        if self.output_json is None:
            return None

        return json.loads(
            self.output_json
        )

    @property
    def realized_context(
        self,
    ) -> dict[str, Any] | None:
        if self.realized_context_json is None:
            return None

        return json.loads(
            self.realized_context_json
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "status": self.status,
            "assignments": [
                item.to_dict()
                for item in self.assignments
            ],
            "realized_device_hash": (
                self.realized_device_hash
            ),
            "realized_operating_hash": (
                self.realized_operating_hash
            ),
            "realized_context": (
                self.realized_context
            ),
            "output": self.output,
            "failure": (
                None
                if self.status == "success"
                else {
                    "stage": self.failure_stage,
                    "category": self.failure_category,
                    "type": self.error_type,
                    "message": self.error_message,
                }
            ),
        }

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


@dataclass(frozen=True)
class EnsembleExecutionResult:
    """Ordered isolated execution result for one exact sample manifest."""

    manifest: SampleManifest
    execution_json: str
    points: tuple[
        RealizationExecutionPoint,
        ...
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.manifest,
            SampleManifest,
        ):
            raise TypeError(
                "manifest must be SampleManifest"
            )

        execution = json.loads(
            self.execution_json
        )

        if (
            type(execution) is not dict
            or set(execution)
            != {
                "schema_version",
                "manifest_hash",
                "nominal",
                "evaluator",
                "execution",
                "ordering",
                "runtime",
            }
        ):
            raise ValueError(
                "execution definition fields mismatch"
            )

        if (
            execution["schema_version"]
            != EXECUTION_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported execution schema_version"
            )

        if (
            execution["manifest_hash"]
            != self.manifest.manifest_hash
        ):
            raise ValueError(
                "execution manifest identity mismatch"
            )

        if (
            execution["execution"]
            != "serial-isolated"
            or execution["ordering"]
            != "manifest-order"
        ):
            raise ValueError(
                "unsupported ensemble execution policy"
            )

        evaluator = execution["evaluator"]

        if (
            type(evaluator) is not dict
            or set(evaluator)
            != {"id", "parameters"}
            or type(
                evaluator["parameters"]
            )
            is not dict
        ):
            raise ValueError(
                "execution requires evaluator identity "
                "and parameters"
            )

        _label(
            evaluator["id"],
            "evaluator id",
        )

        runtime = execution["runtime"]

        if (
            type(runtime) is not dict
            or set(runtime)
            != {
                "python",
                "python_implementation",
                "numpy",
                "ncmemsim",
            }
            or not all(
                isinstance(value, str)
                and value
                for value in runtime.values()
            )
        ):
            raise ValueError(
                "execution requires runtime provenance"
            )

        nominal = execution["nominal"]

        if (
            type(nominal) is not dict
            or set(nominal)
            != {"device", "operating"}
            or type(nominal["device"])
            is not dict
        ):
            raise ValueError(
                "execution requires nominal context"
            )

        ensemble_spec = (
            self.manifest
            .sampling_spec
            .ensemble_spec
        )

        if (
            canonical_hash(
                nominal["device"]
            )
            != ensemble_spec.base_device_hash
        ):
            raise ValueError(
                "nominal device differs from "
                "ensemble specification"
            )

        if (
            ensemble_spec.base_operating_hash
            is None
        ):
            if nominal["operating"] is not None:
                raise ValueError(
                    "unexpected nominal operating context"
                )

        else:
            if (
                type(nominal["operating"])
                is not dict
                or canonical_hash(
                    nominal["operating"]
                )
                != ensemble_spec.base_operating_hash
            ):
                raise ValueError(
                    "nominal operating context differs "
                    "from ensemble specification"
                )

        points = tuple(
            self.points
        )

        if (
            len(points)
            != len(self.manifest.samples)
        ):
            raise ValueError(
                "every manifest sample must have "
                "an execution result"
            )

        variables = (
            self.manifest
            .sampling_spec
            .ensemble_spec
            .variables
        )

        for sample, point in zip(
            self.manifest.samples,
            points,
            strict=True,
        ):
            if not isinstance(
                point,
                RealizationExecutionPoint,
            ):
                raise TypeError(
                    "points must contain "
                    "RealizationExecutionPoint instances"
                )

            expected_identity = (
                RealizationIdentity.from_sample(
                    self.manifest.sampling_spec,
                    sample,
                )
            )

            if point.identity != expected_identity:
                raise ValueError(
                    "execution point identity "
                    "differs from manifest"
                )

            constructed = (
                point.status == "success"
                or point.failure_stage
                in {"workflow", "serialization"}
            )

            if constructed:
                expected_assignments = tuple(
                    RealizationAssignment(
                        variable_name=variable.name,
                        binding=variable.binding,
                        unit=variable.unit,
                        value=value,
                    )
                    for variable, value in zip(
                        variables,
                        sample.values,
                        strict=True,
                    )
                )

                if (
                    point.assignments
                    != expected_assignments
                ):
                    raise ValueError(
                        "execution assignments differ "
                        "from manifest sample"
                    )

        object.__setattr__(
            self,
            "execution_json",
            _json_snapshot(execution),
        )

        object.__setattr__(
            self,
            "points",
            points,
        )

    @property
    def success_count(self) -> int:
        return sum(
            point.status == "success"
            for point in self.points
        )

    @property
    def failure_count(self) -> int:
        return (
            len(self.points)
            - self.success_count
        )

    @property
    def execution_hash(self) -> str:
        return canonical_hash(
            json.loads(
                self.execution_json
            )
        )

    @property
    def nominal_hash(self) -> str:
        return canonical_hash(
            json.loads(
                self.execution_json
            )["nominal"]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": (
                "ensemble-execution-result-v1"
            ),
            "execution": json.loads(
                self.execution_json
            ),
            "execution_hash": (
                self.execution_hash
            ),
            "nominal_hash": (
                self.nominal_hash
            ),
            "manifest": (
                self.manifest.to_dict()
            ),
            "points": [
                point.to_dict()
                for point in self.points
            ],
            "success_count": (
                self.success_count
            ),
            "failure_count": (
                self.failure_count
            ),
        }

    def to_json(self) -> str:
        return _json_snapshot(
            self.to_dict()
        )

    @property
    def result_hash(self) -> str:
        return canonical_hash(
            self.to_dict()
        )


EnsembleEvaluator = Callable[
    [
        Device,
        OperatingProtocol | None,
        AppliedRealization,
    ],
    dict[str, Any],
]


def execute_sample_manifest(
    manifest: SampleManifest,
    base_device: Device,
    evaluator: EnsembleEvaluator,
    *,
    evaluation_id: str,
    evaluation_parameters: (
        dict[str, Any] | None
    ) = None,
    base_operating_protocol: (
        OperatingProtocol | None
    ) = None,
) -> EnsembleExecutionResult:
    """Execute stored Phase K samples serially without resampling."""

    if not isinstance(
        manifest,
        SampleManifest,
    ):
        raise TypeError(
            "manifest must be SampleManifest"
        )

    if not isinstance(
        base_device,
        Device,
    ):
        raise TypeError(
            "base_device must be Device"
        )

    if not callable(evaluator):
        raise TypeError(
            "evaluator must be callable"
        )

    _label(
        evaluation_id,
        "evaluation_id",
    )

    parameters = (
        {}
        if evaluation_parameters is None
        else evaluation_parameters
    )

    if type(parameters) is not dict:
        raise TypeError(
            "evaluation_parameters must be "
            "a JSON object"
        )

    evaluator_identity = json.loads(
        _json_snapshot(
            {
                "id": evaluation_id,
                "parameters": parameters,
            }
        )
    )

    nominal_device = deepcopy(
        base_device
    )

    nominal_protocol = deepcopy(
        base_operating_protocol
    )

    nominal_device.validate()

    ensemble_spec = (
        manifest
        .sampling_spec
        .ensemble_spec
    )

    ensemble_spec.require_matching_device(
        nominal_device
    )

    if (
        ensemble_spec.base_operating_hash
        is None
    ):
        if nominal_protocol is not None:
            raise ValueError(
                "ensemble specification has no "
                "operating baseline identity"
            )

    else:
        if nominal_protocol is None:
            raise ValueError(
                "base_operating_protocol is required "
                "by ensemble specification"
            )

        ensemble_spec.require_matching_operating(
            nominal_protocol
        )

    nominal = {
        "device": _device_definition_payload(
            nominal_device
        ),
        "operating": (
            None
            if nominal_protocol is None
            else _operating_definition_payload(
                nominal_protocol
            )
        ),
    }

    execution_json = _json_snapshot(
        {
            "schema_version": (
                EXECUTION_SCHEMA_VERSION
            ),
            "manifest_hash": (
                manifest.manifest_hash
            ),
            "nominal": nominal,
            "evaluator": evaluator_identity,
            "execution": "serial-isolated",
            "ordering": "manifest-order",
            "runtime": _runtime(),
        }
    )

    points = []

    for sample in manifest.samples:
        identity = (
            RealizationIdentity.from_sample(
                manifest.sampling_spec,
                sample,
            )
        )

        stage = "sample-domain-validation"
        captured_realization = None
        realized_context_json = None

        try:
            validate_sample_domain(
                sample,
                manifest.sampling_spec,
            )

            stage = "realization-construction"

            try:
                realization = apply_sample_to_context(
                    manifest.sampling_spec,
                    sample,
                    nominal_device,
                    nominal_protocol,
                )
            except (
                BindingApplicationError,
                OperatingBindingError,
            ):
                stage = "binding"
                raise

            realized_context_json = (
                _json_snapshot(
                    {
                        "device": (
                            _device_definition_payload(
                                realization.device
                            )
                        ),
                        "operating": (
                            None
                            if (
                                realization
                                .operating_protocol
                                is None
                            )
                            else (
                                _operating_definition_payload(
                                    realization
                                    .operating_protocol
                                )
                            )
                        ),
                    }
                )
            )

            captured_realization = realization

            stage = "workflow"

            output = evaluator(
                realization.device,
                realization.operating_protocol,
                realization,
            )

            stage = "serialization"

            if type(output) is not dict:
                raise TypeError(
                    "evaluator must return "
                    "a JSON object"
                )

            output_json = _json_snapshot(
                output
            )

            point = RealizationExecutionPoint(
                identity=identity,
                status="success",
                assignments=(
                    realization.assignments
                ),
                realized_device_hash=(
                    realization
                    .realized_device_hash
                ),
                realized_operating_hash=(
                    realization
                    .realized_operating_hash
                ),
                realized_context_json=(
                    realized_context_json
                ),
                output_json=output_json,
            )

        except Exception as exc:
            kwargs: dict[str, Any] = {}

            if captured_realization is not None:
                kwargs = {
                    "assignments": (
                        captured_realization
                        .assignments
                    ),
                    "realized_device_hash": (
                        captured_realization
                        .realized_device_hash
                    ),
                    "realized_operating_hash": (
                        captured_realization
                        .realized_operating_hash
                    ),
                    "realized_context_json": (
                        realized_context_json
                    ),
                }

            point = RealizationExecutionPoint(
                identity=identity,
                status="failed",
                failure_stage=stage,
                failure_category=(
                    _FAILURE_CATEGORY_BY_STAGE[
                        stage
                    ]
                ),
                error_type=_error_type(exc),
                error_message=str(exc),
                **kwargs,
            )

        points.append(
            point
        )

    return EnsembleExecutionResult(
        manifest=manifest,
        execution_json=execution_json,
        points=tuple(points),
    )


__all__ = [
    "EXECUTION_SCHEMA_VERSION",
    "EnsembleEvaluator",
    "EnsembleExecutionResult",
    "RealizationExecutionPoint",
    "execute_sample_manifest",
]
