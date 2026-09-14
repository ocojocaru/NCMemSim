from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from ...experimental import OpticalAbsorptionDataset
from ...fit_diagnostics import (
    FitUncertaintyDiagnostics,
    analyze_fit_uncertainty,
)
from ...fitting import (
    DeterministicFitResult,
    FitParameterSet,
    LeastSquaresConfig,
    ObjectiveEvaluation,
    evaluate_least_squares_objective,
    least_squares_residuals,
    run_least_squares_fit,
)
from ..provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from .models import (
    direct_gap_gesn_eV,
    photon_energy_eV,
)
from .near_edge import (
    GeSnNearEdgeParameterSet,
    TRAN_2016_NEAR_EDGE_PARAMETERS,
    TRAN_2016_PARAMETER_SET_NAME,
    derive_near_edge_connection,
    near_edge_direct_absorption_m_inv,
    near_edge_urbach_absorption_m_inv,
)


GESN_NEAR_EDGE_FIT_PARAMETER_NAMES = (
    "direct_prefactor_A",
    "urbach_energy_eV",
)


def _as_wavelength_array(
    values: np.ndarray | Sequence[float],
) -> np.ndarray:
    wavelengths_nm = np.array(
        values,
        dtype=float,
        copy=True,
    )

    if wavelengths_nm.ndim != 1:
        raise ValueError(
            "wavelength_nm must be one-dimensional."
        )

    if wavelengths_nm.size == 0:
        raise ValueError(
            "wavelength_nm cannot be empty."
        )

    if not np.all(np.isfinite(wavelengths_nm)):
        raise ValueError(
            "wavelength_nm must contain only finite values."
        )

    if np.any(wavelengths_nm <= 0.0):
        raise ValueError(
            "wavelength_nm values must be strictly positive."
        )

    wavelengths_nm.setflags(write=False)
    return wavelengths_nm


def _validate_sn_fraction(sn_fraction: float) -> float:
    value = float(sn_fraction)

    if not math.isfinite(value):
        raise ValueError(
            "sn_fraction must be finite."
        )

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "sn_fraction must be between 0 and 1."
        )

    return value


def _validate_near_edge_fit_parameter_set(
    parameter_set: FitParameterSet,
) -> None:
    if not isinstance(parameter_set, FitParameterSet):
        raise TypeError(
            "parameter_set must be a FitParameterSet instance."
        )

    expected = set(GESN_NEAR_EDGE_FIT_PARAMETER_NAMES)
    actual = set(parameter_set.names)

    if (
        parameter_set.n_parameters != len(expected)
        or actual != expected
    ):
        raise ValueError(
            "GeSn near-edge fitting requires exactly the parameters "
            "'direct_prefactor_A' and 'urbach_energy_eV'."
        )

    for parameter in parameter_set.parameters:
        if parameter.lower_bound <= 0.0:
            raise ValueError(
                "GeSn near-edge fit-parameter bounds must remain "
                "strictly positive."
            )


def predict_gesn_near_edge_absorption_m_inv(
    wavelength_nm: np.ndarray | Sequence[float],
    *,
    sn_fraction: float,
    parameters: GeSnNearEdgeParameterSet,
) -> np.ndarray:
    """
    Evaluate the GeSn direct/Urbach near-edge model for a wavelength vector.

    This helper evaluates the same functional branches used by
    ``GeSnNearEdgeReferenceModel`` without assigning calibration status.
    It is intended for fitting workflows where the composition is already
    represented explicitly by the experimental dataset.
    """

    if not isinstance(parameters, GeSnNearEdgeParameterSet):
        raise TypeError(
            "parameters must be a GeSnNearEdgeParameterSet instance."
        )

    wavelengths_nm = _as_wavelength_array(
        wavelength_nm
    )
    sn_fraction = _validate_sn_fraction(
        sn_fraction
    )

    direct_gap_eV = direct_gap_gesn_eV(
        sn_fraction
    )

    if (
        not math.isfinite(direct_gap_eV)
        or direct_gap_eV <= 0.0
    ):
        raise ValueError(
            "The GeSn near-edge model requires a positive direct gap "
            "for the requested Sn fraction."
        )

    connection = derive_near_edge_connection(
        direct_gap_eV=direct_gap_eV,
        parameters=parameters,
    )

    predicted = np.empty(
        wavelengths_nm.size,
        dtype=float,
    )

    for index, wavelength in enumerate(
        wavelengths_nm
    ):
        energy_eV = photon_energy_eV(
            float(wavelength)
        )

        if (
            energy_eV
            >= connection.connection_energy_eV
        ):
            predicted[index] = (
                near_edge_direct_absorption_m_inv(
                    photon_energy_eV=energy_eV,
                    direct_gap_eV=direct_gap_eV,
                    parameters=parameters,
                )
            )
        else:
            predicted[index] = (
                near_edge_urbach_absorption_m_inv(
                    photon_energy_eV=energy_eV,
                    direct_gap_eV=direct_gap_eV,
                    parameters=parameters,
                )
            )

    if not np.all(np.isfinite(predicted)):
        raise ValueError(
            "GeSn near-edge model produced non-finite absorption values."
        )

    if np.any(predicted < 0.0):
        raise ValueError(
            "GeSn near-edge model produced negative absorption values."
        )

    predicted.setflags(write=False)
    return predicted


def _parameter_set_to_dict(
    parameters: GeSnNearEdgeParameterSet,
) -> dict[str, Any]:
    provenance = parameters.provenance or {}

    return {
        "name": parameters.name,
        "direct_prefactor_A": (
            parameters.direct_prefactor_A
        ),
        "urbach_energy_eV": (
            parameters.urbach_energy_eV
        ),
        "temperature_K": parameters.temperature_K,
        "provenance": {
            key: value.to_dict()
            for key, value in provenance.items()
        },
    }


@dataclass(frozen=True)
class GeSnNearEdgeFitResult:
    """
    Successful GeSn near-edge optical fit.

    ``FITTED`` here means numerically optimized against the identified
    experimental dataset. It does not imply independent validation or
    ``CALIBRATED`` status.
    """

    dataset_id: str
    dataset_hash: str
    fitted_parameter_set: GeSnNearEdgeParameterSet
    numerical_result: DeterministicFitResult
    objective: ObjectiveEvaluation
    uncertainty_diagnostics: FitUncertaintyDiagnostics
    predicted_absorption_m_inv: np.ndarray

    def __post_init__(self) -> None:
        dataset_id = self.dataset_id.strip()
        if not dataset_id:
            raise ValueError(
                "dataset_id cannot be empty."
            )

        dataset_hash = self.dataset_hash.strip()
        if not dataset_hash:
            raise ValueError(
                "dataset_hash cannot be empty."
            )

        if not isinstance(
            self.fitted_parameter_set,
            GeSnNearEdgeParameterSet,
        ):
            raise TypeError(
                "fitted_parameter_set must be a "
                "GeSnNearEdgeParameterSet instance."
            )

        if not isinstance(
            self.numerical_result,
            DeterministicFitResult,
        ):
            raise TypeError(
                "numerical_result must be a "
                "DeterministicFitResult instance."
            )

        if not self.numerical_result.success:
            raise ValueError(
                "GeSnNearEdgeFitResult requires a successful "
                "numerical fit."
            )

        if not isinstance(
            self.objective,
            ObjectiveEvaluation,
        ):
            raise TypeError(
                "objective must be an ObjectiveEvaluation instance."
            )

        if not isinstance(
            self.uncertainty_diagnostics,
            FitUncertaintyDiagnostics,
        ):
            raise TypeError(
                "uncertainty_diagnostics must be a "
                "FitUncertaintyDiagnostics instance."
            )

        diagnostics = self.uncertainty_diagnostics

        if (
            diagnostics.parameter_names
            != self.numerical_result.parameter_set.names
        ):
            raise ValueError(
                "uncertainty_diagnostics parameter names must match "
                "the numerical fit parameter order."
            )

        if diagnostics.n_observations != self.objective.n_points:
            raise ValueError(
                "uncertainty_diagnostics observation count must match "
                "the objective data-point count."
            )

        if (
            diagnostics.n_parameters
            != self.numerical_result.parameter_set.n_parameters
        ):
            raise ValueError(
                "uncertainty_diagnostics parameter count must match "
                "the numerical fit."
            )

        predicted = np.array(
            self.predicted_absorption_m_inv,
            dtype=float,
            copy=True,
        )

        if predicted.ndim != 1:
            raise ValueError(
                "predicted_absorption_m_inv must be one-dimensional."
            )

        if predicted.size != self.objective.n_points:
            raise ValueError(
                "predicted_absorption_m_inv must contain one value "
                "per objective data point."
            )

        if not np.all(np.isfinite(predicted)):
            raise ValueError(
                "predicted_absorption_m_inv must contain only "
                "finite values."
            )

        if np.any(predicted < 0.0):
            raise ValueError(
                "predicted_absorption_m_inv values must be "
                "non-negative."
            )

        provenance = (
            self.fitted_parameter_set.provenance
            or {}
        )

        for name in GESN_NEAR_EDGE_FIT_PARAMETER_NAMES:
            if name not in provenance:
                raise ValueError(
                    f"Missing provenance for fitted parameter {name!r}."
                )

            if (
                provenance[name].status
                is not ParameterStatus.FITTED
            ):
                raise ValueError(
                    "Fitted near-edge parameters must carry "
                    "ParameterStatus.FITTED provenance."
                )

        predicted.setflags(write=False)

        object.__setattr__(
            self,
            "dataset_id",
            dataset_id,
        )
        object.__setattr__(
            self,
            "dataset_hash",
            dataset_hash,
        )
        object.__setattr__(
            self,
            "predicted_absorption_m_inv",
            predicted,
        )

    @property
    def weighted(self) -> bool:
        return self.objective.weighted

    @property
    def fitted_parameters(self) -> dict[str, float]:
        return {
            "direct_prefactor_A": (
                self.fitted_parameter_set.direct_prefactor_A
            ),
            "urbach_energy_eV": (
                self.fitted_parameter_set.urbach_energy_eV
            ),
        }

    @property
    def parameter_standard_errors(
        self,
    ) -> dict[str, float] | None:
        return (
            self.uncertainty_diagnostics.parameter_standard_errors
        )

    @property
    def parameter_correlation(
        self,
    ) -> dict[str, dict[str, float]] | None:
        matrix = (
            self.uncertainty_diagnostics.correlation_matrix
        )

        if matrix is None:
            return None

        names = self.uncertainty_diagnostics.parameter_names

        return {
            row_name: {
                column_name: float(matrix[row_index, column_index])
                for column_index, column_name in enumerate(names)
            }
            for row_index, row_name in enumerate(names)
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "fit_type": "gesn_near_edge_optical_absorption",
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "weighted": self.weighted,
            "fitted_parameter_set": (
                _parameter_set_to_dict(
                    self.fitted_parameter_set
                )
            ),
            "numerical_result": (
                self.numerical_result.to_dict()
            ),
            "objective": self.objective.to_dict(),
            "uncertainty_diagnostics": (
                self.uncertainty_diagnostics.to_dict()
            ),
            "parameter_standard_errors": (
                self.parameter_standard_errors
            ),
            "parameter_correlation": (
                self.parameter_correlation
            ),
            "predicted_absorption_m_inv": (
                self.predicted_absorption_m_inv.tolist()
            ),
        }


def fit_gesn_near_edge_absorption(
    dataset: OpticalAbsorptionDataset,
    parameter_set: FitParameterSet,
    *,
    fitted_parameter_set_name: str,
    config: LeastSquaresConfig | None = None,
    model_temperature_K: float | None = None,
) -> GeSnNearEdgeFitResult:
    """
    Fit the GeSn near-edge direct prefactor and Urbach energy.

    Only ``direct_prefactor_A`` and ``urbach_energy_eV`` are optimized.
    The existing NCMemSim direct-gap composition relation, including its
    bowing parameterization, remains fixed.

    Experimental uncertainty is used automatically when present in the
    dataset. A successful optimization produces a new parameter set whose
    two optimized parameters carry ``ParameterStatus.FITTED`` provenance.

    ``FITTED`` denotes numerical fitting only. This function never assigns
    ``ParameterStatus.CALIBRATED``.

    ``model_temperature_K`` is model metadata rather than an optimized
    parameter. When omitted, an explicitly reported dataset temperature is
    used if available; otherwise the NCMemSim 300 K room-temperature
    reference value is retained.
    """

    if not isinstance(
        dataset,
        OpticalAbsorptionDataset,
    ):
        raise TypeError(
            "dataset must be an OpticalAbsorptionDataset instance."
        )

    _validate_near_edge_fit_parameter_set(
        parameter_set
    )

    fitted_name = fitted_parameter_set_name.strip()

    if not fitted_name:
        raise ValueError(
            "fitted_parameter_set_name cannot be empty."
        )

    if fitted_name == TRAN_2016_PARAMETER_SET_NAME:
        raise ValueError(
            "A fitted parameter set must use a new identity and cannot "
            "reuse the Tran 2016 reference parameter-set name."
        )

    if model_temperature_K is None:
        if dataset.metadata.temperature_K is not None:
            resolved_temperature_K = (
                dataset.metadata.temperature_K
            )
        else:
            resolved_temperature_K = (
                TRAN_2016_NEAR_EDGE_PARAMETERS.temperature_K
            )
    else:
        resolved_temperature_K = float(
            model_temperature_K
        )

    if (
        not math.isfinite(resolved_temperature_K)
        or resolved_temperature_K <= 0.0
    ):
        raise ValueError(
            "model_temperature_K must be finite and positive."
        )

    def parameter_values_to_model(
        values: np.ndarray,
    ) -> GeSnNearEdgeParameterSet:
        mapped = parameter_set.values_to_dict(
            values
        )

        return GeSnNearEdgeParameterSet(
            name="ncmemsim-near-edge-fit-working-set",
            direct_prefactor_A=(
                mapped["direct_prefactor_A"]
            ),
            urbach_energy_eV=(
                mapped["urbach_energy_eV"]
            ),
            temperature_K=resolved_temperature_K,
        )

    def residual_function(
        values: np.ndarray,
    ) -> np.ndarray:
        trial_parameters = (
            parameter_values_to_model(values)
        )

        predicted = (
            predict_gesn_near_edge_absorption_m_inv(
                dataset.wavelength_nm,
                sn_fraction=dataset.sn_fraction,
                parameters=trial_parameters,
            )
        )

        return least_squares_residuals(
            observed=(
                dataset.absorption_coefficient_m_inv
            ),
            predicted=predicted,
            uncertainty=(
                dataset.absorption_uncertainty_m_inv
            ),
        )

    numerical_result = run_least_squares_fit(
        parameter_set,
        residual_function,
        config=config,
    )

    if not numerical_result.success:
        raise RuntimeError(
            "GeSn near-edge fitting did not converge successfully: "
            f"status={numerical_result.status}; "
            f"message={numerical_result.message}"
        )

    uncertainty_diagnostics = analyze_fit_uncertainty(
        numerical_result
    )

    fitted_values = (
        numerical_result.fitted_parameters
    )
    dataset_hash = dataset.dataset_hash()

    provenance_source = (
        "NCMemSim deterministic least-squares fit to "
        f"experimental dataset '{dataset.metadata.dataset_id}': "
        f"{dataset.metadata.source}"
    )

    common_notes = (
        "Numerically optimized by NCMemSim against optical absorption "
        "coefficient data. "
        f"dataset_hash={dataset_hash}; "
        "parameter_specification_hash="
        f"{numerical_result.parameter_specification_hash}; "
        "solver_configuration_hash="
        f"{numerical_result.solver_configuration_hash}. "
        "FITTED denotes numerical fitting only; this parameter has not "
        "been promoted to CALIBRATED status."
    )

    fitted_provenance = {
        "direct_prefactor_A": ParameterProvenance(
            source=provenance_source,
            status=ParameterStatus.FITTED,
            doi=dataset.metadata.doi,
            notes=(
                "Direct near-edge absorption prefactor. "
                + common_notes
            ),
            parameter_set=fitted_name,
        ),
        "urbach_energy_eV": ParameterProvenance(
            source=provenance_source,
            status=ParameterStatus.FITTED,
            doi=dataset.metadata.doi,
            notes=(
                "Urbach energy. "
                + common_notes
            ),
            parameter_set=fitted_name,
        ),
    }

    fitted_parameter_set = (
        GeSnNearEdgeParameterSet(
            name=fitted_name,
            direct_prefactor_A=(
                fitted_values[
                    "direct_prefactor_A"
                ]
            ),
            urbach_energy_eV=(
                fitted_values[
                    "urbach_energy_eV"
                ]
            ),
            temperature_K=(
                resolved_temperature_K
            ),
            provenance=fitted_provenance,
        )
    )

    predicted = (
        predict_gesn_near_edge_absorption_m_inv(
            dataset.wavelength_nm,
            sn_fraction=dataset.sn_fraction,
            parameters=fitted_parameter_set,
        )
    )

    objective = evaluate_least_squares_objective(
        observed=(
            dataset.absorption_coefficient_m_inv
        ),
        predicted=predicted,
        uncertainty=(
            dataset.absorption_uncertainty_m_inv
        ),
    )

    if not np.allclose(
        objective.objective_residuals,
        numerical_result.objective_residuals,
        rtol=1.0e-10,
        atol=1.0e-12,
    ):
        raise RuntimeError(
            "Final fitted-model residuals are inconsistent with the "
            "numerical optimizer result."
        )

    return GeSnNearEdgeFitResult(
        dataset_id=dataset.metadata.dataset_id,
        dataset_hash=dataset_hash,
        fitted_parameter_set=fitted_parameter_set,
        numerical_result=numerical_result,
        objective=objective,
        uncertainty_diagnostics=uncertainty_diagnostics,
        predicted_absorption_m_inv=predicted,
    )


__all__ = [
    "GESN_NEAR_EDGE_FIT_PARAMETER_NAMES",
    "GeSnNearEdgeFitResult",
    "fit_gesn_near_edge_absorption",
    "predict_gesn_near_edge_absorption_m_inv",
]
