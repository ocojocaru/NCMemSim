from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalDatasetMetadata,
)
from ncmemsim.io import load_cv_csv


@pytest.fixture
def metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="cv-test",
        source="Synthetic C-V test data",
        sample_id="sample-cv",
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


def test_load_cv_csv_without_uncertainty(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "-1.0,0.010\n"
            "0.0,0.020\n"
            "1.0,0.030\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
    )

    assert isinstance(
        dataset,
        DeviceObservableDataset,
    )
    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert (
        dataset.independent_variable_name
        == "gate_voltage"
    )
    assert dataset.independent_variable_unit == "V"
    assert dataset.observable_name == "capacitance"
    assert dataset.observable_unit == "F/m^2"
    assert np.allclose(
        dataset.independent_values,
        [-1.0, 0.0, 1.0],
    )
    assert np.allclose(
        dataset.observed_values,
        [0.010, 0.020, 0.030],
    )
    assert dataset.condition_dict == {
        "sweep_direction": "forward",
    }


def test_load_cv_csv_with_uncertainty_and_frequency(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "cv_uncertainty.csv",
        (
            "gate_voltage_V,capacitance_F_m2,"
            "capacitance_uncertainty_F_m2\n"
            "-1.0,0.010,0.001\n"
            "0.0,0.020,0.001\n"
            "1.0,0.030,0.002\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="backward",
        measurement_frequency_Hz=1000.0,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.001, 0.001, 0.002],
    )
    assert dataset.condition_dict == {
        "measurement_frequency": 1000.0,
        "sweep_direction": "backward",
    }

    assert [
        condition.name
        for condition in dataset.conditions
    ] == [
        "measurement_frequency",
        "sweep_direction",
    ]


def test_load_cv_csv_preserves_backward_row_order(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "backward.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "1.0,0.030\n"
            "0.0,0.020\n"
            "-1.0,0.010\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="backward",
    )

    assert np.array_equal(
        dataset.independent_values,
        np.array([1.0, 0.0, -1.0]),
    )
    assert np.array_equal(
        dataset.observed_values,
        np.array([0.030, 0.020, 0.010]),
    )


def test_forward_and_backward_files_produce_distinct_hashes(
    tmp_path,
    metadata,
):
    forward_path = _write(
        tmp_path / "forward.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "-1.0,0.010\n"
            "0.0,0.020\n"
            "1.0,0.030\n"
        ),
    )
    backward_path = _write(
        tmp_path / "backward.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "1.0,0.030\n"
            "0.0,0.020\n"
            "-1.0,0.010\n"
        ),
    )

    forward = load_cv_csv(
        forward_path,
        metadata=metadata,
        sweep_direction="forward",
    )
    backward = load_cv_csv(
        backward_path,
        metadata=metadata,
        sweep_direction="backward",
    )

    assert (
        forward.dataset_hash()
        != backward.dataset_hash()
    )


def test_same_data_with_different_frequency_changes_hash(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "-1.0,0.010\n"
            "1.0,0.030\n"
        ),
    )

    low = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
        measurement_frequency_Hz=1.0e3,
    )
    high = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
        measurement_frequency_Hz=1.0e6,
    )

    assert low.dataset_hash() != high.dataset_hash()


@pytest.mark.parametrize(
    "direction",
    [
        "FORWARD",
        " Forward ",
        "backward",
        " BACKWARD ",
    ],
)
def test_sweep_direction_is_normalized(
    tmp_path,
    metadata,
    direction,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction=direction,
    )

    expected = direction.strip().lower()
    assert (
        dataset.condition_dict[
            "sweep_direction"
        ]
        == expected
    )


@pytest.mark.parametrize(
    "direction",
    [
        "",
        " ",
        "up",
        "down",
        "forward_backward",
    ],
)
def test_load_cv_csv_rejects_invalid_sweep_direction(
    tmp_path,
    metadata,
    direction,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="sweep_direction",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction=direction,
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
def test_load_cv_csv_rejects_invalid_frequency(
    tmp_path,
    metadata,
    frequency,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="measurement_frequency_Hz",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
            measurement_frequency_Hz=frequency,
        )


def test_load_cv_csv_requires_metadata(
    tmp_path,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(TypeError):
        load_cv_csv(
            path,
            metadata="bad",
            sweep_direction="forward",
        )


def test_load_cv_csv_accepts_utf8_bom(
    tmp_path,
    metadata,
):
    path = tmp_path / "bom.csv"
    path.write_text(
        (
            "\ufeffgate_voltage_V,"
            "capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
        encoding="utf-8",
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
    )

    assert dataset.n_points == 2


def test_load_cv_csv_ignores_completely_blank_rows(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "blank_rows.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "\n"
            "   ,   \n"
            "1.0,0.020\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
    )

    assert dataset.n_points == 2


@pytest.mark.parametrize(
    "header",
    [
        "voltage_V,capacitance_F_m2",
        "gate_voltage_V,capacitance",
        (
            "gate_voltage_V,capacitance_F_m2,"
            "uncertainty"
        ),
        (
            "capacitance_F_m2,gate_voltage_V"
        ),
        (
            "gate_voltage_V,capacitance_F_m2,"
            "extra"
        ),
    ],
)
def test_load_cv_csv_rejects_unsupported_header(
    tmp_path,
    metadata,
    header,
):
    path = _write(
        tmp_path / "bad_header.csv",
        (
            f"{header}\n"
            "0.0,0.010\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported C-V CSV header",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


def test_load_cv_csv_rejects_empty_file(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "empty.csv",
        "",
    )

    with pytest.raises(
        ValueError,
        match="C-V CSV file is empty",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


def test_load_cv_csv_requires_two_data_rows(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "one_row.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="at least two data rows",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


def test_load_cv_csv_rejects_wrong_field_count(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "wrong_count.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "0.0,0.010\n"
            "1.0,0.020,extra\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="has 3 fields; expected 2",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


@pytest.mark.parametrize(
    ("row", "field_name"),
    [
        (",0.010", "gate_voltage_V"),
        ("bad,0.010", "gate_voltage_V"),
        ("0.0,", "capacitance_F_m2"),
        ("0.0,bad", "capacitance_F_m2"),
    ],
)
def test_load_cv_csv_rejects_missing_or_invalid_required_values(
    tmp_path,
    metadata,
    row,
    field_name,
):
    path = _write(
        tmp_path / "bad_value.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            f"{row}\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


@pytest.mark.parametrize(
    "uncertainty",
    [
        "0.0",
        "-0.001",
    ],
)
def test_load_cv_csv_rejects_nonpositive_uncertainty(
    tmp_path,
    metadata,
    uncertainty,
):
    path = _write(
        tmp_path / "bad_uncertainty.csv",
        (
            "gate_voltage_V,capacitance_F_m2,"
            "capacitance_uncertainty_F_m2\n"
            f"0.0,0.010,{uncertainty}\n"
            "1.0,0.020,0.001\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


def test_load_cv_csv_rejects_nonfinite_values(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "nan.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "nan,0.010\n"
            "1.0,0.020\n"
        ),
    )

    with pytest.raises(
        ValueError,
        match="finite",
    ):
        load_cv_csv(
            path,
            metadata=metadata,
            sweep_direction="forward",
        )


def test_serialized_cv_schema_is_explicit(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2,"
            "capacitance_uncertainty_F_m2\n"
            "-1.0,0.010,0.001\n"
            "1.0,0.030,0.002\n"
        ),
    )

    dataset = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
        measurement_frequency_Hz=1000.0,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "device_observable",
        "metadata": metadata.to_dict(),
        "independent_variable": {
            "name": "gate_voltage",
            "unit": "V",
            "values": [-1.0, 1.0],
        },
        "observable": {
            "name": "capacitance",
            "unit": "F/m^2",
            "values": [0.01, 0.03],
            "uncertainty": [0.001, 0.002],
        },
        "conditions": [
            {
                "name": "measurement_frequency",
                "value": 1000.0,
                "unit": "Hz",
            },
            {
                "name": "sweep_direction",
                "value": "forward",
                "unit": None,
            },
        ],
    }


def test_loader_is_deterministic(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "cv.csv",
        (
            "gate_voltage_V,capacitance_F_m2\n"
            "-1.0,0.010\n"
            "1.0,0.030\n"
        ),
    )

    first = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
        measurement_frequency_Hz=1000.0,
    )
    second = load_cv_csv(
        path,
        metadata=metadata,
        sweep_direction="forward",
        measurement_frequency_Hz=1000.0,
    )

    assert first.to_dict() == second.to_dict()
    assert (
        first.dataset_hash()
        == second.dataset_hash()
    )
