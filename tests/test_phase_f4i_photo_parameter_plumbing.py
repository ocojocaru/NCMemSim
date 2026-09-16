from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from ncmemsim.fitting import FitParameter, FitParameterSet
from ncmemsim.photo import PhotoTransitionConfig
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig


def _base_objects():
    return (
        make_v53_reference_device(grid_points=7),
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=5.0e-3,
            internal_dt_s=1.0e-5,
        ),
    )


def _photo_spec(
    *,
    initial_value: float = 1.0e-7,
    lower_bound: float = 0.0,
    upper_bound: float = 1.0,
) -> DeviceCalibrationSpec:
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="photo_capture_efficiency",
                    initial_value=initial_value,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                    description=(
                        "Effective probability that an absorbed photon "
                        "produces a useful photo-assisted transition."
                    ),
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="photo_capture_efficiency",
                target=DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY,
            ),
        ),
        name="f4i1-photo-capture-efficiency",
    )


def _qfix_spec() -> DeviceCalibrationSpec:
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="qfix_C_m2",
                    initial_value=0.0,
                    lower_bound=-1.0e-2,
                    upper_bound=1.0e-2,
                    unit="C/m^2",
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="qfix_C_m2",
                target=DeviceFitTarget.SIMULATION_QFIX_C_M2,
            ),
        ),
        name="f4i1-backward-compatibility-qfix",
    )


def test_photo_capture_efficiency_target_serializes_canonically():
    binding = _photo_spec().bindings[0]

    assert binding.target == DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY
    assert binding.target_key == "photo.photo_capture_efficiency"
    assert binding.canonical_unit is None

    payload = binding.to_dict()
    assert payload["target"] == "photo.photo_capture_efficiency"
    assert payload["canonical_unit"] is None


def test_photo_target_requires_explicit_base_photo_config():
    device, physics, simulation_config = _base_objects()

    with pytest.raises(
        ValueError,
        match="explicit base_photo_config",
    ):
        apply_device_calibration_parameters(
            device,
            physics,
            simulation_config,
            _photo_spec(),
            np.asarray([2.0e-7]),
        )


def test_base_photo_config_type_is_validated():
    device, physics, simulation_config = _base_objects()

    with pytest.raises(
        TypeError,
        match="PhotoTransitionConfig or None",
    ):
        apply_device_calibration_parameters(
            device,
            physics,
            simulation_config,
            _qfix_spec(),
            np.asarray([1.0e-3]),
            base_photo_config="not-a-photo-config",
        )


def test_photo_parameter_application_is_isolated():
    device, physics, simulation_config = _base_objects()
    baseline_photo = PhotoTransitionConfig(
        photo_capture_efficiency=1.0e-7,
    )

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        _photo_spec(),
        np.asarray([2.5e-7]),
        base_photo_config=baseline_photo,
    )

    assert baseline_photo.photo_capture_efficiency == pytest.approx(1.0e-7)
    assert context.photo_config is not baseline_photo
    assert context.photo_config is not None
    assert context.photo_config.photo_capture_efficiency == pytest.approx(
        2.5e-7
    )
    assert context.parameter_values["photo_capture_efficiency"] == pytest.approx(
        2.5e-7
    )


@pytest.mark.parametrize("value", [-1.0e-6, 1.000001])
def test_photo_target_rejects_values_outside_physical_interval(value):
    device, physics, simulation_config = _base_objects()
    baseline_photo = PhotoTransitionConfig(
        photo_capture_efficiency=1.0e-7,
    )
    spec = _photo_spec(
        initial_value=0.5,
        lower_bound=-2.0,
        upper_bound=2.0,
    )

    with pytest.raises(
        ValueError,
        match=r"must lie in \[0, 1\]",
    ):
        apply_device_calibration_parameters(
            device,
            physics,
            simulation_config,
            spec,
            np.asarray([value]),
            base_photo_config=baseline_photo,
        )


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_photo_target_accepts_closed_interval_endpoints(value):
    device, physics, simulation_config = _base_objects()
    baseline_photo = PhotoTransitionConfig(
        photo_capture_efficiency=1.0e-7,
    )

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        _photo_spec(),
        np.asarray([value]),
        base_photo_config=baseline_photo,
    )

    assert context.photo_config is not None
    assert context.photo_config.photo_capture_efficiency == pytest.approx(value)


def test_nonphoto_application_remains_backward_compatible():
    device, physics, simulation_config = _base_objects()

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        _qfix_spec(),
        np.asarray([1.0e-3]),
    )

    assert context.photo_config is None
    assert context.simulation_config.qfix_C_m2 == pytest.approx(1.0e-3)


def test_nonphoto_fit_can_carry_explicit_photo_baseline():
    device, physics, simulation_config = _base_objects()
    baseline_photo = PhotoTransitionConfig(
        photo_capture_efficiency=3.0e-7,
    )

    context = apply_device_calibration_parameters(
        device,
        physics,
        simulation_config,
        _qfix_spec(),
        np.asarray([1.0e-3]),
        base_photo_config=baseline_photo,
    )

    assert context.photo_config is not None
    assert context.photo_config is not baseline_photo
    assert context.photo_config.photo_capture_efficiency == pytest.approx(
        3.0e-7
    )
