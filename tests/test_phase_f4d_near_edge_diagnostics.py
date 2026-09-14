from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from ncmemsim import make_gesn
from ncmemsim.experimental import (
    ExperimentalDatasetMetadata,
    OpticalAbsorptionDataset,
)
from ncmemsim.fit_diagnostics import (
    FitUncertaintyDiagnostics,
)
from ncmemsim.fitting import (
    FitParameter,
    FitParameterSet,
)
from ncmemsim.materials.optics import (
    GeSnNearEdgeParameterSet,
    GeSnNearEdgeReferenceModel,
    fit_gesn_near_edge_absorption,
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


def _synthetic_alpha() -> np.ndarray:
    model = GeSnNearEdgeReferenceModel(
        parameters=_true_parameters()
    )
    material = make_gesn(0.0)

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
) -> OpticalAbsorptionDataset:
    metadata = ExperimentalDatasetMetadata(
        dataset_id="synthetic-f4d-near-edge-fit",
        source="NCMemSim synthetic F4d integration regression data",
        temperature_K=300.0,
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


def _fit(
    *,
    uncertainty: bool = False,
):
    return fit_gesn_near_edge_absorption(
        _dataset(uncertainty=uncertainty),
        _fit_parameter_set(),
        fitted_parameter_set_name=(
            "synthetic-f4d-near-edge-fit-v1"
        ),
    )


def test_near_edge_fit_attaches_uncertainty_diagnostics():
    result = _fit()

    diagnostics = result.uncertainty_diagnostics

    assert isinstance(
        diagnostics,
        FitUncertaintyDiagnostics,
    )
    assert diagnostics.parameter_names == (
        "direct_prefactor_A",
        "urbach_energy_eV",
    )
    assert diagnostics.n_observations == WAVELENGTHS_NM.size
    assert diagnostics.n_parameters == 2
    assert diagnostics.jacobian_rank == 2
    assert diagnostics.locally_identifiable is True


def test_near_edge_fit_exposes_parameter_standard_errors():
    result = _fit()

    standard_errors = result.parameter_standard_errors

    assert standard_errors is not None
    assert list(standard_errors) == [
        "direct_prefactor_A",
        "urbach_energy_eV",
    ]
    assert standard_errors["direct_prefactor_A"] >= 0.0
    assert standard_errors["urbach_energy_eV"] >= 0.0
    assert np.isfinite(
        standard_errors["direct_prefactor_A"]
    )
    assert np.isfinite(
        standard_errors["urbach_energy_eV"]
    )


def test_near_edge_fit_exposes_named_parameter_correlation():
    result = _fit()

    correlation = result.parameter_correlation

    assert correlation is not None

    names = (
        "direct_prefactor_A",
        "urbach_energy_eV",
    )

    assert tuple(correlation) == names

    for row_name in names:
        assert tuple(correlation[row_name]) == names

    assert correlation[
        "direct_prefactor_A"
    ][
        "direct_prefactor_A"
    ] == pytest.approx(1.0)

    assert correlation[
        "urbach_energy_eV"
    ][
        "urbach_energy_eV"
    ] == pytest.approx(1.0)

    assert correlation[
        "direct_prefactor_A"
    ][
        "urbach_energy_eV"
    ] == pytest.approx(
        correlation[
            "urbach_energy_eV"
        ][
            "direct_prefactor_A"
        ]
    )

    assert abs(
        correlation[
            "direct_prefactor_A"
        ][
            "urbach_energy_eV"
        ]
    ) <= 1.0


def test_weighted_near_edge_fit_also_attaches_diagnostics():
    result = _fit(uncertainty=True)

    assert result.weighted is True
    assert (
        result.uncertainty_diagnostics.n_observations
        == result.objective.n_points
    )
    assert (
        result.uncertainty_diagnostics.n_parameters
        == result.numerical_result.parameter_set.n_parameters
    )


def test_fit_standard_errors_are_not_reported_uncertainties():
    result = _fit()

    assert result.parameter_standard_errors is not None

    provenance = result.fitted_parameter_set.provenance
    assert provenance is not None

    for name in (
        "direct_prefactor_A",
        "urbach_energy_eV",
    ):
        assert (
            provenance[name].status
            is ParameterStatus.FITTED
        )
        assert (
            provenance[name].reported_uncertainty
            is None
        )
        assert provenance[name].uncertainty_unit is None


def test_fit_uncertainty_diagnostics_do_not_promote_calibration_status():
    result = _fit()

    provenance = result.fitted_parameter_set.provenance
    assert provenance is not None

    statuses = {
        provenance[name].status
        for name in (
            "direct_prefactor_A",
            "urbach_energy_eV",
        )
    }

    assert statuses == {ParameterStatus.FITTED}
    assert ParameterStatus.CALIBRATED not in statuses


def test_fit_result_serializes_uncertainty_diagnostics():
    result = _fit()

    data = result.to_dict()

    assert "uncertainty_diagnostics" in data
    assert "parameter_standard_errors" in data
    assert "parameter_correlation" in data

    diagnostics = data["uncertainty_diagnostics"]

    assert diagnostics["schema_version"] == 1
    assert (
        diagnostics["method"]
        == "linearized-local-least-squares"
    )
    assert diagnostics["parameter_names"] == [
        "direct_prefactor_A",
        "urbach_energy_eV",
    ]
    assert diagnostics["jacobian_rank"] == 2
    assert diagnostics["locally_identifiable"] is True
    assert diagnostics["covariance_available"] is True

    assert (
        data["parameter_standard_errors"]
        == result.parameter_standard_errors
    )
    assert (
        data["parameter_correlation"]
        == result.parameter_correlation
    )


def test_fit_result_rejects_non_diagnostics_object():
    result = _fit()

    with pytest.raises(
        TypeError,
        match="FitUncertaintyDiagnostics",
    ):
        replace(
            result,
            uncertainty_diagnostics={},  # type: ignore[arg-type]
        )


def test_fit_result_rejects_diagnostics_parameter_order_mismatch():
    result = _fit()
    diagnostics = result.uncertainty_diagnostics

    reversed_diagnostics = FitUncertaintyDiagnostics(
        parameter_names=tuple(
            reversed(diagnostics.parameter_names)
        ),
        n_observations=diagnostics.n_observations,
        n_parameters=diagnostics.n_parameters,
        degrees_of_freedom=diagnostics.degrees_of_freedom,
        jacobian_rank=diagnostics.jacobian_rank,
        active_bound_count=diagnostics.active_bound_count,
        scaled_singular_values=(
            diagnostics.scaled_singular_values
        ),
        scaled_condition_number=(
            diagnostics.scaled_condition_number
        ),
        residual_variance=diagnostics.residual_variance,
        covariance_matrix=diagnostics.covariance_matrix,
        standard_errors=diagnostics.standard_errors,
        correlation_matrix=diagnostics.correlation_matrix,
    )

    with pytest.raises(
        ValueError,
        match="parameter names",
    ):
        replace(
            result,
            uncertainty_diagnostics=reversed_diagnostics,
        )
