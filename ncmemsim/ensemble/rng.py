# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Explicit random-number-generator contract for Phase K."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..hashing import canonical_hash
from ._serialization import strict_fields


RNG_FAMILY = "numpy.random.Generator"
BIT_GENERATOR = "PCG64"
RNG_ALGORITHM = "numpy-pcg64-v1"
RNG_SCHEMA_VERSION = "ensemble-rng-v1"


@dataclass(frozen=True)
class RNGSpec:
    """Immutable Phase K pseudo-random generator identity."""

    seed: int
    family: str = RNG_FAMILY
    bit_generator: str = BIT_GENERATOR
    algorithm: str = RNG_ALGORITHM
    schema_version: str = RNG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer excluding bool")

        if self.seed < 0 or self.seed >= 2**128:
            raise ValueError(
                "seed must fit an unsigned 128-bit integer"
            )

        if self.family != RNG_FAMILY:
            raise ValueError(
                f"unsupported RNG family {self.family!r}"
            )

        if self.bit_generator != BIT_GENERATOR:
            raise ValueError(
                f"unsupported bit generator {self.bit_generator!r}"
            )

        if self.algorithm != RNG_ALGORITHM:
            raise ValueError(
                f"unsupported RNG algorithm {self.algorithm!r}"
            )

        if self.schema_version != RNG_SCHEMA_VERSION:
            raise ValueError(
                "unsupported RNG schema_version"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "family": self.family,
            "bit_generator": self.bit_generator,
            "algorithm": self.algorithm,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "RNGSpec":
        strict_fields(
            data,
            label="rng-specification",
            required={
                "schema_version",
                "family",
                "bit_generator",
                "algorithm",
                "seed",
            },
        )

        return cls(
            seed=data["seed"],
            family=data["family"],
            bit_generator=data["bit_generator"],
            algorithm=data["algorithm"],
            schema_version=data["schema_version"],
        )

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def create_generator(self) -> np.random.Generator:
        """Create an independent local generator for this specification."""

        return np.random.Generator(
            np.random.PCG64(self.seed)
        )


__all__ = [
    "BIT_GENERATOR",
    "RNG_ALGORITHM",
    "RNG_FAMILY",
    "RNG_SCHEMA_VERSION",
    "RNGSpec",
]
