from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

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

_MEMORY_WINDOW_VS_PROGRAM_VOLTAGE_HEADER = (
    "program_voltage_V",
    "memory_window_V",
)

_MEMORY_WINDOW_VS_PROGRAM_VOLTAGE_HEADER_WITH_UNCERTAINTY = (
    "program_voltage_V",
    "memory_window_V",
    "memory_window_uncertainty_V",
)

_MEMORY_WINDOW_VS_PROGRAMMING_TIME_HEADER = (
    "programming_time_s",
    "memory_window_V",
)

_MEMORY_WINDOW_VS_PROGRAMMING_TIME_HEADER_WITH_UNCERTAINTY = (
    "programming_time_s",
    "memory_window_V",
    "memory_window_uncertainty_V",
)

_RETENTION_DELTA_VFB_HEADER = (
    "time_s",
    "delta_vfb_V",
)

_RETENTION_DELTA_VFB_HEADER_WITH_UNCERTAINTY = (
    "time_s",
    "delta_vfb_V",
    "delta_vfb_uncertainty_V",
)

_RETENTION_CHARGE_FRACTION_HEADER = (
    "time_s",
    "total_charge_retention_fraction",
)

_RETENTION_CHARGE_FRACTION_HEADER_WITH_UNCERTAINTY = (
    "time_s",
    "total_charge_retention_fraction",
    "total_charge_retention_fraction_uncertainty",
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


def _normalize_positive_float(
    value: float,
    *,
    field_name: str,
) -> float:
    normalized = float(value)

    if not math.isfinite(normalized) or normalized <= 0.0:
        raise ValueError(
            f"{field_name} must be finite and strictly positive."
        )

    return normalized


def _normalize_finite_float(
    value: float,
    *,
    field_name: str,
) -> float:
    normalized = float(value)

    if not math.isfinite(normalized):
        raise ValueError(
            f"{field_name} must be finite."
        )

    return normalized


def _read_strict_two_or_three_column_csv(
    path: str | Path,
    *,
    header_without_uncertainty: tuple[str, str],
    header_with_uncertainty: tuple[str, str, str],
    dataset_label: str,
) -> tuple[
    list[float],
    list[float],
    list[float] | None,
]:
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
                f"{dataset_label} CSV file is empty."
            ) from exc

        if header not in {
            header_without_uncertainty,
            header_with_uncertainty,
        }:
            expected_without_uncertainty = ",".join(
                header_without_uncertainty
            )
            expected_with_uncertainty = ",".join(
                header_with_uncertainty
            )

            raise ValueError(
                f"Unsupported {dataset_label} CSV header. "
                "Expected exactly one of: "
                f"{expected_without_uncertainty!r} or "
                f"{expected_with_uncertainty!r}."
            )

        has_uncertainty = (
            header == header_with_uncertainty
        )

        independent_values: list[float] = []
        observed_values: list[float] = []
        uncertainties: list[float] = []

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

            independent_values.append(
                _parse_required_float(
                    row[0],
                    field_name=header[0],
                    line_number=line_number,
                )
            )
            observed_values.append(
                _parse_required_float(
                    row[1],
                    field_name=header[1],
                    line_number=line_number,
                )
            )

            if has_uncertainty:
                uncertainties.append(
                    _parse_required_float(
                        row[2],
                        field_name=header[2],
                        line_number=line_number,
                    )
                )

    if len(independent_values) < 2:
        raise ValueError(
            f"{dataset_label} CSV must contain "
            "at least two data rows."
        )

    return (
        independent_values,
        observed_values,
        uncertainties if has_uncertainty else None,
    )


def _validate_retention_times(
    time_s: list[float],
) -> None:
    times = np.asarray(time_s, dtype=float)

    if not np.all(np.isfinite(times)):
        raise ValueError(
            "time_s values must contain only finite values."
        )

    if np.any(times < 0.0):
        raise ValueError(
            "time_s values must be non-negative."
        )

    if np.any(np.diff(times) <= 0.0):
        raise ValueError(
            "time_s values must be strictly increasing."
        )


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

    (
        wavelengths_nm,
        absorption_coefficients_m_inv,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=(
            _OPTICAL_ABSORPTION_HEADER
        ),
        header_with_uncertainty=(
            _OPTICAL_ABSORPTION_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="optical absorption",
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

    (
        gate_voltages_V,
        capacitances_F_m2,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=_CV_HEADER,
        header_with_uncertainty=(
            _CV_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="C-V",
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


def load_memory_window_vs_program_voltage_csv(
    path: str | Path,
    *,
    metadata: ExperimentalDatasetMetadata,
    program_pulse_width_s: float,
    measurement_frequency_Hz: float | None = None,
) -> DeviceObservableDataset:
    """
    Load memory window versus program-voltage data from a strict CSV schema.

    Accepted schemas are exactly:

    program_voltage_V,memory_window_V

    or:

    program_voltage_V,memory_window_V,memory_window_uncertainty_V

    ``program_pulse_width_s`` is required because pulse duration is a
    physically relevant fixed condition when program voltage is scanned.

    The returned canonical device-observable dataset uses:

    - independent variable: ``program_voltage`` in V;
    - observable: ``memory_window`` in V;
    - condition: ``program_pulse_width`` in s;
    - optional condition: ``measurement_frequency`` in Hz.

    Input row order is preserved exactly.
    """

    if not isinstance(
        metadata,
        ExperimentalDatasetMetadata,
    ):
        raise TypeError(
            "metadata must be an "
            "ExperimentalDatasetMetadata instance."
        )

    pulse_width_s = _normalize_positive_float(
        program_pulse_width_s,
        field_name="program_pulse_width_s",
    )
    frequency = _normalize_measurement_frequency_Hz(
        measurement_frequency_Hz
    )

    (
        program_voltages_V,
        memory_windows_V,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=(
            _MEMORY_WINDOW_VS_PROGRAM_VOLTAGE_HEADER
        ),
        header_with_uncertainty=(
            _MEMORY_WINDOW_VS_PROGRAM_VOLTAGE_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="memory-window/program-voltage",
    )

    conditions = [
        ExperimentalCondition(
            name="program_pulse_width",
            value=pulse_width_s,
            unit="s",
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

    return DeviceObservableDataset(
        independent_variable_name="program_voltage",
        independent_variable_unit="V",
        independent_values=program_voltages_V,
        observable_name="memory_window",
        observable_unit="V",
        observed_values=memory_windows_V,
        observed_uncertainty=uncertainty,
        metadata=metadata,
        conditions=tuple(conditions),
    )


def load_memory_window_vs_programming_time_csv(
    path: str | Path,
    *,
    metadata: ExperimentalDatasetMetadata,
    program_voltage_V: float,
    measurement_frequency_Hz: float | None = None,
) -> DeviceObservableDataset:
    """
    Load memory window versus programming-time data from a strict CSV schema.

    Accepted schemas are exactly:

    programming_time_s,memory_window_V

    or:

    programming_time_s,memory_window_V,memory_window_uncertainty_V

    ``program_voltage_V`` is required because program bias is a physically
    relevant fixed condition when programming time is scanned.

    The returned canonical device-observable dataset uses:

    - independent variable: ``programming_time`` in s;
    - observable: ``memory_window`` in V;
    - condition: ``program_voltage`` in V;
    - optional condition: ``measurement_frequency`` in Hz.

    Programming-time values must be strictly positive. Input row order is
    preserved exactly.
    """

    if not isinstance(
        metadata,
        ExperimentalDatasetMetadata,
    ):
        raise TypeError(
            "metadata must be an "
            "ExperimentalDatasetMetadata instance."
        )

    voltage_V = _normalize_finite_float(
        program_voltage_V,
        field_name="program_voltage_V",
    )
    frequency = _normalize_measurement_frequency_Hz(
        measurement_frequency_Hz
    )

    (
        programming_times_s,
        memory_windows_V,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=(
            _MEMORY_WINDOW_VS_PROGRAMMING_TIME_HEADER
        ),
        header_with_uncertainty=(
            _MEMORY_WINDOW_VS_PROGRAMMING_TIME_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="memory-window/programming-time",
    )

    if any(
        time_s <= 0.0
        for time_s in programming_times_s
    ):
        raise ValueError(
            "programming_time_s values must be "
            "strictly positive."
        )

    conditions = [
        ExperimentalCondition(
            name="program_voltage",
            value=voltage_V,
            unit="V",
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

    return DeviceObservableDataset(
        independent_variable_name="programming_time",
        independent_variable_unit="s",
        independent_values=programming_times_s,
        observable_name="memory_window",
        observable_unit="V",
        observed_values=memory_windows_V,
        observed_uncertainty=uncertainty,
        metadata=metadata,
        conditions=tuple(conditions),
    )


def load_retention_delta_vfb_csv(
    path: str | Path,
    *,
    metadata: ExperimentalDatasetMetadata,
    retention_gate_voltage_V: float,
    measurement_frequency_Hz: float | None = None,
) -> DeviceObservableDataset:
    """
    Load retention flat-band-voltage shift versus time from strict CSV.

    Accepted schemas are exactly:

    time_s,delta_vfb_V

    or:

    time_s,delta_vfb_V,delta_vfb_uncertainty_V

    Retention times must be finite, non-negative, and strictly increasing.
    A first point at t = 0 is allowed but is not required.

    ``retention_gate_voltage_V`` maps directly to
    ``RetentionConfig.gate_voltage_V``. ``measurement_frequency_Hz`` is
    optional readout metadata for electrically extracted flat-band shifts.

    The returned canonical device-observable dataset uses:

    - independent variable: ``time`` in s;
    - observable: ``delta_vfb`` in V;
    - condition: ``retention_gate_voltage`` in V;
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

    gate_voltage_V = _normalize_finite_float(
        retention_gate_voltage_V,
        field_name="retention_gate_voltage_V",
    )
    frequency = _normalize_measurement_frequency_Hz(
        measurement_frequency_Hz
    )

    (
        time_s,
        delta_vfb_V,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=(
            _RETENTION_DELTA_VFB_HEADER
        ),
        header_with_uncertainty=(
            _RETENTION_DELTA_VFB_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="retention/delta-vfb",
    )

    _validate_retention_times(time_s)

    conditions = [
        ExperimentalCondition(
            name="retention_gate_voltage",
            value=gate_voltage_V,
            unit="V",
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

    return DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=time_s,
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=delta_vfb_V,
        observed_uncertainty=uncertainty,
        metadata=metadata,
        conditions=tuple(conditions),
    )


def load_retention_charge_fraction_csv(
    path: str | Path,
    *,
    metadata: ExperimentalDatasetMetadata,
    retention_gate_voltage_V: float,
    measurement_frequency_Hz: float | None = None,
) -> DeviceObservableDataset:
    """
    Load normalized total-charge retention versus time from strict CSV.

    Accepted schemas are exactly:

    time_s,total_charge_retention_fraction

    or:

    time_s,total_charge_retention_fraction,total_charge_retention_fraction_uncertainty

    Retention times must be finite, non-negative, and strictly increasing.
    A first point at t = 0 is allowed but is not required.

    The observable name intentionally matches
    ``RetentionResult.total_charge_retention_fraction``. No [0, 1] bound is
    imposed because experimental noise or charge redistribution can produce
    values slightly above unity, and the simulator itself does not impose
    such a bound on q(t) / q(0).

    The returned canonical device-observable dataset uses:

    - independent variable: ``time`` in s;
    - observable: ``total_charge_retention_fraction`` (dimensionless);
    - condition: ``retention_gate_voltage`` in V;
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

    gate_voltage_V = _normalize_finite_float(
        retention_gate_voltage_V,
        field_name="retention_gate_voltage_V",
    )
    frequency = _normalize_measurement_frequency_Hz(
        measurement_frequency_Hz
    )

    (
        time_s,
        retention_fraction,
        uncertainty,
    ) = _read_strict_two_or_three_column_csv(
        path,
        header_without_uncertainty=(
            _RETENTION_CHARGE_FRACTION_HEADER
        ),
        header_with_uncertainty=(
            _RETENTION_CHARGE_FRACTION_HEADER_WITH_UNCERTAINTY
        ),
        dataset_label="retention/charge-fraction",
    )

    _validate_retention_times(time_s)

    conditions = [
        ExperimentalCondition(
            name="retention_gate_voltage",
            value=gate_voltage_V,
            unit="V",
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

    return DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=time_s,
        observable_name="total_charge_retention_fraction",
        observable_unit=None,
        observed_values=retention_fraction,
        observed_uncertainty=uncertainty,
        metadata=metadata,
        conditions=tuple(conditions),
    )


__all__ = [
    "load_cv_csv",
    "load_memory_window_vs_program_voltage_csv",
    "load_memory_window_vs_programming_time_csv",
    "load_optical_absorption_csv",
    "load_retention_charge_fraction_csv",
    "load_retention_delta_vfb_csv",
]
