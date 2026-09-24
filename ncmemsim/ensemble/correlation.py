"""Dependence contracts for Phase K ensemble sampling."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any

import numpy as np

from ..hashing import canonical_hash
from ..materials.provenance import ParameterProvenance
from ._serialization import (
    parameter_provenance_from_dict,
    strict_fields,
)


DEPENDENCE_SCHEMA_VERSION = "ensemble-dependence-v1"

GAUSSIAN_COPULA_KIND = "gaussian_copula"
GAUSSIAN_COPULA_REPRESENTATION = "latent_gaussian_pearson"

DEFAULT_CORRELATION_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class IndependentDependence:
    """Explicit independent-sampling dependence contract."""

    kind: str = "independent"
    schema_version: str = DEPENDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.kind != "independent":
            raise ValueError(
                f"unsupported dependence kind {self.kind!r}"
            )

        if self.schema_version != DEPENDENCE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported dependence schema_version"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "IndependentDependence":
        strict_fields(
            data,
            label="dependence-specification",
            required={
                "schema_version",
                "kind",
            },
        )

        return cls(
            kind=data["kind"],
            schema_version=data["schema_version"],
        )

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class MatrixCorrelation:
    """Gaussian-copula latent correlation specification."""

    variable_names: tuple[str, ...]
    matrix: tuple[tuple[float, ...], ...]
    provenance: ParameterProvenance
    applicability: str
    numerical_tolerance: float = DEFAULT_CORRELATION_TOLERANCE
    kind: str = GAUSSIAN_COPULA_KIND
    representation: str = GAUSSIAN_COPULA_REPRESENTATION
    schema_version: str = DEPENDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        variable_names = tuple(self.variable_names)

        if len(variable_names) < 2:
            raise ValueError(
                "matrix correlation requires at least two variables"
            )

        for name in variable_names:
            if (
                not isinstance(name, str)
                or not name
                or name != name.strip()
            ):
                raise ValueError(
                    "correlation variable names must be "
                    "nonempty normalized text"
                )

        if len(set(variable_names)) != len(variable_names):
            raise ValueError(
                "correlation variable names must be unique"
            )

        if not isinstance(self.provenance, ParameterProvenance):
            raise TypeError(
                "provenance must be ParameterProvenance"
            )

        if (
            not isinstance(self.applicability, str)
            or not self.applicability
            or self.applicability != self.applicability.strip()
        ):
            raise ValueError(
                "applicability must be nonempty normalized text"
            )

        if (
            isinstance(self.numerical_tolerance, bool)
            or not isinstance(self.numerical_tolerance, Real)
        ):
            raise TypeError(
                "numerical_tolerance must be a real number excluding bool"
            )

        tolerance = float(self.numerical_tolerance)

        if (
            not math.isfinite(tolerance)
            or tolerance <= 0.0
        ):
            raise ValueError(
                "numerical_tolerance must be positive and finite"
            )

        if self.kind != GAUSSIAN_COPULA_KIND:
            raise ValueError(
                f"unsupported dependence kind {self.kind!r}"
            )

        if (
            self.representation
            != GAUSSIAN_COPULA_REPRESENTATION
        ):
            raise ValueError(
                "unsupported correlation representation"
            )

        if self.schema_version != DEPENDENCE_SCHEMA_VERSION:
            raise ValueError(
                "unsupported dependence schema_version"
            )

        try:
            rows = tuple(
                tuple(row)
                for row in self.matrix
            )
        except TypeError as exc:
            raise TypeError(
                "correlation matrix must be a two-dimensional sequence"
            ) from exc

        size = len(variable_names)

        if len(rows) != size:
            raise ValueError(
                "correlation matrix size must match variable_names"
            )

        normalized_rows: list[tuple[float, ...]] = []

        for row in rows:
            if len(row) != size:
                raise ValueError(
                    "correlation matrix must be square"
                )

            normalized_row: list[float] = []

            for value in row:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, Real)
                ):
                    raise TypeError(
                        "correlation matrix entries must be "
                        "real numbers excluding bool"
                    )

                number = float(value)

                if not math.isfinite(number):
                    raise ValueError(
                        "correlation matrix entries must be finite"
                    )

                if number < -1.0 or number > 1.0:
                    raise ValueError(
                        "correlation matrix entries must lie "
                        "within [-1, 1]"
                    )

                normalized_row.append(number)

            normalized_rows.append(
                tuple(normalized_row)
            )

        matrix = tuple(normalized_rows)

        for index in range(size):
            if (
                abs(matrix[index][index] - 1.0)
                > tolerance
            ):
                raise ValueError(
                    "correlation matrix diagonal must equal "
                    "one within numerical_tolerance"
                )

        for row_index in range(size):
            for column_index in range(
                row_index + 1,
                size,
            ):
                if (
                    abs(
                        matrix[row_index][column_index]
                        - matrix[column_index][row_index]
                    )
                    > tolerance
                ):
                    raise ValueError(
                        "correlation matrix must be symmetric "
                        "within numerical_tolerance"
                    )

        array = np.asarray(
            matrix,
            dtype=np.float64,
        )

        symmetric_validation_matrix = (
            0.5 * (array + array.T)
        )

        eigenvalues = np.linalg.eigvalsh(
            symmetric_validation_matrix
        )

        if not np.all(np.isfinite(eigenvalues)):
            raise ValueError(
                "correlation matrix eigenvalues must be finite"
            )

        if float(np.min(eigenvalues)) < -tolerance:
            raise ValueError(
                "correlation matrix must be positive semidefinite "
                "within numerical_tolerance"
            )

        object.__setattr__(
            self,
            "variable_names",
            variable_names,
        )
        object.__setattr__(
            self,
            "matrix",
            matrix,
        )
        object.__setattr__(
            self,
            "numerical_tolerance",
            tolerance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "representation": self.representation,
            "variable_names": list(
                self.variable_names
            ),
            "matrix": [
                list(row)
                for row in self.matrix
            ],
            "numerical_tolerance": (
                self.numerical_tolerance
            ),
            "provenance": self.provenance.to_dict(),
            "applicability": self.applicability,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "MatrixCorrelation":
        strict_fields(
            data,
            label="matrix-correlation",
            required={
                "schema_version",
                "kind",
                "representation",
                "variable_names",
                "matrix",
                "numerical_tolerance",
                "provenance",
                "applicability",
            },
        )

        if not isinstance(
            data["variable_names"],
            list,
        ):
            raise TypeError(
                "matrix-correlation variable_names must be a list"
            )

        if not isinstance(data["matrix"], list):
            raise TypeError(
                "matrix-correlation matrix must be a list"
            )

        for row in data["matrix"]:
            if not isinstance(row, list):
                raise TypeError(
                    "matrix-correlation rows must be lists"
                )

        return cls(
            variable_names=tuple(
                data["variable_names"]
            ),
            matrix=tuple(
                tuple(row)
                for row in data["matrix"]
            ),
            provenance=parameter_provenance_from_dict(
                data["provenance"]
            ),
            applicability=data["applicability"],
            numerical_tolerance=(
                data["numerical_tolerance"]
            ),
            kind=data["kind"],
            representation=data["representation"],
            schema_version=data["schema_version"],
        )

    @property
    def definition_hash(self) -> str:
        return canonical_hash(self.to_dict())


DependenceSpec = (
    IndependentDependence
    | MatrixCorrelation
)


def dependence_from_dict(
    data: dict[str, Any],
) -> DependenceSpec:
    """Restore one supported Phase K dependence specification."""

    if not isinstance(data, dict):
        raise TypeError(
            "dependence specification data must be a dict"
        )

    if "kind" not in data:
        raise ValueError(
            "missing dependence-specification fields: kind"
        )

    kind = data["kind"]

    if not isinstance(kind, str):
        raise TypeError(
            "dependence specification kind must be text"
        )

    if kind == "independent":
        return IndependentDependence.from_dict(data)

    if kind == GAUSSIAN_COPULA_KIND:
        return MatrixCorrelation.from_dict(data)

    raise ValueError(
        f"unsupported dependence kind {kind!r}"
    )


__all__ = [
    "DEFAULT_CORRELATION_TOLERANCE",
    "DEPENDENCE_SCHEMA_VERSION",
    "DependenceSpec",
    "GAUSSIAN_COPULA_KIND",
    "GAUSSIAN_COPULA_REPRESENTATION",
    "IndependentDependence",
    "MatrixCorrelation",
    "dependence_from_dict",
]
