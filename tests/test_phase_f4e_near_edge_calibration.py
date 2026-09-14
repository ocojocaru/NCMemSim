from __future__ import annotations

import numpy as np
import pytest

from ncmemsim import make_gesn
from ncmemsim.calibration import CalibrationCriteria
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
)
from ncmemsim.materials.optics import (
    GeSnNearEdgeCalibrationResult,
    GeSnNearEdgeParameterSet,
    GeSnNearEdgeReferenceModel,
    fit_gesn_near_edge_absorption,
    qualify_gesn_near_edge_fit,
)
from ncmemsim.materials.optics.near_edge import (
    TRAN_2016_PARAMETER_SET_NAME,
)
from ncmemsim.materials.provenance import (
    ParameterStatus,
)


FIT_WAVELENGTHS_NM = np.array(
    [
        1400.0,
        1450.0,
        1500.0,
        1600.0,
        1650.0,
        1700.0,
        1750.0,
    ]
)

VALIDATION_WAVELENGTHS_NM = np.array(
    [
        1425.0,
        1475.0,
        1525.0,
        1575.0,
        1650.0,
        1725.0,
    ]
)


def _true_parameters() -> GeSnNearEdgeParameterSet:
    return GeSnNearEdgeParameterSet(
        name="synthetic-calibration-truth",
        direct_prefactor_A=4.40e6,
        urbach_energy_eV=0.0135,
        temperature_K=300.0,
    )


def _alpha(
    wavelengths_nm: np.ndarray,
    *,
    sn_fraction: float = 0.0,
) -> np.ndarray:
    model = GeSnNearEdgeReferenceModel(
        parameters=_true_parameters()
    )
    material = make_gesn(sn_fraction)

    return np.array(
        [
            model.evaluate(
                material,
                wavelength_nm=float(wavelength_nm),
            ).absorption_coefficient_m_inv
            for wavelength_nm in wavelengths_nm
        ]
    )


def _fit_dataset() -> OpticalAbsorptionDataset:
    return OpticalAbsorptionDataset(
        wavelength_nm=FIT_WAVELENGTHS_NM,
        absorption_coefficient_m_inv=_alpha(
            FIT_WAVELENGTHS_NM
        ),
        sn_fraction=0.0,
        metadata=ExperimentalDatasetMetadata(
            dataset_id="synthetic-calibration-fit",
            source="NCMemSim synthetic calibration fitting data",
            temperature_K=300.0,
        ),
    )


def _validation_dataset(
    *,
    scale: float = 1.0,
    uncertainty: bool = False,
) -> OpticalAbsorptionDataset:
    kwargs = {}

    if uncertainty:
        kwargs["absorption_uncertainty_m_inv"] = np.full(
            VALIDATION_WAVELENGTHS_NM.size,
            2.0e4,
        )

    return OpticalAbsorptionDataset(
        wavelength_nm=VALIDATION_WAVELENGTHS_NM,
        absorption_coefficient_m_inv=(
            scale
            * _alpha(VALIDATION_WAVELENGTHS_NM)
        ),
        sn_fraction=0.0,
        metadata=ExperimentalDatasetMetadata(
            dataset_id="synthetic-calibration-validation",
            source="NCMemSim synthetic independent validation data",
            doi="10.0000/ncmemsim.synthetic.validation",
            temperature_K=300.0,
        ),
        **kwargs,
    )


def _fit_parameter_set() -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=2.0e6,
                upper_bound=7.0e6,
            ),
            FitParameter(
                name="urbach_energy_eV",
                initial_value=0.01058,
                lower_bound=0.005,
                upper_bound=0.030,
            ),
        )
    )


def _fit_result():
    return fit_gesn_near_edge_absorption(
        _fit_dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name=(
            "synthetic-near-edge-fitted-v1"
        ),
    )


def _criteria() -> CalibrationCriteria:
    return CalibrationCriteria(
        max_validation_rmse=1.0,
        min_validation_r2=0.999999,
    )


def test_independent_validation_promotes_to_calibrated():
    fit_result = _fit_result()

    result = qualify_gesn_near_edge_fit(
        fit_result,
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "synthetic-near-edge-calibrated-v1"
        ),
    )

    assert isinstance(
        result,
        GeSnNearEdgeCalibrationResult,
    )
    assert result.qualification.eligible_for_calibration is True
    assert result.calibrated is True
    assert result.failed_criteria == ()
    assert result.calibrated_parameter_set is not None


def test_calibrated_parameter_values_equal_fitted_values():
    fit_result = _fit_result()

    result = qualify_gesn_near_edge_fit(
        fit_result,
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "synthetic-near-edge-calibrated-v1"
        ),
    )

    calibrated = result.calibrated_parameter_set
    assert calibrated is not None

    fitted = fit_result.fitted_parameter_set

    assert (
        calibrated.direct_prefactor_A
        == fitted.direct_prefactor_A
    )
    assert (
        calibrated.urbach_energy_eV
        == fitted.urbach_energy_eV
    )
    assert (
        calibrated.temperature_K
        == fitted.temperature_K
    )


def test_calibrated_parameters_receive_calibrated_provenance():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "synthetic-near-edge-calibrated-v1"
        ),
    )

    calibrated = result.calibrated_parameter_set
    assert calibrated is not None

    provenance = calibrated.provenance
    assert provenance is not None

    for name in (
        "direct_prefactor_A",
        "urbach_energy_eV",
    ):
        entry = provenance[name]

        assert (
            entry.status
            is ParameterStatus.CALIBRATED
        )
        assert (
            entry.parameter_set
            == "synthetic-near-edge-calibrated-v1"
        )
        assert (
            entry.doi
            == "10.0000/ncmemsim.synthetic.validation"
        )
        assert entry.reported_uncertainty is None
        assert entry.uncertainty_unit is None
        assert "qualification_hash=" in (
            entry.notes or ""
        )
        assert "parent_parameter_set=" in (
            entry.notes or ""
        )


def test_original_fitted_parameter_set_remains_fitted():
    fit_result = _fit_result()

    original = fit_result.fitted_parameter_set
    original_provenance = original.provenance
    assert original_provenance is not None

    result = qualify_gesn_near_edge_fit(
        fit_result,
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "synthetic-near-edge-calibrated-v1"
        ),
    )

    assert result.calibrated is True
    assert fit_result.fitted_parameter_set is original

    for name in (
        "direct_prefactor_A",
        "urbach_energy_eV",
    ):
        assert (
            original_provenance[name].status
            is ParameterStatus.FITTED
        )


def test_failed_validation_does_not_create_calibrated_set():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(scale=1.20),
        criteria=CalibrationCriteria(
            max_validation_rmse=100.0,
        ),
        calibrated_parameter_set_name=(
            "should-not-be-created"
        ),
    )

    assert result.qualification.eligible_for_calibration is False
    assert result.calibrated is False
    assert result.calibrated_parameter_set is None
    assert "validation_rmse" in result.failed_criteria


def test_same_dataset_fails_default_independence_requirement():
    fit_result = _fit_result()
    same_dataset = _fit_dataset()

    result = qualify_gesn_near_edge_fit(
        fit_result,
        same_dataset,
        criteria=CalibrationCriteria(
            max_validation_rmse=1.0,
        ),
        calibrated_parameter_set_name=(
            "same-data-calibrated-v1"
        ),
    )

    assert result.calibrated is False
    assert result.calibrated_parameter_set is None
    assert "distinct_validation_dataset" in (
        result.failed_criteria
    )


def test_same_dataset_can_only_promote_when_requirement_explicitly_disabled():
    fit_result = _fit_result()
    same_dataset = _fit_dataset()

    result = qualify_gesn_near_edge_fit(
        fit_result,
        same_dataset,
        criteria=CalibrationCriteria(
            max_validation_rmse=1.0,
            require_distinct_validation_dataset=False,
        ),
        calibrated_parameter_set_name=(
            "explicit-same-data-calibrated-v1"
        ),
    )

    assert result.calibrated is True
    assert result.calibrated_parameter_set is not None


def test_weighted_validation_objective_is_preserved():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(
            uncertainty=True
        ),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "weighted-validation-calibrated-v1"
        ),
    )

    assert (
        result.qualification.validation_objective.weighted
        is True
    )


def test_validation_does_not_reoptimize_parameters():
    fit_result = _fit_result()
    fitted_values_before = (
        fit_result.numerical_result.fitted_values.copy()
    )
    nfev_before = fit_result.numerical_result.nfev

    qualify_gesn_near_edge_fit(
        fit_result,
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "no-reoptimization-calibrated-v1"
        ),
    )

    assert fit_result.numerical_result.nfev == nfev_before
    assert np.array_equal(
        fit_result.numerical_result.fitted_values,
        fitted_values_before,
    )


def test_validation_predictions_are_read_only():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "read-only-calibrated-v1"
        ),
    )

    assert (
        not result.predicted_absorption_m_inv.flags.writeable
    )

    with pytest.raises(ValueError):
        result.predicted_absorption_m_inv[0] = 0.0


def test_result_records_validation_identity_and_hash():
    validation_dataset = _validation_dataset()

    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        validation_dataset,
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "identity-calibrated-v1"
        ),
    )

    assert (
        result.validation_dataset_id
        == validation_dataset.metadata.dataset_id
    )
    assert (
        result.validation_dataset_hash
        == validation_dataset.dataset_hash()
    )
    assert (
        result.qualification.validation_dataset_hash
        == validation_dataset.dataset_hash()
    )


def test_result_serialization_records_qualification_and_calibrated_set():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(),
        criteria=_criteria(),
        calibrated_parameter_set_name=(
            "serialized-calibrated-v1"
        ),
    )

    data = result.to_dict()

    assert data["schema_version"] == 1
    assert (
        data["calibration_type"]
        == "gesn_near_edge_optical_absorption"
    )
    assert data["calibrated"] is True
    assert (
        data["qualification"]["eligible_for_calibration"]
        is True
    )
    assert (
        data["qualification_hash"]
        == result.qualification.qualification_hash()
    )
    assert (
        data["calibrated_parameter_set"]["name"]
        == "serialized-calibrated-v1"
    )
    assert (
        data["calibrated_parameter_set"][
            "provenance"
        ][
            "direct_prefactor_A"
        ][
            "status"
        ]
        == ParameterStatus.CALIBRATED.value
    )


def test_failed_result_serializes_without_calibrated_parameter_set():
    result = qualify_gesn_near_edge_fit(
        _fit_result(),
        _validation_dataset(scale=1.20),
        criteria=CalibrationCriteria(
            max_validation_rmse=100.0,
        ),
        calibrated_parameter_set_name=(
            "not-created-calibrated-v1"
        ),
    )

    data = result.to_dict()

    assert data["calibrated"] is False
    assert data["calibrated_parameter_set"] is None
    assert (
        data["qualification"]["eligible_for_calibration"]
        is False
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        "synthetic-near-edge-fitted-v1",
        TRAN_2016_PARAMETER_SET_NAME,
    ],
)
def test_calibrated_parameter_set_requires_new_identity(
    name: str,
):
    with pytest.raises(ValueError):
        qualify_gesn_near_edge_fit(
            _fit_result(),
            _validation_dataset(),
            criteria=_criteria(),
            calibrated_parameter_set_name=name,
        )


def test_requires_gesn_fit_result():
    with pytest.raises(
        TypeError,
        match="GeSnNearEdgeFitResult",
    ):
        qualify_gesn_near_edge_fit(
            {},  # type: ignore[arg-type]
            _validation_dataset(),
            criteria=_criteria(),
            calibrated_parameter_set_name="bad-fit-result",
        )


def test_requires_validation_dataset():
    with pytest.raises(
        TypeError,
        match="OpticalAbsorptionDataset",
    ):
        qualify_gesn_near_edge_fit(
            _fit_result(),
            {},  # type: ignore[arg-type]
            criteria=_criteria(),
            calibrated_parameter_set_name="bad-validation",
        )


def test_requires_calibration_criteria():
    with pytest.raises(
        TypeError,
        match="CalibrationCriteria",
    ):
        qualify_gesn_near_edge_fit(
            _fit_result(),
            _validation_dataset(),
            criteria={},  # type: ignore[arg-type]
            calibrated_parameter_set_name="bad-criteria",
        )
