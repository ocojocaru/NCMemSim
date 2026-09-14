from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np

from ...calibration import (
    CalibrationCriteria,
    CalibrationQualification,
    qualify_calibration,
)
from ...experimental import OpticalAbsorptionDataset
from ...fitting import evaluate_least_squares_objective
from ..provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from .near_edge import (
    GeSnNearEdgeParameterSet,
    TRAN_2016_PARAMETER_SET_NAME,
)
from .near_edge_fit import (
    GeSnNearEdgeFitResult,
    predict_gesn_near_edge_absorption_m_inv,
)


def _required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    return normalized


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
class GeSnNearEdgeCalibrationResult:
    """
    Result of GeSn near-edge calibration qualification.

    The result is always returned so failed qualification remains auditable.
    ``calibrated_parameter_set`` is created only when every configured
    qualification criterion passes.

    Fit uncertainty remains stored in the qualification diagnostics. It is
    not copied into ``ParameterProvenance.reported_uncertainty``.
    """

    fitted_parameter_set_name: str
    validation_dataset_id: str
    validation_dataset_hash: str
    qualification: CalibrationQualification
    predicted_absorption_m_inv: np.ndarray
    calibrated_parameter_set: GeSnNearEdgeParameterSet | None = None

    def __post_init__(self) -> None:
        fitted_name = _required_text(
            self.fitted_parameter_set_name,
            field_name="fitted_parameter_set_name",
        )
        validation_dataset_id = _required_text(
            self.validation_dataset_id,
            field_name="validation_dataset_id",
        )
        validation_dataset_hash = _required_text(
            self.validation_dataset_hash,
            field_name="validation_dataset_hash",
        )

        if not isinstance(
            self.qualification,
            CalibrationQualification,
        ):
            raise TypeError(
                "qualification must be a "
                "CalibrationQualification instance."
            )

        if (
            self.qualification.validation_dataset_hash
            != validation_dataset_hash
        ):
            raise ValueError(
                "validation_dataset_hash must match the "
                "qualification validation dataset hash."
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

        if (
            predicted.size
            != self.qualification.validation_objective.n_points
        ):
            raise ValueError(
                "predicted_absorption_m_inv must contain one value "
                "per validation data point."
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

        calibrated = self.calibrated_parameter_set
        eligible = self.qualification.eligible_for_calibration

        if eligible and calibrated is None:
            raise ValueError(
                "An eligible qualification must provide a calibrated "
                "parameter set."
            )

        if not eligible and calibrated is not None:
            raise ValueError(
                "A failed qualification cannot provide a calibrated "
                "parameter set."
            )

        if calibrated is not None:
            if not isinstance(
                calibrated,
                GeSnNearEdgeParameterSet,
            ):
                raise TypeError(
                    "calibrated_parameter_set must be None or a "
                    "GeSnNearEdgeParameterSet instance."
                )

            if calibrated.name == fitted_name:
                raise ValueError(
                    "The calibrated parameter set must use a new "
                    "identity."
                )

            provenance = calibrated.provenance or {}

            for name in (
                "direct_prefactor_A",
                "urbach_energy_eV",
            ):
                if name not in provenance:
                    raise ValueError(
                        f"Missing calibrated provenance for {name!r}."
                    )

                if (
                    provenance[name].status
                    is not ParameterStatus.CALIBRATED
                ):
                    raise ValueError(
                        "Calibrated near-edge parameters must carry "
                        "ParameterStatus.CALIBRATED provenance."
                    )

                if (
                    provenance[name].reported_uncertainty
                    is not None
                ):
                    raise ValueError(
                        "Fit-derived uncertainty must not be stored as "
                        "reported_uncertainty."
                    )

        predicted.setflags(write=False)

        object.__setattr__(
            self,
            "fitted_parameter_set_name",
            fitted_name,
        )
        object.__setattr__(
            self,
            "validation_dataset_id",
            validation_dataset_id,
        )
        object.__setattr__(
            self,
            "validation_dataset_hash",
            validation_dataset_hash,
        )
        object.__setattr__(
            self,
            "predicted_absorption_m_inv",
            predicted,
        )

    @property
    def calibrated(self) -> bool:
        return self.calibrated_parameter_set is not None

    @property
    def failed_criteria(self) -> tuple[str, ...]:
        return self.qualification.failed_criteria

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "calibration_type": (
                "gesn_near_edge_optical_absorption"
            ),
            "calibrated": self.calibrated,
            "fitted_parameter_set_name": (
                self.fitted_parameter_set_name
            ),
            "validation_dataset_id": (
                self.validation_dataset_id
            ),
            "validation_dataset_hash": (
                self.validation_dataset_hash
            ),
            "qualification": self.qualification.to_dict(),
            "qualification_hash": (
                self.qualification.qualification_hash()
            ),
            "predicted_absorption_m_inv": (
                self.predicted_absorption_m_inv.tolist()
            ),
            "calibrated_parameter_set": (
                None
                if self.calibrated_parameter_set is None
                else _parameter_set_to_dict(
                    self.calibrated_parameter_set
                )
            ),
        }


def qualify_gesn_near_edge_fit(
    fit_result: GeSnNearEdgeFitResult,
    validation_dataset: OpticalAbsorptionDataset,
    *,
    criteria: CalibrationCriteria,
    calibrated_parameter_set_name: str,
) -> GeSnNearEdgeCalibrationResult:
    """
    Validate a fitted GeSn near-edge parameter set and conditionally promote it.

    The validation dataset is evaluated with the already fitted parameter
    values; no parameters are re-optimized on validation data.

    A new ``GeSnNearEdgeParameterSet`` with
    ``ParameterStatus.CALIBRATED`` provenance is created only when every
    configured qualification criterion passes. The original fitted parameter
    set remains unchanged.

    The generic calibration framework controls whether the validation dataset
    must be distinct from the fitting dataset. That requirement is enabled by
    default.

    Model-based fit standard errors remain in uncertainty diagnostics and are
    deliberately not copied into ``reported_uncertainty``.
    """

    if not isinstance(
        fit_result,
        GeSnNearEdgeFitResult,
    ):
        raise TypeError(
            "fit_result must be a GeSnNearEdgeFitResult instance."
        )

    if not isinstance(
        validation_dataset,
        OpticalAbsorptionDataset,
    ):
        raise TypeError(
            "validation_dataset must be an "
            "OpticalAbsorptionDataset instance."
        )

    if not isinstance(
        criteria,
        CalibrationCriteria,
    ):
        raise TypeError(
            "criteria must be a CalibrationCriteria instance."
        )

    calibrated_name = _required_text(
        calibrated_parameter_set_name,
        field_name="calibrated_parameter_set_name",
    )

    fitted_parameters = fit_result.fitted_parameter_set

    if calibrated_name == fitted_parameters.name:
        raise ValueError(
            "The calibrated parameter set must use a new identity."
        )

    if calibrated_name == TRAN_2016_PARAMETER_SET_NAME:
        raise ValueError(
            "The calibrated parameter set cannot reuse the Tran 2016 "
            "reference parameter-set identity."
        )

    validation_hash = (
        validation_dataset.dataset_hash()
    )

    predicted = (
        predict_gesn_near_edge_absorption_m_inv(
            validation_dataset.wavelength_nm,
            sn_fraction=validation_dataset.sn_fraction,
            parameters=fitted_parameters,
        )
    )

    validation_objective = (
        evaluate_least_squares_objective(
            observed=(
                validation_dataset.absorption_coefficient_m_inv
            ),
            predicted=predicted,
            uncertainty=(
                validation_dataset.absorption_uncertainty_m_inv
            ),
        )
    )

    qualification = qualify_calibration(
        fit_result.numerical_result,
        fit_result.uncertainty_diagnostics,
        fit_dataset_hash=fit_result.dataset_hash,
        validation_dataset_hash=validation_hash,
        validation_objective=validation_objective,
        criteria=criteria,
    )

    calibrated_parameter_set: (
        GeSnNearEdgeParameterSet | None
    ) = None

    if qualification.eligible_for_calibration:
        qualification_hash = (
            qualification.qualification_hash()
        )

        provenance_source = (
            "NCMemSim calibration qualification of fitted GeSn "
            f"near-edge parameter set '{fitted_parameters.name}' "
            f"using validation dataset "
            f"'{validation_dataset.metadata.dataset_id}': "
            f"{validation_dataset.metadata.source}"
        )

        common_notes = (
            "Promoted from FITTED to CALIBRATED only after all "
            "configured calibration-qualification criteria passed. "
            f"fit_dataset_hash={fit_result.dataset_hash}; "
            f"validation_dataset_hash={validation_hash}; "
            f"qualification_hash={qualification_hash}; "
            f"parent_parameter_set={fitted_parameters.name}. "
            "Model-based fit uncertainty remains in the fit diagnostics "
            "and is not stored as reported_uncertainty."
        )

        calibrated_provenance = {
            "direct_prefactor_A": ParameterProvenance(
                source=provenance_source,
                status=ParameterStatus.CALIBRATED,
                doi=validation_dataset.metadata.doi,
                notes=(
                    "Direct near-edge absorption prefactor. "
                    + common_notes
                ),
                parameter_set=calibrated_name,
            ),
            "urbach_energy_eV": ParameterProvenance(
                source=provenance_source,
                status=ParameterStatus.CALIBRATED,
                doi=validation_dataset.metadata.doi,
                notes=(
                    "Urbach energy. "
                    + common_notes
                ),
                parameter_set=calibrated_name,
            ),
        }

        calibrated_parameter_set = (
            GeSnNearEdgeParameterSet(
                name=calibrated_name,
                direct_prefactor_A=(
                    fitted_parameters.direct_prefactor_A
                ),
                urbach_energy_eV=(
                    fitted_parameters.urbach_energy_eV
                ),
                temperature_K=(
                    fitted_parameters.temperature_K
                ),
                provenance=calibrated_provenance,
            )
        )

    return GeSnNearEdgeCalibrationResult(
        fitted_parameter_set_name=(
            fitted_parameters.name
        ),
        validation_dataset_id=(
            validation_dataset.metadata.dataset_id
        ),
        validation_dataset_hash=validation_hash,
        qualification=qualification,
        predicted_absorption_m_inv=predicted,
        calibrated_parameter_set=(
            calibrated_parameter_set
        ),
    )


__all__ = [
    "GeSnNearEdgeCalibrationResult",
    "qualify_gesn_near_edge_fit",
]
