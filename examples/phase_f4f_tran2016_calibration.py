from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ncmemsim.calibration import (
    CalibrationCriteria,
)
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
)
from ncmemsim.io import (
    load_optical_absorption_csv,
)
from ncmemsim.materials.optics import (
    fit_gesn_near_edge_absorption,
    qualify_gesn_near_edge_fit,
)


WORKFLOW_NAME = (
    "tran2016_sampleA_fig6a_near_edge_calibration"
)

FIT_PARAMETER_SET_NAME = (
    "gesn-near-edge-tran2016-fig6a-sampleA-fit-v1"
)

CALIBRATED_PARAMETER_SET_NAME = (
    "gesn-near-edge-tran2016-fig6a-sampleA-calibrated-v1"
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reference_directory() -> Path:
    return (
        repository_root()
        / "data"
        / "reference"
        / "tran2016"
    )


def load_reference_metadata() -> dict[str, Any]:
    path = (
        reference_directory()
        / "tran2016_sampleA_fig6a_metadata.json"
    )

    with path.open(
        encoding="utf-8"
    ) as file_handle:
        return json.load(file_handle)


def _experimental_metadata(
    *,
    dataset_id: str,
    notes: str,
    reference_metadata: dict[str, Any],
) -> ExperimentalDatasetMetadata:
    source = reference_metadata["source"]
    sample = reference_metadata["sample_metadata"]

    return ExperimentalDatasetMetadata(
        dataset_id=dataset_id,
        source=source["citation"],
        doi=source["doi"],
        sample_id=source["sample"],
        temperature_description=(
            sample["temperature_description"]
        ),
        notes=notes,
    )


def load_reference_datasets():
    metadata = load_reference_metadata()
    directory = reference_directory()

    fit_dataset = load_optical_absorption_csv(
        directory
        / "tran2016_sampleA_fig6a_fit.csv",
        sn_fraction=0.0,
        metadata=_experimental_metadata(
            dataset_id=(
                "tran2016-sampleA-fig6a-fit"
            ),
            notes=(
                "Alternating-point fitting subset "
                "digitized from Tran 2016 Figure 6(a)."
            ),
            reference_metadata=metadata,
        ),
    )

    validation_dataset = load_optical_absorption_csv(
        directory
        / "tran2016_sampleA_fig6a_validation.csv",
        sn_fraction=0.0,
        metadata=_experimental_metadata(
            dataset_id=(
                "tran2016-sampleA-fig6a-validation"
            ),
            notes=(
                "Alternating-point holdout subset "
                "from the same published Tran 2016 "
                "Figure 6(a) curve."
            ),
            reference_metadata=metadata,
        ),
    )

    return metadata, fit_dataset, validation_dataset


def build_fit_parameter_set() -> FitParameterSet:
    """
    Return the explicit F4f1 parameter specification.

    The initial values are the Tran 2016 literature-fit central values.
    The bounds are deliberately broader than the reported uncertainties;
    they are numerical/physical search bounds rather than confidence
    intervals or literature uncertainty claims.
    """

    return FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=1.0e6,
                upper_bound=7.0e6,
                unit="m^-1 eV^(1/2)",
                description=(
                    "Direct near-edge absorption prefactor."
                ),
            ),
            FitParameter(
                name="urbach_energy_eV",
                initial_value=0.01058,
                lower_bound=0.005,
                upper_bound=0.020,
                unit="eV",
                description="Urbach energy.",
            ),
        )
    )


def validation_rmse_threshold(
    validation_dataset,
) -> float:
    """
    Derive the validation RMSE criterion from digitization uncertainty.

    F4f0 assigns a 5% alpha uncertainty as a conservative digitization
    estimate. F4f1 predeclares that validation RMSE must not exceed the
    RMS of those assigned pointwise uncertainties.

    This threshold depends only on the validation dataset uncertainty,
    not on model predictions or fit residuals.
    """

    uncertainty = (
        validation_dataset.absorption_uncertainty_m_inv
    )

    if uncertainty is None:
        raise ValueError(
            "The Tran 2016 F4f1 workflow requires the "
            "digitization-uncertainty column."
        )

    values = np.asarray(
        uncertainty,
        dtype=float,
    )

    return float(
        math.sqrt(
            float(
                np.mean(
                    values * values
                )
            )
        )
    )


def build_calibration_criteria(
    validation_dataset,
) -> CalibrationCriteria:
    return CalibrationCriteria(
        max_validation_rmse=(
            validation_rmse_threshold(
                validation_dataset
            )
        ),
        require_distinct_validation_dataset=True,
        require_local_identifiability=True,
        require_covariance=True,
    )


def run_workflow() -> dict[str, Any]:
    (
        reference_metadata,
        fit_dataset,
        validation_dataset,
    ) = load_reference_datasets()

    parameter_set = build_fit_parameter_set()

    fit_result = fit_gesn_near_edge_absorption(
        fit_dataset,
        parameter_set,
        fitted_parameter_set_name=(
            FIT_PARAMETER_SET_NAME
        ),
    )

    criteria = build_calibration_criteria(
        validation_dataset
    )

    calibration_result = (
        qualify_gesn_near_edge_fit(
            fit_result,
            validation_dataset,
            criteria=criteria,
            calibrated_parameter_set_name=(
                CALIBRATED_PARAMETER_SET_NAME
            ),
        )
    )

    split_policy = reference_metadata[
        "split_policy"
    ]

    report = {
        "schema_version": 1,
        "workflow": WORKFLOW_NAME,
        "reference_classification": (
            reference_metadata["classification"]
        ),
        "scientific_scope": {
            "sample": (
                reference_metadata["source"][
                    "sample"
                ]
            ),
            "sn_fraction": (
                reference_metadata[
                    "sample_metadata"
                ]["sn_fraction"]
            ),
            "reported_in_plane_compressive_strain_percent": (
                reference_metadata[
                    "sample_metadata"
                ][
                    "in_plane_compressive_strain_percent"
                ]
            ),
            "temperature_description": (
                reference_metadata[
                    "sample_metadata"
                ]["temperature_description"]
            ),
            "validation_type": (
                split_policy["type"]
            ),
            "independent_experiment": (
                split_policy[
                    "independent_experiment"
                ]
            ),
            "interpretation": (
                "This workflow validates against a disjoint holdout "
                "from the same published curve. It is not an "
                "independent experimental replication."
            ),
        },
        "inputs": {
            "fit_dataset_id": (
                fit_dataset.metadata.dataset_id
            ),
            "fit_dataset_hash": (
                fit_dataset.dataset_hash()
            ),
            "fit_n_points": fit_dataset.n_points,
            "validation_dataset_id": (
                validation_dataset.metadata.dataset_id
            ),
            "validation_dataset_hash": (
                validation_dataset.dataset_hash()
            ),
            "validation_n_points": (
                validation_dataset.n_points
            ),
            "assigned_relative_alpha_uncertainty": (
                reference_metadata["digitization"][
                    "assigned_relative_alpha_uncertainty"
                ]
            ),
        },
        "fit_configuration": {
            "parameter_specification": (
                parameter_set.to_dict()
            ),
            "parameter_specification_hash": (
                parameter_set.specification_hash()
            ),
            "fitted_parameter_set_name": (
                FIT_PARAMETER_SET_NAME
            ),
            "direct_gap_policy": (
                "Use the existing NCMemSim direct_gap_gesn_eV() "
                "relation unchanged; direct gap and bowing are not "
                "optimized in F4f1."
            ),
        },
        "fit_result": {
            "success": (
                fit_result.numerical_result.success
            ),
            "parameters": (
                fit_result.fitted_parameters
            ),
            "objective": (
                fit_result.objective.to_dict()
            ),
            "uncertainty_diagnostics": (
                fit_result.uncertainty_diagnostics.to_dict()
            ),
            "parameter_standard_errors": (
                fit_result.parameter_standard_errors
            ),
            "parameter_correlation": (
                fit_result.parameter_correlation
            ),
            "parameter_status": "fitted",
        },
        "qualification_policy": {
            "criterion_basis": (
                "validation RMSE <= RMS of the assigned "
                "pointwise digitization uncertainties"
            ),
            "validation_rmse_threshold_m_inv": (
                criteria.max_validation_rmse
            ),
            "criteria": criteria.to_dict(),
            "criteria_hash": (
                criteria.criteria_hash()
            ),
            "note": (
                "The threshold is derived before evaluating model "
                "predictions and is not tuned to force a "
                "CALIBRATED outcome."
            ),
        },
        "calibration_result": {
            "eligible_for_calibration": (
                calibration_result.qualification.
                eligible_for_calibration
            ),
            "calibrated": (
                calibration_result.calibrated
            ),
            "failed_criteria": list(
                calibration_result.failed_criteria
            ),
            "validation_objective": (
                calibration_result.qualification.
                validation_objective.to_dict()
            ),
            "qualification_hash": (
                calibration_result.qualification.
                qualification_hash()
            ),
            "calibrated_parameter_set_name": (
                None
                if calibration_result.
                calibrated_parameter_set is None
                else calibration_result.
                calibrated_parameter_set.name
            ),
        },
        "scientific_conclusion": (
            "CALIBRATED"
            if calibration_result.calibrated
            else "NOT_CALIBRATED"
        ),
    }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the NCMemSim F4f1 Tran 2016 "
            "real-data near-edge fitting and "
            "holdout-qualification workflow."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional JSON output path. The report is "
            "also printed to stdout."
        ),
    )
    args = parser.parse_args()

    report = run_workflow()

    text = json.dumps(
        report,
        indent=2,
        sort_keys=True,
    )

    print(text)

    if args.output is not None:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            text + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
