from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

pytest.importorskip("scipy")

from ncmemsim.device_calibration import (
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
)
from ncmemsim.device_fit import (
    CVCalibrationProtocol,
    DeviceCVFitResult,
    fit_single_parameter_cv_dataset,
)
from ncmemsim.experimental import (
    DeviceObservableDataset,
    ExperimentalCondition,
    ExperimentalDatasetMetadata,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
    LeastSquaresConfig,
)
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig, Simulator


TRUE_QFIX_C_M2 = 1.2e-3


def _protocol():
    return CVCalibrationProtocol(vmin_V=-2.0, vmax_V=2.0, points=31)


def _base_objects():
    return (
        make_v53_reference_device(grid_points=7),
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=0.0,
            internal_dt_s=1.0e-5,
            qfix_C_m2=0.0,
            qit_C_m2=0.0,
        ),
    )


def _synthetic_dataset(direction="forward", uncertainty=None):
    device, physics, config = _base_objects()
    protocol = _protocol()
    truth = replace(config, qfix_C_m2=TRUE_QFIX_C_M2)

    cv = Simulator(device, physics, truth).simulate_cv(
        vmin_V=protocol.vmin_V,
        vmax_V=protocol.vmax_V,
        points=protocol.points,
    )
    sweep = cv.forward if direction == "forward" else cv.backward

    sigma = None
    if uncertainty is not None:
        sigma = np.full(sweep.voltages_V.size, uncertainty, dtype=float)

    return DeviceObservableDataset(
        independent_variable_name="gate_voltage",
        independent_variable_unit="V",
        independent_values=np.asarray(sweep.voltages_V, dtype=float),
        observable_name="capacitance",
        observable_unit="F/m^2",
        observed_values=np.asarray(sweep.capacitance_F_m2, dtype=float),
        observed_uncertainty=sigma,
        metadata=ExperimentalDatasetMetadata(
            dataset_id=f"synthetic-cv-qfix-{direction}",
            source="NCMemSim synthetic F4h2a recovery data",
            sample_id="synthetic-v53",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="sweep_direction",
                value=direction,
            ),
        ),
    )


def _qfix_spec():
    parameter = FitParameter(
        name="qfix_C_m2",
        initial_value=0.0,
        lower_bound=-3.0e-3,
        upper_bound=3.0e-3,
        unit="C/m^2",
        description="Synthetic C-V fixed-charge recovery parameter.",
    )
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet((parameter,)),
        bindings=(
            DeviceFitParameterBinding(
                parameter_name="qfix_C_m2",
                target=DeviceFitTarget.SIMULATION_QFIX_C_M2,
            ),
        ),
        name="synthetic-cv-qfix-recovery",
    )


def _strict_solver_config():
    return LeastSquaresConfig(
        ftol=1.0e-12,
        xtol=1.0e-12,
        gtol=1.0e-12,
        max_nfev=1000,
    )


@pytest.mark.parametrize(
    ("vmin", "vmax"),
    [(0.0, 0.0), (1.0, -1.0)],
)
def test_protocol_requires_ordered_bounds(vmin, vmax):
    with pytest.raises(ValueError):
        CVCalibrationProtocol(vmin_V=vmin, vmax_V=vmax, points=11)


@pytest.mark.parametrize("points", [0, 1, 2])
def test_protocol_requires_at_least_three_points(points):
    with pytest.raises(ValueError):
        CVCalibrationProtocol(points=points)


def test_protocol_hash_is_deterministic():
    assert _protocol().protocol_hash() == _protocol().protocol_hash()


@pytest.mark.parametrize("direction", ["forward", "backward"])
def test_fit_recovers_known_qfix(direction):
    device, physics, config = _base_objects()
    result = fit_single_parameter_cv_dataset(
        _synthetic_dataset(direction=direction),
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_qfix_spec(),
        protocol=_protocol(),
        least_squares_config=_strict_solver_config(),
    )

    assert isinstance(result, DeviceCVFitResult)
    assert result.numerical_result.success
    assert result.fitted_parameter_values["qfix_C_m2"] == pytest.approx(
        TRUE_QFIX_C_M2,
        abs=2.0e-7,
    )
    assert (
        result.objective.objective.root_mean_square_error
        < 1.0e-7
    )


def test_fit_uses_uncertainty_weighting():
    device, physics, config = _base_objects()
    result = fit_single_parameter_cv_dataset(
        _synthetic_dataset(uncertainty=1.0e-5),
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_qfix_spec(),
        protocol=_protocol(),
    )
    assert result.objective.objective.weighted


def test_fit_does_not_mutate_baseline_config():
    device, physics, config = _base_objects()
    original = config.qfix_C_m2

    result = fit_single_parameter_cv_dataset(
        _synthetic_dataset(),
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_qfix_spec(),
        protocol=_protocol(),
    )

    assert config.qfix_C_m2 == pytest.approx(original)
    assert result.fitted_context.simulation_config.qfix_C_m2 != pytest.approx(
        original
    )


def test_fit_result_is_fitted_not_calibrated():
    device, physics, config = _base_objects()
    result = fit_single_parameter_cv_dataset(
        _synthetic_dataset(),
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=_qfix_spec(),
        protocol=_protocol(),
    )
    assert result.scientific_status == "FITTED"
    assert result.to_dict()["scientific_status"] == "FITTED"


def test_fit_result_serializes_hashes():
    device, physics, config = _base_objects()
    dataset = _synthetic_dataset()
    spec = _qfix_spec()
    protocol = _protocol()

    result = fit_single_parameter_cv_dataset(
        dataset,
        base_device=device,
        base_physics=physics,
        base_simulation_config=config,
        calibration_spec=spec,
        protocol=protocol,
    )
    payload = result.to_dict()

    assert payload["dataset_hash"] == dataset.dataset_hash()
    assert (
        payload["calibration_specification_hash"]
        == spec.specification_hash()
    )
    assert payload["protocol_hash"] == protocol.protocol_hash()
    assert payload["workflow"] == "single-dataset-cv-fit"


def test_fit_rejects_non_cv_dataset():
    device, physics, config = _base_objects()

    dataset = DeviceObservableDataset(
        independent_variable_name="time",
        independent_variable_unit="s",
        independent_values=np.asarray([0.0, 1.0]),
        observable_name="delta_vfb",
        observable_unit="V",
        observed_values=np.asarray([1.0, 0.9]),
        metadata=ExperimentalDatasetMetadata(
            dataset_id="not-cv",
            source="synthetic",
            sample_id="sample",
            temperature_K=300.0,
        ),
        conditions=(
            ExperimentalCondition(
                name="retention_gate_voltage",
                value=0.0,
                unit="V",
            ),
        ),
    )

    with pytest.raises(ValueError, match="C-V fitting requires"):
        fit_single_parameter_cv_dataset(
            dataset,
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_qfix_spec(),
            protocol=_protocol(),
        )


def test_fit_rejects_multi_parameter_spec():
    device, physics, config = _base_objects()

    spec = DeviceCalibrationSpec(
        parameter_set=FitParameterSet(
            (
                FitParameter(
                    name="qfix_C_m2",
                    initial_value=0.0,
                    lower_bound=-3e-3,
                    upper_bound=3e-3,
                ),
                FitParameter(
                    name="nu0_Hz",
                    initial_value=1e12,
                    lower_bound=1e10,
                    upper_bound=1e13,
                ),
            )
        ),
        bindings=(
            DeviceFitParameterBinding(
                "qfix_C_m2",
                DeviceFitTarget.SIMULATION_QFIX_C_M2,
            ),
            DeviceFitParameterBinding(
                "nu0_Hz",
                DeviceFitTarget.KINETICS_NU0_HZ,
            ),
        ),
    )

    with pytest.raises(ValueError, match="exactly one free parameter"):
        fit_single_parameter_cv_dataset(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=spec,
            protocol=_protocol(),
        )


def test_protocol_domain_must_cover_dataset():
    device, physics, config = _base_objects()

    with pytest.raises(ValueError, match="extrapolation is not allowed"):
        fit_single_parameter_cv_dataset(
            _synthetic_dataset(),
            base_device=device,
            base_physics=physics,
            base_simulation_config=config,
            calibration_spec=_qfix_spec(),
            protocol=CVCalibrationProtocol(
                vmin_V=-1.0,
                vmax_V=1.0,
                points=21,
            ),
        )
