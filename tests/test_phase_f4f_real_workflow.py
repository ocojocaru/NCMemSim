from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from ncmemsim.materials.provenance import (
    ParameterStatus,
)


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

WORKFLOW_PATH = (
    REPOSITORY_ROOT
    / "examples"
    / "phase_f4f_tran2016_calibration.py"
)


def _load_workflow_module():
    spec = importlib.util.spec_from_file_location(
        "phase_f4f_tran2016_calibration",
        WORKFLOW_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not load the F4f1 workflow module."
        )

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


@pytest.fixture(scope="module")
def workflow_module():
    return _load_workflow_module()


@pytest.fixture(scope="module")
def workflow_report(workflow_module):
    return workflow_module.run_workflow()


def test_workflow_example_exists():
    assert WORKFLOW_PATH.is_file()


def test_reference_datasets_are_four_plus_four(
    workflow_module,
):
    (
        metadata,
        fit_dataset,
        validation_dataset,
    ) = workflow_module.load_reference_datasets()

    assert (
        metadata["split_policy"]["type"]
        == "holdout_from_same_published_curve"
    )
    assert fit_dataset.n_points == 4
    assert validation_dataset.n_points == 4


def test_workflow_records_non_independent_validation(
    workflow_report,
):
    scope = workflow_report[
        "scientific_scope"
    ]

    assert (
        scope["validation_type"]
        == "holdout_from_same_published_curve"
    )
    assert scope["independent_experiment"] is False
    assert (
        "not an independent experimental replication"
        in scope["interpretation"]
    )


def test_fit_and_validation_dataset_hashes_are_distinct(
    workflow_report,
):
    inputs = workflow_report["inputs"]

    assert (
        inputs["fit_dataset_hash"]
        != inputs["validation_dataset_hash"]
    )


def test_parameter_specification_uses_only_a_and_urbach(
    workflow_module,
):
    parameter_set = (
        workflow_module.build_fit_parameter_set()
    )

    assert parameter_set.names == (
        "direct_prefactor_A",
        "urbach_energy_eV",
    )


def test_initial_values_are_tran_literature_central_values(
    workflow_module,
):
    parameter_set = (
        workflow_module.build_fit_parameter_set()
    )

    initial = parameter_set.initial_values

    assert initial[0] == pytest.approx(
        3.68e6
    )
    assert initial[1] == pytest.approx(
        0.01058
    )


def test_fit_bounds_are_broader_than_initial_values(
    workflow_module,
):
    parameter_set = (
        workflow_module.build_fit_parameter_set()
    )

    initial = parameter_set.initial_values
    lower = parameter_set.lower_bounds
    upper = parameter_set.upper_bounds

    assert np.all(lower < initial)
    assert np.all(initial < upper)


def test_validation_threshold_is_derived_only_from_uncertainty(
    workflow_module,
):
    (
        _,
        _,
        validation_dataset,
    ) = workflow_module.load_reference_datasets()

    uncertainty = (
        validation_dataset.absorption_uncertainty_m_inv
    )
    assert uncertainty is not None

    expected = math.sqrt(
        float(
            np.mean(
                uncertainty * uncertainty
            )
        )
    )

    observed = (
        workflow_module.validation_rmse_threshold(
            validation_dataset
        )
    )

    assert observed == pytest.approx(
        expected
    )


def test_validation_threshold_matches_f4f0_digitization_scale(
    workflow_report,
):
    threshold = workflow_report[
        "qualification_policy"
    ][
        "validation_rmse_threshold_m_inv"
    ]

    assert 1.5e4 < threshold < 1.6e4


def test_fit_converges(
    workflow_report,
):
    assert (
        workflow_report["fit_result"]["success"]
        is True
    )


def test_real_data_fit_moves_a_below_tran_central_value(
    workflow_report,
):
    fitted = workflow_report[
        "fit_result"
    ][
        "parameters"
    ]

    assert (
        2.0e6
        < fitted["direct_prefactor_A"]
        < 3.0e6
    )
    assert (
        fitted["direct_prefactor_A"]
        < 3.68e6
    )


def test_real_data_fit_moves_urbach_below_tran_central_value(
    workflow_report,
):
    fitted = workflow_report[
        "fit_result"
    ][
        "parameters"
    ]

    assert (
        0.007
        < fitted["urbach_energy_eV"]
        < 0.010
    )
    assert (
        fitted["urbach_energy_eV"]
        < 0.01058
    )


def test_real_data_fit_remains_locally_identifiable(
    workflow_report,
):
    diagnostics = workflow_report[
        "fit_result"
    ][
        "uncertainty_diagnostics"
    ]

    assert (
        diagnostics["locally_identifiable"]
        is True
    )
    assert diagnostics["jacobian_rank"] == 2
    assert (
        diagnostics["covariance_available"]
        is True
    )


def test_fit_parameter_status_is_fitted_not_calibrated(
    workflow_report,
):
    assert (
        workflow_report["fit_result"][
            "parameter_status"
        ]
        == ParameterStatus.FITTED.value
    )


def test_validation_rmse_exceeds_predeclared_threshold(
    workflow_report,
):
    validation = workflow_report[
        "calibration_result"
    ][
        "validation_objective"
    ]

    threshold = workflow_report[
        "qualification_policy"
    ][
        "validation_rmse_threshold_m_inv"
    ]

    assert (
        validation[
            "root_mean_square_error"
        ]
        > threshold
    )


def test_validation_rmse_is_materially_larger_than_digitization_scale(
    workflow_report,
):
    validation = workflow_report[
        "calibration_result"
    ][
        "validation_objective"
    ]

    threshold = workflow_report[
        "qualification_policy"
    ][
        "validation_rmse_threshold_m_inv"
    ]

    ratio = (
        validation[
            "root_mean_square_error"
        ]
        / threshold
    )

    assert ratio > 2.0


def test_validation_r2_is_good_but_not_sufficient_for_calibration(
    workflow_report,
):
    validation = workflow_report[
        "calibration_result"
    ][
        "validation_objective"
    ]

    r2 = validation[
        "coefficient_of_determination"
    ]

    assert r2 is not None
    assert 0.90 < r2 < 0.98


def test_real_reference_workflow_is_not_calibrated(
    workflow_report,
):
    calibration = workflow_report[
        "calibration_result"
    ]

    assert (
        calibration[
            "eligible_for_calibration"
        ]
        is False
    )
    assert calibration["calibrated"] is False
    assert (
        calibration[
            "calibrated_parameter_set_name"
        ]
        is None
    )


def test_validation_rmse_is_recorded_as_failed_criterion(
    workflow_report,
):
    failed = workflow_report[
        "calibration_result"
    ][
        "failed_criteria"
    ]

    assert "validation_rmse" in failed


def test_workflow_does_not_claim_independent_experimental_calibration(
    workflow_report,
):
    assert (
        workflow_report[
            "scientific_conclusion"
        ]
        == "NOT_CALIBRATED"
    )

    assert (
        workflow_report[
            "scientific_scope"
        ][
            "independent_experiment"
        ]
        is False
    )


def test_threshold_policy_is_explicitly_not_tuned_to_outcome(
    workflow_report,
):
    note = workflow_report[
        "qualification_policy"
    ]["note"]

    assert (
        "not tuned to force a CALIBRATED outcome"
        in note
    )


def test_repeat_runs_are_numerically_reproducible(
    workflow_module,
    workflow_report,
):
    second = workflow_module.run_workflow()

    first_parameters = workflow_report[
        "fit_result"
    ]["parameters"]
    second_parameters = second[
        "fit_result"
    ]["parameters"]

    assert (
        second_parameters[
            "direct_prefactor_A"
        ]
        == pytest.approx(
            first_parameters[
                "direct_prefactor_A"
            ],
            rel=1.0e-10,
            abs=1.0e-6,
        )
    )

    assert (
        second_parameters[
            "urbach_energy_eV"
        ]
        == pytest.approx(
            first_parameters[
                "urbach_energy_eV"
            ],
            rel=1.0e-10,
            abs=1.0e-12,
        )
    )

    assert (
        second[
            "scientific_conclusion"
        ]
        == workflow_report[
            "scientific_conclusion"
        ]
    )
