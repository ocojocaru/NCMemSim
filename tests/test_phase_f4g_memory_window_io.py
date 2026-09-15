from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalDatasetMetadata,
)
from ncmemsim.io import (
    load_memory_window_vs_program_voltage_csv,
    load_memory_window_vs_programming_time_csv,
)


@pytest.fixture
def metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="memory-window-test",
        source="Synthetic memory-window test data",
        sample_id="sample-mw",
        temperature_K=300.0,
    )


def _write(
    path: Path,
    text: str,
) -> Path:
    path.write_text(
        text,
        encoding="utf-8",
        newline="",
    )
    return path


def test_load_memory_window_vs_program_voltage_without_uncertainty(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw_vs_voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
            "4.0,2.1\n"
        ),
    )

    dataset = load_memory_window_vs_program_voltage_csv(
        path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )

    assert isinstance(
        dataset,
        DeviceObservableDataset,
    )
    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert dataset.independent_variable_name == "program_voltage"
    assert dataset.independent_variable_unit == "V"
    assert dataset.observable_name == "memory_window"
    assert dataset.observable_unit == "V"
    assert np.allclose(
        dataset.independent_values,
        [2.0, 3.0, 4.0],
    )
    assert np.allclose(
        dataset.observed_values,
        [0.5, 1.2, 2.1],
    )
    assert dataset.condition_dict == {
        "program_pulse_width": 1.0e-3,
    }


def test_load_memory_window_vs_program_voltage_with_uncertainty_and_frequency(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw_vs_voltage_unc.csv",
        (
            "program_voltage_V,memory_window_V,"
            "memory_window_uncertainty_V\n"
            "2.0,0.5,0.05\n"
            "3.0,1.2,0.08\n"
            "4.0,2.1,0.10\n"
        ),
    )

    dataset = load_memory_window_vs_program_voltage_csv(
        path,
        metadata=metadata,
        program_pulse_width_s=2.0e-3,
        measurement_frequency_Hz=1.0e6,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.05, 0.08, 0.10],
    )
    assert dataset.condition_dict == {
        "measurement_frequency": 1.0e6,
        "program_pulse_width": 2.0e-3,
    }


def test_load_memory_window_vs_programming_time_without_uncertainty(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw_vs_time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.0001,0.2\n"
            "0.001,0.8\n"
            "0.01,1.6\n"
        ),
    )

    dataset = load_memory_window_vs_programming_time_csv(
        path,
        metadata=metadata,
        program_voltage_V=4.0,
    )

    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert dataset.independent_variable_name == "programming_time"
    assert dataset.independent_variable_unit == "s"
    assert dataset.observable_name == "memory_window"
    assert dataset.observable_unit == "V"
    assert np.allclose(
        dataset.independent_values,
        [1.0e-4, 1.0e-3, 1.0e-2],
    )
    assert np.allclose(
        dataset.observed_values,
        [0.2, 0.8, 1.6],
    )
    assert dataset.condition_dict == {
        "program_voltage": 4.0,
    }


def test_load_memory_window_vs_programming_time_with_uncertainty_and_frequency(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw_vs_time_unc.csv",
        (
            "programming_time_s,memory_window_V,"
            "memory_window_uncertainty_V\n"
            "0.0001,0.2,0.02\n"
            "0.001,0.8,0.05\n"
            "0.01,1.6,0.08\n"
        ),
    )

    dataset = load_memory_window_vs_programming_time_csv(
        path,
        metadata=metadata,
        program_voltage_V=-4.0,
        measurement_frequency_Hz=1.0e5,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.02, 0.05, 0.08],
    )
    assert dataset.condition_dict == {
        "measurement_frequency": 1.0e5,
        "program_voltage": -4.0,
    }


def test_program_voltage_row_order_is_preserved(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "descending_voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "4.0,2.1\n"
            "3.0,1.2\n"
            "2.0,0.5\n"
        ),
    )

    dataset = load_memory_window_vs_program_voltage_csv(
        path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )

    assert np.array_equal(
        dataset.independent_values,
        np.array([4.0, 3.0, 2.0]),
    )
    assert np.array_equal(
        dataset.observed_values,
        np.array([2.1, 1.2, 0.5]),
    )


def test_programming_time_row_order_is_preserved(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "descending_time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.01,1.6\n"
            "0.001,0.8\n"
            "0.0001,0.2\n"
        ),
    )

    dataset = load_memory_window_vs_programming_time_csv(
        path,
        metadata=metadata,
        program_voltage_V=4.0,
    )

    assert np.array_equal(
        dataset.independent_values,
        np.array([1.0e-2, 1.0e-3, 1.0e-4]),
    )


@pytest.mark.parametrize(
    "pulse_width",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_program_voltage_loader_rejects_invalid_pulse_width(
    tmp_path,
    metadata,
    pulse_width,
):
    path = _write(
        tmp_path / "mw.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="program_pulse_width_s",
    ):
        load_memory_window_vs_program_voltage_csv(
            path,
            metadata=metadata,
            program_pulse_width_s=pulse_width,
        )


@pytest.mark.parametrize(
    "program_voltage",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_programming_time_loader_rejects_nonfinite_program_voltage(
    tmp_path,
    metadata,
    program_voltage,
):
    path = _write(
        tmp_path / "mw.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "0.010,1.2\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="program_voltage_V",
    ):
        load_memory_window_vs_programming_time_csv(
            path,
            metadata=metadata,
            program_voltage_V=program_voltage,
        )


@pytest.mark.parametrize(
    "bad_time",
    [
        "0.0",
        "-0.001",
    ],
)
def test_programming_time_loader_requires_positive_times(
    tmp_path,
    metadata,
    bad_time,
):
    path = _write(
        tmp_path / "mw.csv",
        (
            "programming_time_s,memory_window_V\n"
            f"{bad_time},0.5\n"
            "0.010,1.2\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="programming_time_s values",
    ):
        load_memory_window_vs_programming_time_csv(
            path,
            metadata=metadata,
            program_voltage_V=4.0,
        )


@pytest.mark.parametrize(
    "frequency",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
@pytest.mark.parametrize(
    "loader_kind",
    [
        "voltage",
        "time",
    ],
)
def test_memory_window_loaders_reject_invalid_frequency(
    tmp_path,
    metadata,
    frequency,
    loader_kind,
):
    if loader_kind == "voltage":
        path = _write(
            tmp_path / "mw_voltage.csv",
            (
                "program_voltage_V,memory_window_V\n"
                "2.0,0.5\n"
                "3.0,1.2\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="measurement_frequency_Hz",
        ):
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
                measurement_frequency_Hz=frequency,
            )
    else:
        path = _write(
            tmp_path / "mw_time.csv",
            (
                "programming_time_s,memory_window_V\n"
                "0.001,0.5\n"
                "0.010,1.2\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="measurement_frequency_Hz",
        ):
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
                measurement_frequency_Hz=frequency,
            )


def test_memory_window_loaders_require_metadata(
    tmp_path,
):
    voltage_path = _write(
        tmp_path / "voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
        ),
    )
    time_path = _write(
        tmp_path / "time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "0.010,1.2\n"
        ),
    )

    with pytest.raises(TypeError):
        load_memory_window_vs_program_voltage_csv(
            voltage_path,
            metadata="bad",
            program_pulse_width_s=1.0e-3,
        )

    with pytest.raises(TypeError):
        load_memory_window_vs_programming_time_csv(
            time_path,
            metadata="bad",
            program_voltage_V=4.0,
        )


@pytest.mark.parametrize(
    ("loader_kind", "header"),
    [
        (
            "voltage",
            "program_voltage,memory_window_V",
        ),
        (
            "voltage",
            "program_voltage_V,memory_window",
        ),
        (
            "voltage",
            (
                "program_voltage_V,memory_window_V,"
                "uncertainty"
            ),
        ),
        (
            "time",
            "programming_time,memory_window_V",
        ),
        (
            "time",
            "programming_time_s,memory_window",
        ),
        (
            "time",
            (
                "programming_time_s,memory_window_V,"
                "uncertainty"
            ),
        ),
    ],
)
def test_memory_window_loaders_reject_unsupported_headers(
    tmp_path,
    metadata,
    loader_kind,
    header,
):
    path = _write(
        tmp_path / "bad.csv",
        (
            f"{header}\n"
            "1.0,0.5\n"
            "2.0,1.0\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        if loader_kind == "voltage":
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
            )
        else:
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    [
        "voltage",
        "time",
    ],
)
def test_memory_window_loaders_reject_empty_files(
    tmp_path,
    metadata,
    loader_kind,
):
    path = _write(
        tmp_path / "empty.csv",
        "",
    )

    with pytest.raises(
        ValueError,
        match="CSV file is empty",
    ):
        if loader_kind == "voltage":
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
            )
        else:
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    [
        "voltage",
        "time",
    ],
)
def test_memory_window_loaders_require_two_rows(
    tmp_path,
    metadata,
    loader_kind,
):
    if loader_kind == "voltage":
        path = _write(
            tmp_path / "one.csv",
            (
                "program_voltage_V,memory_window_V\n"
                "2.0,0.5\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="at least two data rows",
        ):
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
            )
    else:
        path = _write(
            tmp_path / "one.csv",
            (
                "programming_time_s,memory_window_V\n"
                "0.001,0.5\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="at least two data rows",
        ):
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    [
        "voltage",
        "time",
    ],
)
def test_memory_window_loaders_accept_utf8_bom_and_blank_rows(
    tmp_path,
    metadata,
    loader_kind,
):
    path = tmp_path / "bom.csv"

    if loader_kind == "voltage":
        text = (
            "\ufeffprogram_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "\n"
            "   ,   \n"
            "3.0,1.2\n"
        )
    else:
        text = (
            "\ufeffprogramming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "\n"
            "   ,   \n"
            "0.010,1.2\n"
        )

    path.write_text(
        text,
        encoding="utf-8",
    )

    if loader_kind == "voltage":
        dataset = load_memory_window_vs_program_voltage_csv(
            path,
            metadata=metadata,
            program_pulse_width_s=1.0e-3,
        )
    else:
        dataset = load_memory_window_vs_programming_time_csv(
            path,
            metadata=metadata,
            program_voltage_V=4.0,
        )

    assert dataset.n_points == 2


@pytest.mark.parametrize(
    ("loader_kind", "row", "field_name"),
    [
        (
            "voltage",
            ",0.5",
            "program_voltage_V",
        ),
        (
            "voltage",
            "bad,0.5",
            "program_voltage_V",
        ),
        (
            "voltage",
            "2.0,",
            "memory_window_V",
        ),
        (
            "voltage",
            "2.0,bad",
            "memory_window_V",
        ),
        (
            "time",
            ",0.5",
            "programming_time_s",
        ),
        (
            "time",
            "bad,0.5",
            "programming_time_s",
        ),
        (
            "time",
            "0.001,",
            "memory_window_V",
        ),
        (
            "time",
            "0.001,bad",
            "memory_window_V",
        ),
    ],
)
def test_memory_window_loaders_reject_missing_or_invalid_required_values(
    tmp_path,
    metadata,
    loader_kind,
    row,
    field_name,
):
    if loader_kind == "voltage":
        header = "program_voltage_V,memory_window_V"
        good_row = "3.0,1.2"
    else:
        header = "programming_time_s,memory_window_V"
        good_row = "0.010,1.2"

    path = _write(
        tmp_path / "bad.csv",
        (
            f"{header}\n"
            f"{row}\n"
            f"{good_row}\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        if loader_kind == "voltage":
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
            )
        else:
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    [
        "voltage",
        "time",
    ],
)
@pytest.mark.parametrize(
    "uncertainty",
    [
        "0.0",
        "-0.1",
    ],
)
def test_memory_window_loaders_require_positive_uncertainty(
    tmp_path,
    metadata,
    loader_kind,
    uncertainty,
):
    if loader_kind == "voltage":
        path = _write(
            tmp_path / "bad_unc.csv",
            (
                "program_voltage_V,memory_window_V,"
                "memory_window_uncertainty_V\n"
                f"2.0,0.5,{uncertainty}\n"
                "3.0,1.2,0.1\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="strictly positive",
        ):
            load_memory_window_vs_program_voltage_csv(
                path,
                metadata=metadata,
                program_pulse_width_s=1.0e-3,
            )
    else:
        path = _write(
            tmp_path / "bad_unc.csv",
            (
                "programming_time_s,memory_window_V,"
                "memory_window_uncertainty_V\n"
                f"0.001,0.5,{uncertainty}\n"
                "0.010,1.2,0.1\n"
            ),
        )

        with pytest.raises(
            ValueError,
            match="strictly positive",
        ):
            load_memory_window_vs_programming_time_csv(
                path,
                metadata=metadata,
                program_voltage_V=4.0,
            )


def test_program_voltage_serialization_is_explicit(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw.csv",
        (
            "program_voltage_V,memory_window_V,"
            "memory_window_uncertainty_V\n"
            "2.0,0.5,0.05\n"
            "3.0,1.2,0.08\n"
        ),
    )

    dataset = load_memory_window_vs_program_voltage_csv(
        path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
        measurement_frequency_Hz=1.0e6,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "device_observable",
        "metadata": metadata.to_dict(),
        "independent_variable": {
            "name": "program_voltage",
            "unit": "V",
            "values": [2.0, 3.0],
        },
        "observable": {
            "name": "memory_window",
            "unit": "V",
            "values": [0.5, 1.2],
            "uncertainty": [0.05, 0.08],
        },
        "conditions": [
            {
                "name": "measurement_frequency",
                "value": 1.0e6,
                "unit": "Hz",
            },
            {
                "name": "program_pulse_width",
                "value": 1.0e-3,
                "unit": "s",
            },
        ],
    }


def test_programming_time_serialization_is_explicit(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "mw.csv",
        (
            "programming_time_s,memory_window_V,"
            "memory_window_uncertainty_V\n"
            "0.001,0.5,0.05\n"
            "0.010,1.2,0.08\n"
        ),
    )

    dataset = load_memory_window_vs_programming_time_csv(
        path,
        metadata=metadata,
        program_voltage_V=4.0,
        measurement_frequency_Hz=1.0e5,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "device_observable",
        "metadata": metadata.to_dict(),
        "independent_variable": {
            "name": "programming_time",
            "unit": "s",
            "values": [0.001, 0.01],
        },
        "observable": {
            "name": "memory_window",
            "unit": "V",
            "values": [0.5, 1.2],
            "uncertainty": [0.05, 0.08],
        },
        "conditions": [
            {
                "name": "measurement_frequency",
                "value": 1.0e5,
                "unit": "Hz",
            },
            {
                "name": "program_voltage",
                "value": 4.0,
                "unit": "V",
            },
        ],
    }


def test_memory_window_loader_hashes_are_deterministic(
    tmp_path,
    metadata,
):
    voltage_path = _write(
        tmp_path / "voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
        ),
    )
    time_path = _write(
        tmp_path / "time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "0.010,1.2\n"
        ),
    )

    voltage_a = load_memory_window_vs_program_voltage_csv(
        voltage_path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )
    voltage_b = load_memory_window_vs_program_voltage_csv(
        voltage_path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )
    time_a = load_memory_window_vs_programming_time_csv(
        time_path,
        metadata=metadata,
        program_voltage_V=4.0,
    )
    time_b = load_memory_window_vs_programming_time_csv(
        time_path,
        metadata=metadata,
        program_voltage_V=4.0,
    )

    assert voltage_a.dataset_hash() == voltage_b.dataset_hash()
    assert time_a.dataset_hash() == time_b.dataset_hash()


def test_fixed_program_condition_changes_hash(
    tmp_path,
    metadata,
):
    voltage_path = _write(
        tmp_path / "voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
        ),
    )
    time_path = _write(
        tmp_path / "time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "0.010,1.2\n"
        ),
    )

    short_pulse = load_memory_window_vs_program_voltage_csv(
        voltage_path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )
    long_pulse = load_memory_window_vs_program_voltage_csv(
        voltage_path,
        metadata=metadata,
        program_pulse_width_s=1.0e-2,
    )
    low_voltage = load_memory_window_vs_programming_time_csv(
        time_path,
        metadata=metadata,
        program_voltage_V=3.0,
    )
    high_voltage = load_memory_window_vs_programming_time_csv(
        time_path,
        metadata=metadata,
        program_voltage_V=4.0,
    )

    assert (
        short_pulse.dataset_hash()
        != long_pulse.dataset_hash()
    )
    assert (
        low_voltage.dataset_hash()
        != high_voltage.dataset_hash()
    )


def test_voltage_and_time_dataset_types_remain_distinct(
    tmp_path,
    metadata,
):
    voltage_path = _write(
        tmp_path / "voltage.csv",
        (
            "program_voltage_V,memory_window_V\n"
            "2.0,0.5\n"
            "3.0,1.2\n"
        ),
    )
    time_path = _write(
        tmp_path / "time.csv",
        (
            "programming_time_s,memory_window_V\n"
            "0.001,0.5\n"
            "0.010,1.2\n"
        ),
    )

    voltage_dataset = load_memory_window_vs_program_voltage_csv(
        voltage_path,
        metadata=metadata,
        program_pulse_width_s=1.0e-3,
    )
    time_dataset = load_memory_window_vs_programming_time_csv(
        time_path,
        metadata=metadata,
        program_voltage_V=4.0,
    )

    assert (
        voltage_dataset.independent_variable_name
        != time_dataset.independent_variable_name
    )
    assert (
        voltage_dataset.dataset_hash()
        != time_dataset.dataset_hash()
    )
