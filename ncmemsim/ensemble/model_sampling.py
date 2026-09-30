"""Phase L sampling envelopes using the unchanged Phase K draw kernels."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from types import SimpleNamespace
from typing import Any

from ..hashing import canonical_hash
from ._serialization import strict_fields
from .correlation import IndependentDependence, MatrixCorrelation, dependence_from_dict
from .execution import _runtime
from .model_contracts import ModelVariabilitySpec
from .rng import RNGSpec
from .sampling import (
    EnsembleSample, SampleGenerationError, SamplingError, SCALAR_SAMPLING_ALGORITHM,
    SAMPLING_ORDER, SAMPLING_PRECISION, _integer, _validate_dependence_against_ensemble,
    _dependence_sampling_algorithm, _sequential_psd_cholesky, _standard_normal,
    _correlated_marginal_value, sample_distribution,
)


def _snapshot(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _strict_json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


@dataclass(frozen=True)
class ModelSamplingSpec:
    """MODEL study sampling identity; never accepted by Phase K executors."""

    study: ModelVariabilitySpec
    rng: RNGSpec
    sample_count: int
    dependence: IndependentDependence | MatrixCorrelation = field(default_factory=IndependentDependence)
    max_draws_per_value: int = 10000

    def __post_init__(self) -> None:
        if not isinstance(self.study, ModelVariabilitySpec):
            raise TypeError("study must be ModelVariabilitySpec")
        if not isinstance(self.rng, RNGSpec):
            raise TypeError("rng must be RNGSpec")
        _integer(self.sample_count, "sample_count", 1)
        _integer(self.max_draws_per_value, "max_draws_per_value", 1)
        view = SimpleNamespace(variables=self.study.variables, variable_names=self.variable_names)
        _validate_dependence_against_ensemble(view, self.dependence)

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(v.name for v in self.study.variables)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": "model-sampling-spec-v1", "study": self.study.to_dict(),
                "study_hash": self.study.definition_hash, "rng": self.rng.to_dict(),
                "sample_count": self.sample_count, "dependence": self.dependence.to_dict(),
                "max_draws_per_value": self.max_draws_per_value,
                "scalar_sampling_algorithm": SCALAR_SAMPLING_ALGORITHM,
                "dependence_sampling_algorithm": _dependence_sampling_algorithm(self.dependence),
                "order": SAMPLING_ORDER, "precision": SAMPLING_PRECISION}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelSamplingSpec:
        strict_fields(data, label="MODEL sampling", required={"schema_version", "study", "study_hash", "rng",
            "sample_count", "dependence", "max_draws_per_value", "scalar_sampling_algorithm",
            "dependence_sampling_algorithm", "order", "precision"})
        result = cls(ModelVariabilitySpec.from_dict(data["study"]), RNGSpec.from_dict(data["rng"]),
                     data["sample_count"], dependence_from_dict(data["dependence"]), data["max_draws_per_value"])
        if data != result.to_dict():
            raise ValueError("MODEL sampling identity or algorithm mismatch")
        return result

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class ModelSampleManifest:
    """Authoritative stored values; restoration never draws samples."""

    sampling_spec: ModelSamplingSpec
    samples: tuple[EnsembleSample, ...]
    runtime: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.sampling_spec, ModelSamplingSpec):
            raise TypeError("sampling_spec must be ModelSamplingSpec")
        object.__setattr__(self, "samples", tuple(self.samples))
        object.__setattr__(self, "runtime", tuple(tuple(item) for item in self.runtime))
        runtime = dict(self.runtime)
        if (len(runtime) != len(self.runtime) or set(runtime) != set(_runtime())
                or any(type(v) is not str or not v for v in runtime.values())):
            raise ValueError("invalid MODEL manifest runtime")
        if len(self.samples) != self.sampling_spec.sample_count:
            raise ValueError("every requested sample must be present")
        for index, sample in enumerate(self.samples):
            if not isinstance(sample, EnsembleSample):
                raise TypeError("samples must be EnsembleSample")
            if (sample.sample_index != index or sample.variable_names != self.sampling_spec.variable_names
                    or sample.sampling_spec_hash != self.sampling_spec.definition_hash):
                raise ValueError("MODEL sample ordering or sampling identity mismatch")

    def _payload(self) -> dict[str, Any]:
        return {"schema_version": "model-sample-manifest-v1", "sampling_spec": self.sampling_spec.to_dict(),
                "samples": [s.to_dict() for s in self.samples], "runtime": dict(self.runtime)}

    @property
    def manifest_hash(self) -> str:
        return canonical_hash(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_hash": self.manifest_hash}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelSampleManifest:
        strict_fields(data, label="MODEL manifest", required={"schema_version", "sampling_spec", "samples", "runtime", "manifest_hash"})
        if data["schema_version"] != "model-sample-manifest-v1":
            raise ValueError("unsupported MODEL manifest schema")
        if type(data["samples"]) is not list or type(data["runtime"]) is not dict:
            raise TypeError("invalid MODEL manifest samples/runtime")
        result = cls(ModelSamplingSpec.from_dict(data["sampling_spec"]),
                     tuple(EnsembleSample.from_dict(s) for s in data["samples"]), tuple(sorted(data["runtime"].items())))
        if data["manifest_hash"] != result.manifest_hash:
            raise ValueError("MODEL manifest integrity mismatch")
        return result

    def to_json(self) -> str:
        return _snapshot(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> ModelSampleManifest:
        return cls.from_dict(_strict_json(text))


def generate_model_sample_manifest(spec: ModelSamplingSpec) -> ModelSampleManifest:
    """Use Phase K scalar/copula kernels in sample-major declared order."""
    if not isinstance(spec, ModelSamplingSpec):
        raise TypeError("spec must be ModelSamplingSpec")
    factor = None
    rows = {}
    if isinstance(spec.dependence, MatrixCorrelation):
        factor = _sequential_psd_cholesky(spec.dependence)
        rows = {name: i for i, name in enumerate(spec.dependence.variable_names)}
    rng = spec.rng.create_generator()
    samples = []
    for index in range(spec.sample_count):
        values, latents = [], []
        for variable in spec.study.variables:
            try:
                row = rows.get(variable.name)
                if row is None:
                    value = sample_distribution(variable.distribution, rng, max_draws_per_value=spec.max_draws_per_value)
                else:
                    latents.append(_standard_normal(rng))
                    latent = sum(factor[row][col] * latents[col] for col in range(row + 1))
                    if not math.isfinite(latent):
                        raise SamplingError("gaussian_copula", "non-finite correlated latent")
                    value = _correlated_marginal_value(variable.distribution, latent)
            except SamplingError as exc:
                raise SampleGenerationError(spec.definition_hash, index, variable.name, exc) from exc
            values.append(value)
        samples.append(EnsembleSample(spec.definition_hash, index, spec.variable_names, tuple(values)))
    return ModelSampleManifest(spec, tuple(samples), tuple(sorted(_runtime().items())))


__all__ = ["ModelSamplingSpec", "ModelSampleManifest", "generate_model_sample_manifest"]
