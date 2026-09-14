from __future__ import annotations

import numpy as np
import pytest

from ncmemsim import make_gesn
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
    LeastSquaresConfig,
)
from ncmemsim.materials.optics import (
    GeSnNearEdgeParameterSet,
    GeSnNearEdgeReferenceModel,
    TRAN_2016_NEAR_EDGE_PARAMETERS,
    fit_gesn_near_edge_absorption,
    predict_gesn_near_edge_absorption_m_inv,
)
from ncmemsim.materials.optics.near_edge import (
    TRAN_2016_PARAMETER_SET_NAME,
)
from ncmemsim.materials.provenance import (
    ParameterStatus,
)


WAVELENGTHS_NM = np.array(
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


def _fit_parameter_set() -> FitParameterSet:
    return FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=2.0e6,
                upper_bound=7.0e6,
                unit="m^-1 eV^(1/2)",
            ),
            FitParameter(
                name="urbach_energy_eV",
                initial_value=0.01058,
                lower_bound=0.005,
                upper_bound=0.030,
                unit="eV",
            ),
        )
    )


def _true_parameters() -> GeSnNearEdgeParameterSet:
    return GeSnNearEdgeParameterSet(
        name="synthetic-truth",
        direct_prefactor_A=4.40e6,
        urbach_energy_eV=0.0135,
        temperature_K=300.0,
    )


def _synthetic_alpha(
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
            for wavelength_nm in WAVELENGTHS_NM
        ]
    )


def _dataset(
    *,
    uncertainty: bool = False,
    temperature_K: float | None = 300.0,
) -> OpticalAbsorptionDataset:
    metadata = ExperimentalDatasetMetadata(
        dataset_id="synthetic-near-edge-fit",
        source="NCMemSim synthetic exact-model regression data",
        doi="10.0000/ncmemsim.synthetic",
        temperature_K=temperature_K,
        temperature_description=(
            None
            if temperature_K is not None
            else "room temperature"
        ),
    )

    kwargs = {}

    if uncertainty:
        kwargs["absorption_uncertainty_m_inv"] = np.full(
            WAVELENGTHS_NM.size,
            2.0e4,
        )

    return OpticalAbsorptionDataset(
        wavelength_nm=WAVELENGTHS_NM,
        absorption_coefficient_m_inv=_synthetic_alpha(),
        sn_fraction=0.0,
        metadata=metadata,
        **kwargs,
    )


def test_vector_prediction_matches_reference_model():
    parameters = _true_parameters()

    predicted = predict_gesn_near_edge_absorption_m_inv(
        WAVELENGTHS_NM,
        sn_fraction=0.0,
        parameters=parameters,
    )

    material = make_gesn(0.0)
    model = GeSnNearEdgeReferenceModel(
        parameters=parameters
    )

    expected = np.array(
        [
            model.evaluate(
                material,
                wavelength_nm=float(wavelength_nm),
            ).absorption_coefficient_m_inv
            for wavelength_nm in WAVELENGTHS_NM
        ]
    )

    assert predicted.tolist() == pytest.approx(
        expected.tolist()
    )


def test_vector_prediction_is_read_only():
    predicted = predict_gesn_near_edge_absorption_m_inv(
        WAVELENGTHS_NM,
        sn_fraction=0.0,
        parameters=_true_parameters(),
    )

    assert not predicted.flags.writeable

    with pytest.raises(ValueError):
        predicted[0] = 0.0


@pytest.mark.parametrize(
    "wavelengths",
    [
        [],
        [[1500.0, 1600.0]],
        [0.0, 1600.0],
        [-1500.0, 1600.0],
        [1500.0, float("nan")],
        [1500.0, float("inf")],
    ],
)
def test_prediction_rejects_invalid_wavelength_vectors(
    wavelengths,
):
    with pytest.raises(ValueError):
        predict_gesn_near_edge_absorption_m_inv(
            wavelengths,
            sn_fraction=0.0,
            parameters=_true_parameters(),
        )


@pytest.mark.parametrize(
    "sn_fraction",
    [
        -0.01,
        1.01,
        float("nan"),
        float("inf"),
    ],
)
def test_prediction_rejects_invalid_sn_fraction(
    sn_fraction: float,
):
    with pytest.raises(ValueError):
        predict_gesn_near_edge_absorption_m_inv(
            WAVELENGTHS_NM,
            sn_fraction=sn_fraction,
            parameters=_true_parameters(),
        )


def test_prediction_requires_near_edge_parameter_set():
    with pytest.raises(TypeError, match="GeSnNearEdgeParameterSet"):
        predict_gesn_near_edge_absorption_m_inv(
            WAVELENGTHS_NM,
            sn_fraction=0.0,
            parameters={},  # type: ignore[arg-type]
        )


def test_unweighted_fit_recovers_known_parameters():
    result = fit_gesn_near_edge_absorption(
        _dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name="synthetic-fit-v1",
    )

    assert result.numerical_result.success is True

    assert (
        result.fitted_parameter_set.direct_prefactor_A
        == pytest.approx(4.40e6, rel=2.0e-5)
    )
    assert (
        result.fitted_parameter_set.urbach_energy_eV
        == pytest.approx(0.0135, rel=2.0e-5)
    )

    assert result.objective.weighted is False
    assert (
        result.objective.root_mean_square_error
        == pytest.approx(0.0, abs=1.0e-2)
    )


def test_weighted_fit_uses_dataset_uncertainty():
    result = fit_gesn_near_edge_absorption(
        _dataset(uncertainty=True),
        _fit_parameter_set(),
        fitted_parameter_set_name="synthetic-weighted-fit-v1",
    )

    assert result.weighted is True

    assert (
        result.fitted_parameter_set.direct_prefactor_A
        == pytest.approx(4.40e6, rel=2.0e-5)
    )
    assert (
        result.fitted_parameter_set.urbach_energy_eV
        == pytest.approx(0.0135, rel=2.0e-5)
    )

    assert (
        result.objective.objective_residuals.tolist()
        == pytest.approx(
            result.numerical_result.objective_residuals.tolist(),
            rel=1.0e-10,
            abs=1.0e-10,
        )
    )


def test_fit_creates_new_fitted_provenance():
    result = fit_gesn_near_edge_absorption(
        _dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name="synthetic-fit-provenance-v1",
    )

    provenance = (
        result.fitted_parameter_set.provenance
    )

    assert provenance is not None

    for name in (
        "direct_prefactor_A",
        "urbach_energy_eV",
    ):
        parameter_provenance = provenance[name]

        assert (
            parameter_provenance.status
            is ParameterStatus.FITTED
        )
        assert (
            parameter_provenance.parameter_set
            == "synthetic-fit-provenance-v1"
        )
        assert (
            parameter_provenance.doi
            == "10.0000/ncmemsim.synthetic"
        )
        assert (
            parameter_provenance.reported_uncertainty
            is None
        )
        assert "dataset_hash=" in (
            parameter_provenance.notes or ""
        )
        assert "not been promoted to CALIBRATED" in (
            parameter_provenance.notes or ""
        )


def test_fit_does_not_claim_calibrated_status():
    result = fit_gesn_near_edge_absorption(
        _dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name="synthetic-fit-status-v1",
    )

    provenance = (
        result.fitted_parameter_set.provenance
        or {}
    )

    statuses = {
        entry.status
        for entry in provenance.values()
    }

    assert ParameterStatus.FITTED in statuses
    assert ParameterStatus.CALIBRATED not in statuses


def test_fit_does_not_modify_tran_reference_parameter_set():
    before = (
        TRAN_2016_NEAR_EDGE_PARAMETERS.direct_prefactor_A,
        TRAN_2016_NEAR_EDGE_PARAMETERS.urbach_energy_eV,
        TRAN_2016_NEAR_EDGE_PARAMETERS.name,
        TRAN_2016_NEAR_EDGE_PARAMETERS.provenance,
    )

    result = fit_gesn_near_edge_absorption(
        _dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name="synthetic-independent-fit-v1",
    )

    after = (
        TRAN_2016_NEAR_EDGE_PARAMETERS.direct_prefactor_A,
        TRAN_2016_NEAR_EDGE_PARAMETERS.urbach_energy_eV,
        TRAN_2016_NEAR_EDGE_PARAMETERS.name,
        TRAN_2016_NEAR_EDGE_PARAMETERS.provenance,
    )

    assert after == before
    assert (
        result.fitted_parameter_set.name
        != TRAN_2016_NEAR_EDGE_PARAMETERS.name
    )


def test_fit_rejects_reuse_of_tran_parameter_set_identity():
    with pytest.raises(ValueError, match="new identity"):
        fit_gesn_near_edge_absorption(
            _dataset(),
            _fit_parameter_set(),
            fitted_parameter_set_name=(
                TRAN_2016_PARAMETER_SET_NAME
            ),
        )


@pytest.mark.parametrize(
    "name",
    ["", "   "],
)
def test_fit_requires_nonempty_new_parameter_set_name(
    name: str,
):
    with pytest.raises(
        ValueError,
        match="fitted_parameter_set_name",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            _fit_parameter_set(),
            fitted_parameter_set_name=name,
        )


def test_fit_requires_exact_near_edge_parameter_names():
    wrong = FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=2.0e6,
                upper_bound=7.0e6,
            ),
            FitParameter(
                name="other_parameter",
                initial_value=0.01,
                lower_bound=0.005,
                upper_bound=0.030,
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="requires exactly",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            wrong,
            fitted_parameter_set_name="bad-parameter-names",
        )


def test_fit_accepts_required_parameters_in_reversed_order():
    reversed_parameters = FitParameterSet(
        parameters=(
            FitParameter(
                name="urbach_energy_eV",
                initial_value=0.01058,
                lower_bound=0.005,
                upper_bound=0.030,
            ),
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=2.0e6,
                upper_bound=7.0e6,
            ),
        )
    )

    result = fit_gesn_near_edge_absorption(
        _dataset(),
        reversed_parameters,
        fitted_parameter_set_name="reversed-order-fit-v1",
    )

    assert (
        result.fitted_parameter_set.direct_prefactor_A
        == pytest.approx(4.40e6, rel=2.0e-5)
    )
    assert (
        result.fitted_parameter_set.urbach_energy_eV
        == pytest.approx(0.0135, rel=2.0e-5)
    )


def test_fit_requires_strictly_positive_physical_bounds():
    invalid = FitParameterSet(
        parameters=(
            FitParameter(
                name="direct_prefactor_A",
                initial_value=3.68e6,
                lower_bound=0.0,
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

    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            invalid,
            fitted_parameter_set_name="invalid-bounds-fit",
        )


def test_fit_uses_numeric_dataset_temperature_when_available():
    result = fit_gesn_near_edge_absorption(
        _dataset(temperature_K=295.0),
        _fit_parameter_set(),
        fitted_parameter_set_name="temperature-fit-v1",
    )

    assert (
        result.fitted_parameter_set.temperature_K
        == pytest.approx(295.0)
    )


def test_fit_uses_reference_room_temperature_when_dataset_has_no_numeric_value():
    result = fit_gesn_near_edge_absorption(
        _dataset(temperature_K=None),
        _fit_parameter_set(),
        fitted_parameter_set_name="room-temperature-fit-v1",
    )

    assert (
        result.fitted_parameter_set.temperature_K
        == pytest.approx(
            TRAN_2016_NEAR_EDGE_PARAMETERS.temperature_K
        )
    )


def test_explicit_model_temperature_overrides_dataset_metadata():
    result = fit_gesn_near_edge_absorption(
        _dataset(temperature_K=295.0),
        _fit_parameter_set(),
        fitted_parameter_set_name="temperature-override-fit-v1",
        model_temperature_K=305.0,
    )

    assert (
        result.fitted_parameter_set.temperature_K
        == pytest.approx(305.0)
    )


@pytest.mark.parametrize(
    "temperature_K",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_fit_rejects_invalid_explicit_model_temperature(
    temperature_K: float,
):
    with pytest.raises(
        ValueError,
        match="model_temperature_K",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            _fit_parameter_set(),
            fitted_parameter_set_name="bad-temperature-fit",
            model_temperature_K=temperature_K,
        )


def test_fit_result_records_dataset_identity_and_hash():
    dataset = _dataset()

    result = fit_gesn_near_edge_absorption(
        dataset,
        _fit_parameter_set(),
        fitted_parameter_set_name="dataset-identity-fit-v1",
    )

    assert (
        result.dataset_id
        == dataset.metadata.dataset_id
    )
    assert result.dataset_hash == dataset.dataset_hash()


def test_fitted_predictions_are_read_only_and_match_objective_size():
    result = fit_gesn_near_edge_absorption(
        _dataset(),
        _fit_parameter_set(),
        fitted_parameter_set_name="prediction-result-fit-v1",
    )

    assert (
        result.predicted_absorption_m_inv.size
        == result.objective.n_points
    )
    assert (
        not result.predicted_absorption_m_inv.flags.writeable
    )

    with pytest.raises(ValueError):
        result.predicted_absorption_m_inv[0] = 0.0


def test_fit_result_to_dict_contains_reproducibility_information():
    result = fit_gesn_near_edge_absorption(
        _dataset(uncertainty=True),
        _fit_parameter_set(),
        fitted_parameter_set_name="serialized-fit-v1",
    )

    data = result.to_dict()

    assert data["schema_version"] == 1
    assert (
        data["fit_type"]
        == "gesn_near_edge_optical_absorption"
    )
    assert data["dataset_id"] == (
        "synthetic-near-edge-fit"
    )
    assert data["dataset_hash"] == (
        result.dataset_hash
    )
    assert data["weighted"] is True

    fitted = data["fitted_parameter_set"]

    assert fitted["name"] == "serialized-fit-v1"
    assert (
        fitted["provenance"]["direct_prefactor_A"]["status"]
        == ParameterStatus.FITTED.value
    )
    assert (
        fitted["provenance"]["urbach_energy_eV"]["status"]
        == ParameterStatus.FITTED.value
    )

    assert (
        data["numerical_result"][
            "parameter_specification_hash"
        ]
        == result.numerical_result.parameter_specification_hash
    )
    assert (
        data["numerical_result"][
            "solver_configuration_hash"
        ]
        == result.numerical_result.solver_configuration_hash
    )


def test_fit_failure_does_not_create_fitted_parameter_set():
    with pytest.raises(
        RuntimeError,
        match="did not converge successfully",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            _fit_parameter_set(),
            fitted_parameter_set_name="nonconverged-fit-v1",
            config=LeastSquaresConfig(
                max_nfev=1,
            ),
        )


def test_fit_requires_dataset_instance():
    with pytest.raises(
        TypeError,
        match="OpticalAbsorptionDataset",
    ):
        fit_gesn_near_edge_absorption(
            {},  # type: ignore[arg-type]
            _fit_parameter_set(),
            fitted_parameter_set_name="bad-dataset-fit",
        )


def test_fit_requires_fit_parameter_set_instance():
    with pytest.raises(
        TypeError,
        match="FitParameterSet",
    ):
        fit_gesn_near_edge_absorption(
            _dataset(),
            {},  # type: ignore[arg-type]
            fitted_parameter_set_name="bad-specification-fit",
        )
