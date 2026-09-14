from __future__ import annotations

import csv
from pathlib import Path

from .experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)


_OPTICAL_ABSORPTION_HEADER = (
    "wavelength_nm",
    "absorption_coefficient_m_inv",
)

_OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY = (
    "wavelength_nm",
    "absorption_coefficient_m_inv",
    "absorption_uncertainty_m_inv",
)


def _parse_required_float(
    value: str,
    *,
    field_name: str,
    line_number: int,
) -> float:
    text = value.strip()

    if not text:
        raise ValueError(
            f"Missing value for {field_name!r} on CSV line {line_number}."
        )

    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for {field_name!r} "
            f"on CSV line {line_number}: {value!r}."
        ) from exc


def load_optical_absorption_csv(
    path: str | Path,
    *,
    sn_fraction: float,
    metadata: ExperimentalDatasetMetadata,
) -> OpticalAbsorptionDataset:
    """
    Load a normalized optical-absorption dataset from a strict CSV schema.

    Accepted schemas are exactly:

    wavelength_nm,absorption_coefficient_m_inv

    or:

    wavelength_nm,absorption_coefficient_m_inv,absorption_uncertainty_m_inv

    Internal units are therefore explicit and require no unit inference.
    UTF-8 files with or without a byte-order mark are accepted. Completely
    blank data rows are ignored.
    """

    csv_path = Path(path)

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise ValueError(
                "Optical absorption CSV file is empty."
            ) from exc

        if header not in {
            _OPTICAL_ABSORPTION_HEADER,
            _OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY,
        }:
            expected_without_uncertainty = ",".join(
                _OPTICAL_ABSORPTION_HEADER
            )
            expected_with_uncertainty = ",".join(
                _OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY
            )

            raise ValueError(
                "Unsupported optical absorption CSV header. "
                "Expected exactly one of: "
                f"{expected_without_uncertainty!r} or "
                f"{expected_with_uncertainty!r}."
            )

        has_uncertainty = (
            header == _OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY
        )

        wavelengths_nm: list[float] = []
        absorption_coefficients_m_inv: list[float] = []
        absorption_uncertainties_m_inv: list[float] = []

        for line_number, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue

            if len(row) != len(header):
                raise ValueError(
                    f"CSV line {line_number} has {len(row)} fields; "
                    f"expected {len(header)}."
                )

            wavelengths_nm.append(
                _parse_required_float(
                    row[0],
                    field_name="wavelength_nm",
                    line_number=line_number,
                )
            )
            absorption_coefficients_m_inv.append(
                _parse_required_float(
                    row[1],
                    field_name="absorption_coefficient_m_inv",
                    line_number=line_number,
                )
            )

            if has_uncertainty:
                absorption_uncertainties_m_inv.append(
                    _parse_required_float(
                        row[2],
                        field_name="absorption_uncertainty_m_inv",
                        line_number=line_number,
                    )
                )

    if len(wavelengths_nm) < 2:
        raise ValueError(
            "Optical absorption CSV must contain at least two data rows."
        )

    uncertainty = (
        absorption_uncertainties_m_inv
        if has_uncertainty
        else None
    )

    return OpticalAbsorptionDataset(
        wavelength_nm=wavelengths_nm,
        absorption_coefficient_m_inv=absorption_coefficients_m_inv,
        absorption_uncertainty_m_inv=uncertainty,
        sn_fraction=sn_fraction,
        metadata=metadata,
    )


__all__ = [
    "load_optical_absorption_csv",
]
