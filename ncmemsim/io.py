from __future__ import annotations

import csv
import math
from pathlib import Path

from .experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
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

_CV_HEADER = (
    "gate_voltage_V",
    "capacitance_F_m2",
)

_CV_HEADER_WITH_UNCERTAINTY = (
    "gate_voltage_V",
    "capacitance_F_m2",
    "capacitance_uncertainty_F_m2",
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


def _normalize_sweep_direction(
    sweep_direction: str,
) -> str:
    normalized = sweep_direction.strip().lower()

    if normalized not in {"forward", "backward"}:
        raise ValueError(
            "sweep_direction must be exactly "
            "'forward' or 'backward'."
        )

    return normalized


def _normalize_measurement_frequency_Hz(
    measurement_frequency_Hz: float | None,
) -> float | None:
    if measurement_frequency_Hz is None:
        return None

    frequency = float(measurement_frequency_Hz)

    if not math.isfinite(frequency) or frequency <= 0.0:
        raise ValueError(
            "measurement_frequency_Hz must be "
            "finite and strictly positive."
        )

    return frequency


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
            header
            == _OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY
        )

        wavelengths_nm: list[float] = []
        absorption_coefficients_m_inv: list[float] = []
        absorption_uncertainties_m_inv: list[float] = []

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            if not row or all(
                not cell.strip()
                for cell in row
            ):
                continue

            if len(row) != len(header):
                raise ValueError(
                    f"CSV line {line_number} has "
                    f"{len(row)} fields; expected "
                    f"{len(header)}."
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
                    field_name=(
                        "absorption_coefficient_m_inv"
                    ),
                    line_number=line_number,
                )
            )

            if has_uncertainty:
                absorption_uncertainties_m_inv.append(
                    _parse_required_float(
                        row[2],
                        field_name=(
                            "absorption_uncertainty_m_inv"
                        ),
                        line_number=line_number,
                    )
                )

    if len(wavelengths_nm) < 2:
        raise ValueError(
            "Optical absorption CSV must contain "
            "at least two data rows."
        )

    uncertainty = (
        absorption_uncertainties_m_inv
        if has_uncertainty
        else None
    )

    return OpticalAbsorptionDataset(
        wavelength_nm=wavelengths_nm,
        absorption_coefficient_m_inv=(
            absorption_coefficients_m_inv
        ),
        absorption_uncertainty_m_inv=uncertainty,
        sn_fraction=sn_fraction,
        metadata=metadata,
    )


def load_cv_csv(
    path: str | Path,
    *,
    metadata: ExperimentalDatasetMetadata,
    sweep_direction: str,
    measurement_frequency_Hz: float | None = None,
) -> DeviceObservableDataset:
    """
    Load one experimental C-V sweep from a strict CSV schema.

    Accepted schemas are exactly:

    gate_voltage_V,capacitance_F_m2

    or:

    gate_voltage_V,capacitance_F_m2,capacitance_uncertainty_F_m2

    Row order is preserved exactly because sweep order is part of the
    experimental protocol. The loader does not sort gate voltage.

    ``sweep_direction`` must be ``"forward"`` or ``"backward"``.
    ``measurement_frequency_Hz`` is optional but, when supplied, must be
    finite and strictly positive.

    The returned canonical device-observable dataset uses:

    - independent variable: ``gate_voltage`` in V;
    - observable: ``capacitance`` in F/m^2;
    - condition: ``sweep_direction``;
    - optional condition: ``measurement_frequency`` in Hz.
    """

    if not isinstance(
        metadata,
        ExperimentalDatasetMetadata,
    ):
        raise TypeError(
            "metadata must be an "
            "ExperimentalDatasetMetadata instance."
        )

    direction = _normalize_sweep_direction(
        sweep_direction
    )
    frequency = _normalize_measurement_frequency_Hz(
        measurement_frequency_Hz
    )

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
                "C-V CSV file is empty."
            ) from exc

        if header not in {
            _CV_HEADER,
            _CV_HEADER_WITH_UNCERTAINTY,
        }:
            expected_without_uncertainty = ",".join(
                _CV_HEADER
            )
            expected_with_uncertainty = ",".join(
                _CV_HEADER_WITH_UNCERTAINTY
            )

            raise ValueError(
                "Unsupported C-V CSV header. "
                "Expected exactly one of: "
                f"{expected_without_uncertainty!r} or "
                f"{expected_with_uncertainty!r}."
            )

        has_uncertainty = (
            header
            == _CV_HEADER_WITH_UNCERTAINTY
        )

        gate_voltages_V: list[float] = []
        capacitances_F_m2: list[float] = []
        capacitance_uncertainties_F_m2: list[float] = []

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            if not row or all(
                not cell.strip()
                for cell in row
            ):
                continue

            if len(row) != len(header):
                raise ValueError(
                    f"CSV line {line_number} has "
                    f"{len(row)} fields; expected "
                    f"{len(header)}."
                )

            gate_voltages_V.append(
                _parse_required_float(
                    row[0],
                    field_name="gate_voltage_V",
                    line_number=line_number,
                )
            )
            capacitances_F_m2.append(
                _parse_required_float(
                    row[1],
                    field_name="capacitance_F_m2",
                    line_number=line_number,
                )
            )

            if has_uncertainty:
                capacitance_uncertainties_F_m2.append(
                    _parse_required_float(
                        row[2],
                        field_name=(
                            "capacitance_uncertainty_F_m2"
                        ),
                        line_number=line_number,
                    )
                )

    if len(gate_voltages_V) < 2:
        raise ValueError(
            "C-V CSV must contain at least two "
            "data rows."
        )

    conditions = [
        ExperimentalCondition(
            name="sweep_direction",
            value=direction,
        )
    ]

    if frequency is not None:
        conditions.append(
            ExperimentalCondition(
                name="measurement_frequency",
                value=frequency,
                unit="Hz",
            )
        )

    uncertainty = (
        capacitance_uncertainties_F_m2
        if has_uncertainty
        else None
    )

    return DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=gate_voltages_V,
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=capacitances_F_m2,
        observed_uncertainty=uncertainty,
        metadata=metadata,
        conditions=tuple(conditions),
    )


__all__ = [
    "load_cv_csv",
    "load_optical_absorption_csv",
]
