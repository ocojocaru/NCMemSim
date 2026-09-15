from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)


@pytest.fixture
def metadata() -> ExperimentalDatasetMetadata:
    return ExperimentalDatasetMetadata(
        dataset_id="device-observable-test",
        source="Synthetic unit-test dataset",
        sample_id="sample-1",
        temperature_K=300.0,
    )


def test_condition_numeric_value_is_normalized_to_float():
    condition = ExperimentalCondition(
        name="frequency",
        value=1000,
        unit="Hz",
    )

    assert condition.name == "frequency"
    assert condition.value == pytest.approx(1000.0)
    assert isinstance(condition.value, float)
    assert condition.unit == "Hz"


def test_condition_bool_value_is_preserved():
    condition = ExperimentalCondition(
        name="illuminated",
        value=False,
    )

    assert condition.value is False
    assert isinstance(condition.value, bool)


def test_condition_string_value_is_stripped():
    condition = ExperimentalCondition(
        name="sweep_direction",
        value=" forward ",
    )

    assert condition.value == "forward"


@pytest.mark.parametrize(
    ("name", "value", "unit"),
    [
        ("", 1.0, "V"),
        ("   ", 1.0, "V"),
        ("bias", "", "V"),
        ("bias", "   ", "V"),
        ("bias", 1.0, ""),
        ("bias", 1.0, "   "),
    ],
)
def test_condition_rejects_empty_text(
    name,
    value,
    unit,
):
    with pytest.raises(ValueError):
        ExperimentalCondition(
            name=name,
            value=value,
            unit=unit,
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_condition_rejects_nonfinite_numeric_value(
    value,
):
    with pytest.raises(ValueError):
        ExperimentalCondition(
            name="bias",
            value=value,
            unit="V",
        )


def test_condition_rejects_unsupported_value_type():
    with pytest.raises(TypeError):
        ExperimentalCondition(
            name="bad",
            value=[1.0],
        )


def test_device_observable_dataset_constructs_cv_curve(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[-1.0, 0.0, 1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.01, 0.02, 0.03],
        metadata=metadata,
        conditions=(
            ExperimentalCondition(
                name="frequency",
                value=1000.0,
                unit="Hz",
            ),
            ExperimentalCondition(
                name="sweep_direction",
                value="forward",
            ),
        ),
    )

    assert dataset.n_points == 3
    assert dataset.has_uncertainty is False
    assert dataset.condition_dict == {
        "frequency": 1000.0,
        "sweep_direction": "forward",
    }


def test_device_observable_dataset_constructs_retention_curve(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=[1.0, 10.0, 100.0],
        observable_name="retained_charge",
        observable_unit="C/m^2",
        observed_values=[1.0e-3, 9.5e-4, 9.0e-4],
        metadata=metadata,
        conditions=(
            ExperimentalCondition(
                name="retention_bias",
                value=0.0,
                unit="V",
            ),
        ),
    )

    assert dataset.n_points == 3
    assert dataset.observable_name == "retained_charge"


def test_measurement_order_is_preserved(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[1.0, 0.0, -1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.03, 0.02, 0.01],
        metadata=metadata,
    )

    assert np.array_equal(
        dataset.independent_values,
        np.array([1.0, 0.0, -1.0]),
    )
    assert np.array_equal(
        dataset.observed_values,
        np.array([0.03, 0.02, 0.01]),
    )


def test_device_observable_dataset_copies_input_arrays(
    metadata,
):
    x = np.array([0.0, 1.0, 2.0])
    y = np.array([10.0, 11.0, 12.0])

    dataset = DeviceObservableDataset(
        independent_variable_name="x",
        independent_variable_unit=None,
        independent_values=x,
        observable_name="y",
        observable_unit=None,
        observed_values=y,
        metadata=metadata,
    )

    x[0] = 99.0
    y[0] = 99.0

    assert dataset.independent_values[0] == pytest.approx(0.0)
    assert dataset.observed_values[0] == pytest.approx(10.0)


def test_device_observable_arrays_are_read_only(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="x",
        independent_variable_unit=None,
        independent_values=[0.0, 1.0],
        observable_name="y",
        observable_unit=None,
        observed_values=[2.0, 3.0],
        metadata=metadata,
        observed_uncertainty=[0.1, 0.2],
    )

    assert dataset.independent_values.flags.writeable is False
    assert dataset.observed_values.flags.writeable is False
    assert dataset.observed_uncertainty is not None
    assert dataset.observed_uncertainty.flags.writeable is False


def test_device_observable_dataset_accepts_positive_uncertainty(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[0.0, 1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.01, 0.02],
        observed_uncertainty=[0.001, 0.001],
        metadata=metadata,
    )

    assert dataset.has_uncertainty is True
    assert np.allclose(
        dataset.observed_uncertainty,
        [0.001, 0.001],
    )


def test_device_observable_dataset_requires_metadata():
    with pytest.raises(TypeError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            metadata="bad",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "independent_variable_name",
        "observable_name",
    ],
)
def test_device_observable_dataset_rejects_empty_required_names(
    metadata,
    field_name,
):
    kwargs = {
        "independent_variable_name": "x",
        "independent_variable_unit": None,
        "independent_values": [0.0, 1.0],
        "observable_name": "y",
        "observable_unit": None,
        "observed_values": [2.0, 3.0],
        "metadata": metadata,
    }
    kwargs[field_name] = "   "

    with pytest.raises(ValueError):
        DeviceObservableDataset(**kwargs)


@pytest.mark.parametrize(
    "field_name",
    [
        "independent_variable_unit",
        "observable_unit",
    ],
)
def test_device_observable_dataset_rejects_empty_units(
    metadata,
    field_name,
):
    kwargs = {
        "independent_variable_name": "x",
        "independent_variable_unit": None,
        "independent_values": [0.0, 1.0],
        "observable_name": "y",
        "observable_unit": None,
        "observed_values": [2.0, 3.0],
        "metadata": metadata,
    }
    kwargs[field_name] = "   "

    with pytest.raises(ValueError):
        DeviceObservableDataset(**kwargs)


def test_device_observable_dataset_requires_two_points(
    metadata,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0],
            metadata=metadata,
        )


def test_device_observable_dataset_rejects_shape_mismatch(
    metadata,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0, 2.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            metadata=metadata,
        )


def test_device_observable_dataset_rejects_nonfinite_data(
    metadata,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, float("nan")],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            metadata=metadata,
        )

    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, float("inf")],
            metadata=metadata,
        )


def test_device_observable_dataset_rejects_uncertainty_shape_mismatch(
    metadata,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            observed_uncertainty=[0.1],
            metadata=metadata,
        )


@pytest.mark.parametrize(
    "uncertainty",
    [
        [0.0, 0.1],
        [-0.1, 0.1],
    ],
)
def test_device_observable_dataset_requires_positive_uncertainty(
    metadata,
    uncertainty,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            observed_uncertainty=uncertainty,
            metadata=metadata,
        )


def test_device_observable_dataset_rejects_duplicate_condition_names(
    metadata,
):
    with pytest.raises(ValueError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            metadata=metadata,
            conditions=(
                ExperimentalCondition(
                    name="bias",
                    value=0.0,
                    unit="V",
                ),
                ExperimentalCondition(
                    name="bias",
                    value=1.0,
                    unit="V",
                ),
            ),
        )


def test_device_observable_dataset_rejects_noncondition_objects(
    metadata,
):
    with pytest.raises(TypeError):
        DeviceObservableDataset(
            independent_variable_name="x",
            independent_variable_unit=None,
            independent_values=[0.0, 1.0],
            observable_name="y",
            observable_unit=None,
            observed_values=[2.0, 3.0],
            metadata=metadata,
            conditions=("bad",),
        )


def test_condition_order_is_canonicalized_for_hashing(
    metadata,
):
    conditions_a = (
        ExperimentalCondition(
            name="frequency",
            value=1000.0,
            unit="Hz",
        ),
        ExperimentalCondition(
            name="sweep_direction",
            value="forward",
        ),
    )
    conditions_b = tuple(
        reversed(conditions_a)
    )

    dataset_a = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[-1.0, 0.0, 1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.01, 0.02, 0.03],
        metadata=metadata,
        conditions=conditions_a,
    )
    dataset_b = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[-1.0, 0.0, 1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.01, 0.02, 0.03],
        metadata=metadata,
        conditions=conditions_b,
    )

    assert dataset_a.conditions == dataset_b.conditions
    assert dataset_a.dataset_hash() == dataset_b.dataset_hash()


def test_measurement_order_changes_dataset_hash(
    metadata,
):
    forward = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[-1.0, 0.0, 1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.01, 0.02, 0.03],
        metadata=metadata,
    )
    backward = DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=[1.0, 0.0, -1.0],
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=[0.03, 0.02, 0.01],
        metadata=metadata,
    )

    assert forward.dataset_hash() != backward.dataset_hash()


def test_to_dict_has_explicit_schema(
    metadata,
):
    dataset = DeviceObservableDataset(
        independent_variable_name="program_voltage",
        independent_variable_unit="V",
        independent_values=[2.0, 3.0],
        observable_name="memory_window",
        observable_unit="V",
        observed_values=[1.0, 2.0],
        observed_uncertainty=[0.1, 0.2],
        metadata=metadata,
        conditions=(
            ExperimentalCondition(
                name="pulse_width",
                value=1.0e-3,
                unit="s",
            ),
        ),
    )

    serialized = dataset.to_dict()

    assert serialized["schema_version"] == 1
    assert serialized["dataset_type"] == "device_observable"
    assert serialized["metadata"] == metadata.to_dict()
    assert serialized["independent_variable"] == {
        "name": "program_voltage",
        "unit": "V",
        "values": [2.0, 3.0],
    }
    assert serialized["observable"] == {
        "name": "memory_window",
        "unit": "V",
        "values": [1.0, 2.0],
        "uncertainty": [0.1, 0.2],
    }
    assert serialized["conditions"] == [
        {
            "name": "pulse_width",
            "value": 0.001,
            "unit": "s",
        }
    ]


def test_dataset_hash_is_deterministic(
    metadata,
):
    kwargs = {
        "independent_variable_name": "x",
        "independent_variable_unit": None,
        "independent_values": [0.0, 1.0],
        "observable_name": "y",
        "observable_unit": None,
        "observed_values": [2.0, 3.0],
        "metadata": metadata,
    }

    first = DeviceObservableDataset(**kwargs)
    second = DeviceObservableDataset(**kwargs)

    assert first.dataset_hash() == second.dataset_hash()
    assert len(first.dataset_hash()) == 64


def test_existing_optical_dataset_schema_is_unchanged(
    metadata,
):
    dataset = OpticalAbsorptionDataset(
        wavelength_nm=[1500.0, 1600.0],
        absorption_coefficient_m_inv=[
            1.0e5,
            2.0e5,
        ],
        absorption_uncertainty_m_inv=[
            1.0e4,
            2.0e4,
        ],
        sn_fraction=0.03,
        metadata=metadata,
    )

    assert dataset.to_dict() == {
        "schema_version": 1,
        "dataset_type": "optical_absorption",
        "metadata": metadata.to_dict(),
        "sn_fraction": 0.03,
        "wavelength_nm": [1500.0, 1600.0],
        "absorption_coefficient_m_inv": [
            100000.0,
            200000.0,
        ],
        "absorption_uncertainty_m_inv": [
            10000.0,
            20000.0,
        ],
    }
