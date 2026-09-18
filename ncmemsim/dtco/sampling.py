"""Reproducible independent bounded draws and exact immutable sample manifests."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
import platform
from typing import Any
import numpy as np
from .._version import __version__
from ..hashing import canonical_hash
from .spec import BindingScope, ParameterBinding
from .variation import (VariationDefinition, VariationKind, VariationProvenance,
                        UniformVariation, TruncatedNormalVariation)

ALGORITHM = "numpy-pcg64-scalar-rejection-v1"


def _integer(value: int, label: str, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer excluding bool")
    if value < minimum:
        raise ValueError(f"{label} must be >= {minimum}")


@dataclass(frozen=True)
class SamplingSpec:
    variations: tuple[VariationDefinition, ...]
    seed: int
    sample_count: int
    max_draws_per_value: int = 10000

    def __post_init__(self) -> None:
        items = tuple(self.variations)
        if not items or not all(isinstance(v, VariationDefinition) for v in items):
            raise ValueError("variations must contain typed definitions")
        if len({v.name for v in items}) != len(items):
            raise ValueError("duplicate variation name")
        if len({v.binding.binding_id for v in items}) != len(items):
            raise ValueError("duplicate variation binding")
        object.__setattr__(self, "variations", items)
        _integer(self.seed, "seed", 0)
        if self.seed >= 2**128:
            raise ValueError("seed must fit unsigned 128 bits")
        _integer(self.sample_count, "sample_count", 1)
        _integer(self.max_draws_per_value, "max_draws_per_value", 1)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "variations": [v.to_dict() for v in self.variations],
                "seed": self.seed, "sample_count": self.sample_count,
                "max_draws_per_value": self.max_draws_per_value,
                "algorithm": ALGORITHM, "order": "sample-major,declared-variation-order",
                "precision": "float64", "dependence": "independent"}

    @property
    def spec_hash(self) -> str:
        return canonical_hash(self.to_dict())


class SamplingError(ValueError):
    """A bounded draw exhausted its explicit budget; no partial manifest returned."""
    def __init__(self, sample_index: int, variation_name: str, attempts: int):
        self.sample_index = sample_index
        self.variation_name = variation_name
        self.attempts = attempts
        super().__init__(f"sampling exhausted at sample {sample_index}, "
                         f"variation {variation_name!r}, after {attempts} attempts")


@dataclass(frozen=True)
class SampleManifest:
    spec: SamplingSpec
    values: tuple[tuple[float, ...], ...]
    runtime: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SamplingSpec):
            raise TypeError("spec must be SamplingSpec")
        rows = tuple(tuple(row) for row in self.values)
        if len(rows) != self.spec.sample_count:
            raise ValueError("sample count mismatch")
        for row in rows:
            if len(row) != len(self.spec.variations):
                raise ValueError("sample width mismatch")
            for value, variation in zip(row, self.spec.variations):
                if type(value) is not float or not math.isfinite(value):
                    raise ValueError("manifest values must be finite float64-derived floats")
                law = variation.distribution
                if not law.lower <= value <= law.upper:
                    raise ValueError("sample outside distribution bounds")
        runtime = tuple(tuple(pair) for pair in self.runtime)
        if any(len(pair) != 2 for pair in runtime):
            raise ValueError("invalid runtime metadata")
        if tuple(pair[0] for pair in runtime) != ("python", "python_implementation", "numpy", "ncmemsim"):
            raise ValueError("runtime fields/order mismatch")
        if not all(isinstance(value, str) and value.strip() == value and value for pair in runtime for value in pair):
            raise ValueError("runtime metadata must be nonempty text")
        object.__setattr__(self, "values", rows)
        object.__setattr__(self, "runtime", runtime)

    def _payload(self) -> dict[str, Any]:
        return {"schema_version": 1, "spec": self.spec.to_dict(),
                "spec_hash": self.spec.spec_hash, "runtime": dict(self.runtime),
                "samples": [{"sample_index": i, "values": list(row)}
                            for i, row in enumerate(self.values)]}

    @property
    def manifest_hash(self) -> str:
        return canonical_hash(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_hash": self.manifest_hash}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, allow_nan=False)

    @classmethod
    def from_json(cls, text: str) -> SampleManifest:
        """Restore exact inputs without drawing again; validate schema and hashes.

        Integrity hashes are not signatures. Reproduction across arbitrary runtime
        versions is not promised; restored values define the propagation input.
        """
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        raw = json.loads(text, object_pairs_hook=pairs,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
        try:
            definitions = []
            for v in raw["spec"]["variations"]:
                law = v["distribution"]
                if law["family"] == "uniform":
                    distribution = UniformVariation(law["lower"], law["upper"])
                elif law["family"] == "truncated_normal":
                    distribution = TruncatedNormalVariation(law["lower"], law["upper"], law["mean"], law["standard_deviation"])
                else:
                    raise ValueError("unsupported distribution family")
                definitions.append(VariationDefinition(v["name"],
                    ParameterBinding(BindingScope(v["binding"]["scope"]), tuple(v["binding"]["path"])),
                    distribution, v["unit"], VariationKind(v["kind"]),
                    VariationProvenance(**v["provenance"])))
            s = raw["spec"]
            spec = SamplingSpec(tuple(definitions), s["seed"], s["sample_count"], s["max_draws_per_value"])
            runtime = tuple((key, raw["runtime"][key]) for key in
                            ("python", "python_implementation", "numpy", "ncmemsim"))
            result = cls(spec, tuple(tuple(row["values"]) for row in raw["samples"]), runtime)
            # Exact structural comparison rejects extra fields, altered algorithms,
            # unordered indices, noncanonical units and unsupported schema versions.
            if result.to_json() != json.dumps(raw, sort_keys=True, allow_nan=False):
                raise ValueError("manifest schema or integrity mismatch")
            return result
        except (KeyError, TypeError, AttributeError, IndexError) as exc:
            raise ValueError("invalid manifest structure") from exc


def sample_variations(spec: SamplingSpec) -> SampleManifest:
    """Draw serially with a local PCG64 generator and an explicit per-value limit.

    Normal rejection draws from the underlying law, accepting only finite values
    inside the declared bounds. Rare tail/narrow intervals may exhaust the budget;
    failure is explicit, without clipping, substitution or omitted samples.
    """
    if not isinstance(spec, SamplingSpec):
        raise TypeError("spec must be SamplingSpec")
    rng = np.random.Generator(np.random.PCG64(spec.seed))
    rows = []
    for index in range(spec.sample_count):
        row = []
        for variation in spec.variations:
            law = variation.distribution
            for _ in range(spec.max_draws_per_value):
                if isinstance(law, UniformVariation):
                    u = float(rng.random())
                    value = (1.0 - u) * law.lower + u * law.upper
                else:
                    value = law.mean + law.standard_deviation * float(rng.standard_normal())
                if math.isfinite(value) and law.lower <= value <= law.upper:
                    row.append(value)
                    break
            else:
                raise SamplingError(index, variation.name, spec.max_draws_per_value)
        rows.append(tuple(row))
    runtime = (("python", platform.python_version()),
               ("python_implementation", platform.python_implementation()),
               ("numpy", np.__version__), ("ncmemsim", __version__))
    return SampleManifest(spec, tuple(rows), runtime)
