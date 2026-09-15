from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalDatasetMetadata,
)
from ncmemsim.io import (
    load_retention_charge_fraction_csv,
    load_retention_delta_vfb_csv,
)


@pytest.fixture
def metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="retention-test",
        source="Synthetic retention test data",
        sample_id="sample-retention",
        temperature_K=300.0,
    )


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_load_retention_delta_vfb_without_uncertainty(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "delta_vfb.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "10.0,1.9\n"
            "100.0,1.8\n"
        ),
    )

    dataset = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert isinstance(dataset, DeviceObservableDataset)
    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert dataset.independent_variable_name == "time"
    assert dataset.independent_variable_unit == "s"
    assert dataset.observable_name == "delta_vfb"
    assert dataset.observable_unit == "V"
    assert np.allclose(dataset.independent_values, [0.0, 10.0, 100.0])
    assert np.allclose(dataset.observed_values, [2.0, 1.9, 1.8])
    assert dataset.condition_dict == {
        "retention_gate_voltage": 0.0,
    }


def test_load_retention_delta_vfb_with_uncertainty_and_frequency(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "delta_vfb_unc.csv",
        (
            "time_s,delta_vfb_V,delta_vfb_uncertainty_V\n"
            "1.0,2.0,0.05\n"
            "10.0,1.9,0.05\n"
            "100.0,1.8,0.08\n"
        ),
    )

    dataset = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=-1.0,
        measurement_frequency_Hz=1.0e6,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.05, 0.05, 0.08],
    )
    assert dataset.condition_dict == {
        "measurement_frequency": 1.0e6,
        "retention_gate_voltage": -1.0,
    }


def test_load_retention_charge_fraction_without_uncertainty(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "fraction.csv",
        (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "10.0,0.95\n"
            "100.0,0.90\n"
        ),
    )

    dataset = load_retention_charge_fraction_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert dataset.independent_variable_name == "time"
    assert dataset.independent_variable_unit == "s"
    assert (
        dataset.observable_name
        == "total_charge_retention_fraction"
    )
    assert dataset.observable_unit is None
    assert np.allclose(dataset.observed_values, [1.0, 0.95, 0.90])


def test_load_retention_charge_fraction_with_uncertainty_and_frequency(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "fraction_unc.csv",
        (
            "time_s,total_charge_retention_fraction,"
            "total_charge_retention_fraction_uncertainty\n"
            "1.0,1.01,0.02\n"
            "10.0,0.96,0.02\n"
            "100.0,0.91,0.03\n"
        ),
    )

    dataset = load_retention_charge_fraction_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.5,
        measurement_frequency_Hz=1.0e5,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.02, 0.02, 0.03],
    )
    assert dataset.condition_dict == {
        "measurement_frequency": 1.0e5,
        "retention_gate_voltage": 0.5,
    }


def test_time_zero_is_allowed(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "zero.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "1.0,1.9\n"
        ),
    )

    dataset = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert dataset.independent_values[0] == pytest.approx(0.0)


def test_first_retention_time_need_not_be_zero(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "positive_start.csv",
        (
            "time_s,total_charge_retention_fraction\n"
            "1.0,0.99\n"
            "10.0,0.95\n"
        ),
    )

    dataset = load_retention_charge_fraction_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert dataset.independent_values[0] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "times",
    [
        ("-1.0", "1.0"),
        ("1.0", "1.0"),
        ("10.0", "1.0"),
    ],
)
@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_reject_invalid_time_sequences(
    tmp_path,
    metadata,
    times,
    loader_kind,
):
    first, second = times

    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V\n"
            f"{first},2.0\n"
            f"{second},1.9\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction\n"
            f"{first},1.0\n"
            f"{second},0.9\n"
        )

    path = _write(tmp_path / "bad_time.csv", text)

    with pytest.raises(ValueError):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_reject_nonfinite_time(
    tmp_path,
    metadata,
    loader_kind,
):
    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V\n"
            "nan,2.0\n"
            "1.0,1.9\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction\n"
            "nan,1.0\n"
            "1.0,0.9\n"
        )

    path = _write(tmp_path / "nan_time.csv", text)

    with pytest.raises(ValueError, match="finite"):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


@pytest.mark.parametrize(
    "gate_voltage",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_reject_nonfinite_gate_voltage(
    tmp_path,
    metadata,
    gate_voltage,
    loader_kind,
):
    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "1.0,1.9\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "1.0,0.9\n"
        )

    path = _write(tmp_path / "data.csv", text)

    with pytest.raises(
        ValueError,
        match="retention_gate_voltage_V",
    ):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=gate_voltage,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=gate_voltage,
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
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_reject_invalid_frequency(
    tmp_path,
    metadata,
    frequency,
    loader_kind,
):
    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "1.0,1.9\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "1.0,0.9\n"
        )

    path = _write(tmp_path / "data.csv", text)

    with pytest.raises(
        ValueError,
        match="measurement_frequency_Hz",
    ):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
                measurement_frequency_Hz=frequency,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
                measurement_frequency_Hz=frequency,
            )


def test_retention_loaders_require_metadata(
    tmp_path,
):
    delta_path = _write(
        tmp_path / "delta.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "1.0,1.9\n"
        ),
    )
    fraction_path = _write(
        tmp_path / "fraction.csv",
        (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "1.0,0.9\n"
        ),
    )

    with pytest.raises(TypeError):
        load_retention_delta_vfb_csv(
            delta_path,
            metadata="bad",
            retention_gate_voltage_V=0.0,
        )

    with pytest.raises(TypeError):
        load_retention_charge_fraction_csv(
            fraction_path,
            metadata="bad",
            retention_gate_voltage_V=0.0,
        )


@pytest.mark.parametrize(
    ("loader_kind", "header"),
    [
        ("delta_vfb", "time,delta_vfb_V"),
        ("delta_vfb", "time_s,delta_vfb"),
        (
            "delta_vfb",
            "time_s,delta_vfb_V,uncertainty",
        ),
        (
            "charge_fraction",
            "time,total_charge_retention_fraction",
        ),
        (
            "charge_fraction",
            "time_s,charge_retention_fraction",
        ),
        (
            "charge_fraction",
            "time_s,total_charge_retention_fraction,uncertainty",
        ),
    ],
)
def test_retention_loaders_reject_unsupported_headers(
    tmp_path,
    metadata,
    loader_kind,
    header,
):
    path = _write(
        tmp_path / "bad_header.csv",
        (
            f"{header}\n"
            "0.0,1.0\n"
            "1.0,0.9\n"
        ),
    )

    with pytest.raises(ValueError, match="Unsupported"):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_reject_empty_files(
    tmp_path,
    metadata,
    loader_kind,
):
    path = _write(tmp_path / "empty.csv", "")

    with pytest.raises(ValueError, match="CSV file is empty"):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_require_two_rows(
    tmp_path,
    metadata,
    loader_kind,
):
    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
        )

    path = _write(tmp_path / "one.csv", text)

    with pytest.raises(
        ValueError,
        match="at least two data rows",
    ):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
def test_retention_loaders_accept_bom_and_blank_rows(
    tmp_path,
    metadata,
    loader_kind,
):
    path = tmp_path / "bom.csv"

    if loader_kind == "delta_vfb":
        text = (
            "\ufefftime_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "\n"
            "   ,   \n"
            "1.0,1.9\n"
        )
    else:
        text = (
            "\ufefftime_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "\n"
            "   ,   \n"
            "1.0,0.9\n"
        )

    path.write_text(text, encoding="utf-8")

    if loader_kind == "delta_vfb":
        dataset = load_retention_delta_vfb_csv(
            path,
            metadata=metadata,
            retention_gate_voltage_V=0.0,
        )
    else:
        dataset = load_retention_charge_fraction_csv(
            path,
            metadata=metadata,
            retention_gate_voltage_V=0.0,
        )

    assert dataset.n_points == 2


@pytest.mark.parametrize(
    "loader_kind",
    ["delta_vfb", "charge_fraction"],
)
@pytest.mark.parametrize(
    "uncertainty",
    ["0.0", "-0.1"],
)
def test_retention_loaders_require_positive_uncertainty(
    tmp_path,
    metadata,
    loader_kind,
    uncertainty,
):
    if loader_kind == "delta_vfb":
        text = (
            "time_s,delta_vfb_V,delta_vfb_uncertainty_V\n"
            f"0.0,2.0,{uncertainty}\n"
            "1.0,1.9,0.1\n"
        )
    else:
        text = (
            "time_s,total_charge_retention_fraction,"
            "total_charge_retention_fraction_uncertainty\n"
            f"0.0,1.0,{uncertainty}\n"
            "1.0,0.9,0.1\n"
        )

    path = _write(tmp_path / "bad_unc.csv", text)

    with pytest.raises(ValueError, match="strictly positive"):
        if loader_kind == "delta_vfb":
            load_retention_delta_vfb_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )
        else:
            load_retention_charge_fraction_csv(
                path,
                metadata=metadata,
                retention_gate_voltage_V=0.0,
            )


def test_charge_fraction_is_not_clipped_to_unit_interval(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "above_one.csv",
        (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.02\n"
            "1.0,1.01\n"
        ),
    )

    dataset = load_retention_charge_fraction_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert np.allclose(
        dataset.observed_values,
        [1.02, 1.01],
    )


def test_delta_vfb_serialization_is_explicit(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "delta.csv",
        (
            "time_s,delta_vfb_V,delta_vfb_uncertainty_V\n"
            "0.0,2.0,0.05\n"
            "10.0,1.9,0.06\n"
        ),
    )

    dataset = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=-0.5,
        measurement_frequency_Hz=1.0e6,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "device_observable",
        "metadata": metadata.to_dict(),
        "independent_variable": {
            "name": "time",
            "unit": "s",
            "values": [0.0, 10.0],
        },
        "observable": {
            "name": "delta_vfb",
            "unit": "V",
            "values": [2.0, 1.9],
            "uncertainty": [0.05, 0.06],
        },
        "conditions": [
            {
                "name": "measurement_frequency",
                "value": 1.0e6,
                "unit": "Hz",
            },
            {
                "name": "retention_gate_voltage",
                "value": -0.5,
                "unit": "V",
            },
        ],
    }


def test_charge_fraction_serialization_is_explicit(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "fraction.csv",
        (
            "time_s,total_charge_retention_fraction,"
            "total_charge_retention_fraction_uncertainty\n"
            "0.0,1.0,0.01\n"
            "10.0,0.95,0.02\n"
        ),
    )

    dataset = load_retention_charge_fraction_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
        measurement_frequency_Hz=1.0e5,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "device_observable",
        "metadata": metadata.to_dict(),
        "independent_variable": {
            "name": "time",
            "unit": "s",
            "values": [0.0, 10.0],
        },
        "observable": {
            "name": "total_charge_retention_fraction",
            "unit": None,
            "values": [1.0, 0.95],
            "uncertainty": [0.01, 0.02],
        },
        "conditions": [
            {
                "name": "measurement_frequency",
                "value": 1.0e5,
                "unit": "Hz",
            },
            {
                "name": "retention_gate_voltage",
                "value": 0.0,
                "unit": "V",
            },
        ],
    }


def test_retention_hash_is_deterministic(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "delta.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "10.0,1.9\n"
        ),
    )

    first = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )
    second = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert first.dataset_hash() == second.dataset_hash()


def test_retention_gate_voltage_changes_hash(
    tmp_path,
    metadata,
):
    path = _write(
        tmp_path / "delta.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,2.0\n"
            "10.0,1.9\n"
        ),
    )

    zero_bias = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )
    one_volt = load_retention_delta_vfb_csv(
        path,
        metadata=metadata,
        retention_gate_voltage_V=1.0,
    )

    assert zero_bias.dataset_hash() != one_volt.dataset_hash()


def test_retention_observables_have_distinct_hashes(
    tmp_path,
    metadata,
):
    delta_path = _write(
        tmp_path / "delta.csv",
        (
            "time_s,delta_vfb_V\n"
            "0.0,1.0\n"
            "10.0,0.9\n"
        ),
    )
    fraction_path = _write(
        tmp_path / "fraction.csv",
        (
            "time_s,total_charge_retention_fraction\n"
            "0.0,1.0\n"
            "10.0,0.9\n"
        ),
    )

    delta_dataset = load_retention_delta_vfb_csv(
        delta_path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )
    fraction_dataset = load_retention_charge_fraction_csv(
        fraction_path,
        metadata=metadata,
        retention_gate_voltage_V=0.0,
    )

    assert (
        delta_dataset.observable_name
        != fraction_dataset.observable_name
    )
    assert (
        delta_dataset.dataset_hash()
        != fraction_dataset.dataset_hash()
    )
