from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.fitting import (
    DeterministicFitResult,
    FitParameter,
    FitParameterSet,
    LeastSquaresConfig,
    run_least_squares_fit,
)


def _single_parameter_set(
    *,
    initial_value: float = 0.0,
    lower_bound: float = -10.0,
    upper_bound: float = 10.0,
) -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            FitParameter(
                name="x",
                initial_value=initial_value,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                unit="arb.",
            ),
        )
    )


def _two_parameter_set() -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            FitParameter(
                name="a",
                initial_value=0.0,
                lower_bound=-10.0,
                upper_bound=10.0,
            ),
            FitParameter(
                name="b",
                initial_value=0.0,
                lower_bound=-10.0,
                upper_bound=10.0,
            ),
        )
    )


def test_default_config_is_explicit_and_serializable():
    config = LeastSquaresConfig()

    assert config.ftol == pytest.approx(1.0e-8)
    assert config.xtol == pytest.approx(1.0e-8)
    assert config.gtol == pytest.approx(1.0e-8)
    assert config.max_nfev == 1000

    assert config.to_dict() == {
        "method": "trf",
        "jacobian": "2-point",
        "loss": "linear",
        "parameter_scaling": "normalized-bounds-[0,1]",
        "ftol": 1.0e-8,
        "xtol": 1.0e-8,
        "gtol": 1.0e-8,
        "max_nfev": 1000,
    }


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("ftol", 0.0),
        ("ftol", -1.0),
        ("ftol", float("nan")),
        ("ftol", float("inf")),
        ("xtol", 0.0),
        ("xtol", float("nan")),
        ("gtol", -1.0),
        ("gtol", float("inf")),
    ],
)
def test_config_rejects_invalid_tolerances(
    field_name: str,
    value: float,
):
    kwargs = {
        "ftol": 1.0e-8,
        "xtol": 1.0e-8,
        "gtol": 1.0e-8,
        "max_nfev": 1000,
    }
    kwargs[field_name] = value

    with pytest.raises(ValueError):
        LeastSquaresConfig(**kwargs)


@pytest.mark.parametrize(
    "max_nfev",
    [0, -1, 1.5, True],
)
def test_config_requires_positive_integer_max_nfev(max_nfev):
    with pytest.raises(ValueError, match="max_nfev"):
        LeastSquaresConfig(max_nfev=max_nfev)


def test_config_hash_is_deterministic():
    first = LeastSquaresConfig()
    second = LeastSquaresConfig()

    assert first.configuration_hash() == second.configuration_hash()
    assert len(first.configuration_hash()) == 64


def test_scalar_fit_converges_to_known_solution():
    parameter_set = _single_parameter_set()

    result = run_least_squares_fit(
        parameter_set,
        lambda values: np.array([values[0] - 3.0]),
    )

    assert isinstance(result, DeterministicFitResult)
    assert result.success is True
    assert result.fitted_values[0] == pytest.approx(
        3.0,
        abs=1.0e-6,
    )
    assert result.fitted_parameters["x"] == pytest.approx(
        3.0,
        abs=1.0e-6,
    )
    assert result.objective_sum_squares == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert result.cost == pytest.approx(
        0.0,
        abs=1.0e-12,
    )


def test_two_parameter_fit_converges_to_known_linear_solution():
    parameter_set = _two_parameter_set()

    def residuals(values: np.ndarray) -> np.ndarray:
        a, b = values

        return np.array(
            [
                a + 2.0 * b - 5.0,
                2.0 * a - b - 1.0,
            ]
        )

    result = run_least_squares_fit(
        parameter_set,
        residuals,
    )

    assert result.success is True
    assert result.fitted_parameters["a"] == pytest.approx(
        1.4,
        abs=1.0e-6,
    )
    assert result.fitted_parameters["b"] == pytest.approx(
        1.8,
        abs=1.0e-6,
    )
    assert result.objective_sum_squares == pytest.approx(
        0.0,
        abs=1.0e-12,
    )


def test_fit_respects_physical_parameter_bounds():
    parameter_set = _single_parameter_set(
        initial_value=0.0,
        lower_bound=-2.0,
        upper_bound=2.0,
    )

    result = run_least_squares_fit(
        parameter_set,
        lambda values: [values[0] - 5.0],
    )

    assert result.success is True
    assert result.fitted_values[0] == pytest.approx(
        2.0,
        abs=1.0e-6,
    )
    assert result.active_mask.tolist() == [1]


def test_residual_function_receives_physical_not_normalized_values():
    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="large",
                initial_value=3.68e6,
                lower_bound=1.0e6,
                upper_bound=1.0e7,
            ),
        )
    )

    seen_values: list[float] = []

    def residuals(values: np.ndarray) -> list[float]:
        seen_values.append(float(values[0]))
        return [values[0] - 4.0e6]

    result = run_least_squares_fit(
        parameter_set,
        residuals,
    )

    assert seen_values
    assert seen_values[0] == pytest.approx(3.68e6)
    assert result.fitted_values[0] == pytest.approx(
        4.0e6,
        rel=1.0e-7,
    )


def test_differently_scaled_parameters_fit_in_physical_units():
    parameter_set = FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=1.0e6,
                upper_bound=1.0e7,
            ),
            FitParameter(
                name="urbach_energy_eV",
                initial_value=0.01058,
                lower_bound=0.001,
                upper_bound=0.100,
            ),
        )
    )

    def residuals(values: np.ndarray) -> np.ndarray:
        return np.array(
            [
                (values[0] - 4.2e6) / 1.0e5,
                (values[1] - 0.0125) / 0.001,
            ]
        )

    result = run_least_squares_fit(
        parameter_set,
        residuals,
    )

    assert result.success is True
    assert result.fitted_parameters[
        "direct_prefactor_A"
    ] == pytest.approx(
        4.2e6,
        rel=1.0e-7,
    )
    assert result.fitted_parameters[
        "urbach_energy_eV"
    ] == pytest.approx(
        0.0125,
        rel=1.0e-7,
    )


def test_result_preserves_parameter_and_solver_hashes():
    parameter_set = _single_parameter_set()
    config = LeastSquaresConfig(max_nfev=200)

    result = run_least_squares_fit(
        parameter_set,
        lambda values: [values[0] - 1.0],
        config=config,
    )

    assert (
        result.parameter_specification_hash
        == parameter_set.specification_hash()
    )
    assert (
        result.solver_configuration_hash
        == config.configuration_hash()
    )


def test_result_arrays_are_read_only():
    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: [values[0] - 1.0],
    )

    assert not result.initial_values.flags.writeable
    assert not result.fitted_values.flags.writeable
    assert not result.objective_residuals.flags.writeable
    assert not result.active_mask.flags.writeable

    with pytest.raises(ValueError):
        result.fitted_values[0] = 0.0


def test_result_records_scipy_version_and_solver_diagnostics():
    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: [values[0] - 1.0],
    )

    assert result.scipy_version
    assert result.status > 0
    assert result.message
    assert result.nfev > 0
    assert result.njev is None or result.njev >= 0
    assert result.optimality >= 0.0


def test_result_to_dict_is_explicit_and_serializable():
    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: [values[0] - 1.0],
    )

    data = result.to_dict()

    assert data["schema_version"] == 1
    assert data["solver"] == "scipy.optimize.least_squares"
    assert data["scipy_version"] == result.scipy_version
    assert data["initial_parameters"] == {
        "x": pytest.approx(0.0)
    }
    assert data["fitted_parameters"]["x"] == pytest.approx(
        1.0,
        abs=1.0e-6,
    )
    assert data["parameter_specification_hash"] == (
        result.parameter_specification_hash
    )
    assert data["solver_configuration_hash"] == (
        result.solver_configuration_hash
    )


def test_same_problem_is_numerically_reproducible():
    parameter_set = _two_parameter_set()

    def residuals(values: np.ndarray) -> np.ndarray:
        a, b = values
        return np.array(
            [
                a + b - 3.0,
                2.0 * a - b,
            ]
        )

    first = run_least_squares_fit(
        parameter_set,
        residuals,
    )
    second = run_least_squares_fit(
        parameter_set,
        residuals,
    )

    assert second.fitted_values.tolist() == pytest.approx(
        first.fitted_values.tolist(),
        rel=0.0,
        abs=1.0e-12,
    )
    assert second.objective_sum_squares == pytest.approx(
        first.objective_sum_squares,
        rel=0.0,
        abs=1.0e-18,
    )
    assert second.nfev == first.nfev


def test_runner_returns_unsuccessful_result_when_evaluation_budget_exhausted():
    config = LeastSquaresConfig(max_nfev=1)

    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: [values[0] - 3.0],
        config=config,
    )

    assert result.success is False
    assert result.status == 0
    assert result.nfev == 1
    assert result.message


def test_runner_accepts_sequence_residual_output():
    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: (values[0] - 2.0,),
    )

    assert result.success is True
    assert result.fitted_values[0] == pytest.approx(
        2.0,
        abs=1.0e-6,
    )


@pytest.mark.parametrize(
    "bad_output",
    [
        [],
        [[1.0]],
        [float("nan")],
        [float("inf")],
    ],
)
def test_runner_rejects_invalid_residual_output(bad_output):
    with pytest.raises(ValueError):
        run_least_squares_fit(
            _single_parameter_set(),
            lambda values: bad_output,
        )


def test_runner_rejects_residual_vector_length_changes():
    calls = 0

    def changing_residuals(values: np.ndarray):
        nonlocal calls
        calls += 1

        if calls == 1:
            return [values[0] - 1.0]

        return [
            values[0] - 1.0,
            values[0] - 2.0,
        ]

    with pytest.raises(
        ValueError,
        match="constant length",
    ):
        run_least_squares_fit(
            _single_parameter_set(),
            changing_residuals,
        )


def test_runner_requires_parameter_set_instance():
    with pytest.raises(TypeError, match="parameter_set"):
        run_least_squares_fit(
            "not-a-set",  # type: ignore[arg-type]
            lambda values: [0.0],
        )


def test_runner_requires_callable_residual_function():
    with pytest.raises(TypeError, match="residual_function"):
        run_least_squares_fit(
            _single_parameter_set(),
            None,  # type: ignore[arg-type]
        )


def test_runner_requires_config_instance_when_provided():
    with pytest.raises(TypeError, match="config"):
        run_least_squares_fit(
            _single_parameter_set(),
            lambda values: [values[0]],
            config={},  # type: ignore[arg-type]
        )


def test_result_does_not_assign_material_provenance():
    result = run_least_squares_fit(
        _single_parameter_set(),
        lambda values: [values[0] - 1.0],
    )

    data = result.to_dict()

    assert "provenance" not in data
    assert "status_name" not in data
    assert "calibrated" not in data
