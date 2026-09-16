from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from typing import Any

import numpy as np

from .calibration import (
    CalibrationCriteria,
    CalibrationCriterionResult,
    CalibrationQualification,
    qualify_calibration,
)
from .device_calibration import DeviceFitTarget
from .experimental import DeviceObservableDataset
from .fitting import evaluate_least_squares_objective
from .hashing import canonical_hash
from .photo import PhotoTransitionConfig
from .photo_program_fit import (
    DevicePhotoMultiConditionFitResult,
    ElectroOpticalProgramTimeFitProtocol,
    ElectroOpticalProgramTimePrediction,
    _multi_condition_nonoptical_manifest,
    _require_photo_program_time_dataset,
    _validate_photo_protocol_conditions,
    predict_electro_optical_delta_vfb_vs_programming_time,
)
from .simulator import Simulator


def _required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")
    return normalized


def _training_dataset_collection_manifest(
    fit_result: DevicePhotoMultiConditionFitResult,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dataset_hashes": list(fit_result.dataset_hashes),
    }


def _training_dataset_collection_hash(
    fit_result: DevicePhotoMultiConditionFitResult,
) -> str:
    return canonical_hash(
        _training_dataset_collection_manifest(fit_result)
    )


def _qualify_training_collection(
    fit_result: DevicePhotoMultiConditionFitResult,
    *,
    validation_dataset_hash: str,
    validation_objective,
    criteria: CalibrationCriteria,
) -> CalibrationQualification:
    """
    Apply the generic qualification framework to a multi-dataset fit.

    ``CalibrationQualification`` stores one fit-dataset hash. For the F4i4
    joint fit this adapter supplies a deterministic hash of the ordered
    training-dataset hash collection. The generic distinct-dataset criterion
    is then refined so a validation dataset fails that criterion whenever its
    own hash is any member of the training collection.
    """

    collection_hash = _training_dataset_collection_hash(
        fit_result
    )
    qualification = qualify_calibration(
        fit_result.numerical_result,
        fit_result.uncertainty_diagnostics,
        fit_dataset_hash=collection_hash,
        validation_dataset_hash=validation_dataset_hash,
        validation_objective=validation_objective,
        criteria=criteria,
    )

    if not criteria.require_distinct_validation_dataset:
        return qualification

    validation_is_distinct = (
        validation_dataset_hash
        not in fit_result.dataset_hashes
    )

    patched_results = []
    for criterion in qualification.criterion_results:
        if criterion.name != "distinct_validation_dataset":
            patched_results.append(criterion)
            continue

        patched_results.append(
            CalibrationCriterionResult(
                name="distinct_validation_dataset",
                passed=validation_is_distinct,
                observed_value=validation_is_distinct,
                comparison="is_true",
                threshold=True,
                notes=(
                    "Validation dataset hash must differ from every "
                    "dataset hash used by the joint training fit."
                ),
            )
        )

    return CalibrationQualification(
        fit_dataset_hash=collection_hash,
        validation_dataset_hash=validation_dataset_hash,
        criteria=criteria,
        validation_objective=validation_objective,
        uncertainty_diagnostics=(
            fit_result.uncertainty_diagnostics
        ),
        criterion_results=tuple(patched_results),
    )


@dataclass(frozen=True)
class CalibratedPhotoCaptureEfficiency:
    """
    Auditable calibrated device-parameter record.

    ``PhotoTransitionConfig`` intentionally remains a compact simulator
    configuration without embedded provenance. This record carries the
    calibration status and hashes that qualify the device-level
    ``photo_capture_efficiency`` value.
    """

    parameter_name: str
    value: float
    source: str
    training_dataset_collection_hash: str
    validation_dataset_hash: str
    validation_protocol_hash: str
    qualification_hash: str
    status: str = "CALIBRATED"

    def __post_init__(self) -> None:
        parameter_name = _required_text(
            self.parameter_name,
            field_name="parameter_name",
        )
        if parameter_name != "photo_capture_efficiency":
            raise ValueError(
                "CalibratedPhotoCaptureEfficiency requires "
                "parameter_name='photo_capture_efficiency'."
            )

        value = float(self.value)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(
                "value must be finite and lie in [0, 1]."
            )

        source = _required_text(
            self.source,
            field_name="source",
        )
        training_hash = _required_text(
            self.training_dataset_collection_hash,
            field_name="training_dataset_collection_hash",
        )
        validation_hash = _required_text(
            self.validation_dataset_hash,
            field_name="validation_dataset_hash",
        )
        protocol_hash = _required_text(
            self.validation_protocol_hash,
            field_name="validation_protocol_hash",
        )
        qualification_hash = _required_text(
            self.qualification_hash,
            field_name="qualification_hash",
        )

        if self.status != "CALIBRATED":
            raise ValueError(
                "CalibratedPhotoCaptureEfficiency status must "
                "be 'CALIBRATED'."
            )

        object.__setattr__(
            self,
            "parameter_name",
            parameter_name,
        )
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "source", source)
        object.__setattr__(
            self,
            "training_dataset_collection_hash",
            training_hash,
        )
        object.__setattr__(
            self,
            "validation_dataset_hash",
            validation_hash,
        )
        object.__setattr__(
            self,
            "validation_protocol_hash",
            protocol_hash,
        )
        object.__setattr__(
            self,
            "qualification_hash",
            qualification_hash,
        )

    @property
    def target(self) -> DeviceFitTarget:
        return DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "parameter_name": self.parameter_name,
            "target": self.target.value,
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "training_dataset_collection_hash": (
                self.training_dataset_collection_hash
            ),
            "validation_dataset_hash": (
                self.validation_dataset_hash
            ),
            "validation_protocol_hash": (
                self.validation_protocol_hash
            ),
            "qualification_hash": self.qualification_hash,
            "reported_uncertainty": None,
            "uncertainty_note": (
                "Model-based fit uncertainty remains in the "
                "qualification diagnostics and is not copied into "
                "reported experimental uncertainty."
            ),
        }


@dataclass(frozen=True)
class DevicePhotoCalibrationResult:
    """
    Independent-validation result for a fitted photo-capture efficiency.

    A calibrated parameter/configuration is created only when every configured
    criterion passes. Failed qualification remains auditable and returns
    ``NOT_CALIBRATED`` without changing the original fitted result.
    """

    training_dataset_ids: tuple[str, ...]
    training_dataset_hashes: tuple[str, ...]
    training_dataset_collection_hash: str
    validation_dataset_id: str
    validation_dataset_hash: str
    validation_protocol: ElectroOpticalProgramTimeFitProtocol
    qualification: CalibrationQualification
    prediction: ElectroOpticalProgramTimePrediction
    calibrated_parameter: (
        CalibratedPhotoCaptureEfficiency | None
    ) = None
    calibrated_photo_config: PhotoTransitionConfig | None = None

    def __post_init__(self) -> None:
        training_ids = tuple(
            _required_text(
                value,
                field_name="training_dataset_id",
            )
            for value in self.training_dataset_ids
        )
        training_hashes = tuple(
            _required_text(
                value,
                field_name="training_dataset_hash",
            )
            for value in self.training_dataset_hashes
        )

        if len(training_ids) < 2:
            raise ValueError(
                "Photo calibration requires a multi-condition "
                "training fit with at least two datasets."
            )
        if len(training_ids) != len(training_hashes):
            raise ValueError(
                "training_dataset_ids and training_dataset_hashes "
                "must have matching lengths."
            )
        if len(set(training_hashes)) != len(training_hashes):
            raise ValueError(
                "training_dataset_hashes must be unique."
            )

        collection_hash = _required_text(
            self.training_dataset_collection_hash,
            field_name="training_dataset_collection_hash",
        )
        expected_collection_hash = canonical_hash(
            {
                "schema_version": 1,
                "dataset_hashes": list(training_hashes),
            }
        )
        if collection_hash != expected_collection_hash:
            raise ValueError(
                "training_dataset_collection_hash is inconsistent "
                "with training_dataset_hashes."
            )

        validation_id = _required_text(
            self.validation_dataset_id,
            field_name="validation_dataset_id",
        )
        validation_hash = _required_text(
            self.validation_dataset_hash,
            field_name="validation_dataset_hash",
        )

        if not isinstance(
            self.validation_protocol,
            ElectroOpticalProgramTimeFitProtocol,
        ):
            raise TypeError(
                "validation_protocol must be an "
                "ElectroOpticalProgramTimeFitProtocol."
            )
        if not isinstance(
            self.qualification,
            CalibrationQualification,
        ):
            raise TypeError(
                "qualification must be a CalibrationQualification."
            )
        if not isinstance(
            self.prediction,
            ElectroOpticalProgramTimePrediction,
        ):
            raise TypeError(
                "prediction must be an "
                "ElectroOpticalProgramTimePrediction."
            )

        if self.qualification.fit_dataset_hash != collection_hash:
            raise ValueError(
                "qualification fit_dataset_hash must match the "
                "training dataset collection hash."
            )
        if (
            self.qualification.validation_dataset_hash
            != validation_hash
        ):
            raise ValueError(
                "qualification validation_dataset_hash must match "
                "the result validation dataset hash."
            )
        if (
            self.prediction.predicted_delta_vfb_V.size
            != self.qualification.validation_objective.n_points
        ):
            raise ValueError(
                "prediction must contain one value per validation "
                "objective data point."
            )

        eligible = self.qualification.eligible_for_calibration
        calibrated_parameter = self.calibrated_parameter
        calibrated_config = self.calibrated_photo_config

        if eligible:
            if calibrated_parameter is None:
                raise ValueError(
                    "Eligible photo calibration must provide a "
                    "calibrated_parameter."
                )
            if calibrated_config is None:
                raise ValueError(
                    "Eligible photo calibration must provide a "
                    "calibrated_photo_config."
                )
        else:
            if calibrated_parameter is not None:
                raise ValueError(
                    "Failed photo qualification cannot provide a "
                    "calibrated_parameter."
                )
            if calibrated_config is not None:
                raise ValueError(
                    "Failed photo qualification cannot provide a "
                    "calibrated_photo_config."
                )

        if calibrated_parameter is not None:
            if (
                calibrated_parameter.training_dataset_collection_hash
                != collection_hash
            ):
                raise ValueError(
                    "Calibrated parameter training hash is inconsistent."
                )
            if (
                calibrated_parameter.validation_dataset_hash
                != validation_hash
            ):
                raise ValueError(
                    "Calibrated parameter validation hash is inconsistent."
                )
            if (
                calibrated_parameter.validation_protocol_hash
                != self.validation_protocol.protocol_hash()
            ):
                raise ValueError(
                    "Calibrated parameter protocol hash is inconsistent."
                )
            if (
                calibrated_parameter.qualification_hash
                != self.qualification.qualification_hash()
            ):
                raise ValueError(
                    "Calibrated parameter qualification hash "
                    "is inconsistent."
                )

        if calibrated_config is not None:
            assert calibrated_parameter is not None
            if not math.isclose(
                calibrated_config.photo_capture_efficiency,
                calibrated_parameter.value,
                rel_tol=0.0,
                abs_tol=0.0,
            ):
                raise ValueError(
                    "calibrated_photo_config must contain the "
                    "calibrated photo-capture efficiency."
                )

        object.__setattr__(
            self,
            "training_dataset_ids",
            training_ids,
        )
        object.__setattr__(
            self,
            "training_dataset_hashes",
            training_hashes,
        )
        object.__setattr__(
            self,
            "training_dataset_collection_hash",
            collection_hash,
        )
        object.__setattr__(
            self,
            "validation_dataset_id",
            validation_id,
        )
        object.__setattr__(
            self,
            "validation_dataset_hash",
            validation_hash,
        )

    @property
    def calibrated(self) -> bool:
        return self.calibrated_parameter is not None

    @property
    def scientific_status(self) -> str:
        if self.calibrated:
            return "CALIBRATED"
        return "NOT_CALIBRATED"

    @property
    def failed_criteria(self) -> tuple[str, ...]:
        return self.qualification.failed_criteria

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "calibration_type": (
                "device_photo_capture_efficiency"
            ),
            "scientific_status": self.scientific_status,
            "calibrated": self.calibrated,
            "training_dataset_ids": list(
                self.training_dataset_ids
            ),
            "training_dataset_hashes": list(
                self.training_dataset_hashes
            ),
            "training_dataset_collection_hash": (
                self.training_dataset_collection_hash
            ),
            "validation_dataset_id": (
                self.validation_dataset_id
            ),
            "validation_dataset_hash": (
                self.validation_dataset_hash
            ),
            "validation_protocol": (
                self.validation_protocol.to_dict()
            ),
            "validation_protocol_hash": (
                self.validation_protocol.protocol_hash()
            ),
            "qualification": self.qualification.to_dict(),
            "qualification_hash": (
                self.qualification.qualification_hash()
            ),
            "prediction": {
                "programming_times_s": (
                    self.prediction.programming_times_s.tolist()
                ),
                "predicted_delta_vfb_V": (
                    self.prediction.predicted_delta_vfb_V.tolist()
                ),
            },
            "calibrated_parameter": (
                None
                if self.calibrated_parameter is None
                else self.calibrated_parameter.to_dict()
            ),
            "calibrated_photo_transition_config": (
                None
                if self.calibrated_photo_config is None
                else {
                    "photo_capture_efficiency": (
                        self.calibrated_photo_config
                        .photo_capture_efficiency
                    ),
                    "status": "CALIBRATED",
                }
            ),
        }


def qualify_photo_capture_efficiency_fit(
    fit_result: DevicePhotoMultiConditionFitResult,
    validation_dataset: DeviceObservableDataset,
    validation_protocol: ElectroOpticalProgramTimeFitProtocol,
    *,
    criteria: CalibrationCriteria,
) -> DevicePhotoCalibrationResult:
    """
    Qualify a fitted photo-capture efficiency on independent validation data.

    The already fitted parameter value is evaluated unchanged on the
    validation dataset. No optimization is performed in this function.

    The validation protocol must preserve the non-optical settings of the
    F4i4 multi-condition training fit. Wavelength and/or incident optical
    power may differ.

    Passing every configured criterion creates a new calibrated parameter
    record plus a separate ``PhotoTransitionConfig`` carrying the qualified
    value. The original fitted result and its context remain unchanged.
    """

    if not isinstance(
        fit_result,
        DevicePhotoMultiConditionFitResult,
    ):
        raise TypeError(
            "fit_result must be a "
            "DevicePhotoMultiConditionFitResult."
        )
    if not isinstance(
        validation_dataset,
        DeviceObservableDataset,
    ):
        raise TypeError(
            "validation_dataset must be a "
            "DeviceObservableDataset."
        )
    if not isinstance(
        validation_protocol,
        ElectroOpticalProgramTimeFitProtocol,
    ):
        raise TypeError(
            "validation_protocol must be an "
            "ElectroOpticalProgramTimeFitProtocol."
        )
    if not isinstance(criteria, CalibrationCriteria):
        raise TypeError(
            "criteria must be a CalibrationCriteria."
        )

    _require_photo_program_time_dataset(
        validation_dataset
    )
    _validate_photo_protocol_conditions(
        validation_dataset,
        validation_protocol,
    )

    reference_manifest = (
        _multi_condition_nonoptical_manifest(
            fit_result.protocols[0]
        )
    )
    validation_manifest = (
        _multi_condition_nonoptical_manifest(
            validation_protocol
        )
    )
    if canonical_hash(reference_manifest) != canonical_hash(
        validation_manifest
    ):
        raise ValueError(
            "Photo calibration validation may vary optical source "
            "conditions only; program/read voltages, program "
            "timestep, photo-transition weights, and occupancy "
            "integrator must match the training protocols."
        )

    fitted_photo_config = (
        fit_result.fitted_context.photo_config
    )
    if fitted_photo_config is None:
        raise ValueError(
            "Photo calibration requires a fitted photo_config."
        )

    fitted_values = fit_result.fitted_parameter_values
    if len(fitted_values) != 1:
        raise ValueError(
            "Photo calibration currently requires exactly one "
            "fitted parameter."
        )
    if "photo_capture_efficiency" not in fitted_values:
        raise ValueError(
            "Photo calibration requires a fitted "
            "photo_capture_efficiency parameter."
        )

    fitted_eta = float(
        fitted_values["photo_capture_efficiency"]
    )
    if not math.isclose(
        fitted_photo_config.photo_capture_efficiency,
        fitted_eta,
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise ValueError(
            "Fitted context photo_config is inconsistent with "
            "the fitted photo_capture_efficiency value."
        )

    validation_context = deepcopy(
        fit_result.fitted_context
    )
    assert validation_context.photo_config is not None

    prediction = (
        predict_electro_optical_delta_vfb_vs_programming_time(
            Simulator(
                validation_context.device,
                validation_context.physics,
                validation_context.simulation_config,
            ),
            validation_dataset.independent_values,
            validation_protocol,
            photo_config=validation_context.photo_config,
        )
    )

    validation_objective = (
        evaluate_least_squares_objective(
            validation_dataset.observed_values,
            prediction.predicted_delta_vfb_V,
            uncertainty=(
                validation_dataset.observed_uncertainty
            ),
        )
    )

    validation_hash = (
        validation_dataset.dataset_hash()
    )
    qualification = _qualify_training_collection(
        fit_result,
        validation_dataset_hash=validation_hash,
        validation_objective=validation_objective,
        criteria=criteria,
    )

    calibrated_parameter = None
    calibrated_photo_config = None

    if qualification.eligible_for_calibration:
        qualification_hash = (
            qualification.qualification_hash()
        )
        collection_hash = (
            _training_dataset_collection_hash(
                fit_result
            )
        )
        calibrated_parameter = (
            CalibratedPhotoCaptureEfficiency(
                parameter_name=(
                    "photo_capture_efficiency"
                ),
                value=fitted_eta,
                source=(
                    "NCMemSim independent device-level "
                    "photo-capture calibration qualification "
                    f"using validation dataset "
                    f"'{validation_dataset.metadata.dataset_id}': "
                    f"{validation_dataset.metadata.source}"
                ),
                training_dataset_collection_hash=(
                    collection_hash
                ),
                validation_dataset_hash=validation_hash,
                validation_protocol_hash=(
                    validation_protocol.protocol_hash()
                ),
                qualification_hash=qualification_hash,
            )
        )
        calibrated_photo_config = replace(
            fitted_photo_config,
            photo_capture_efficiency=fitted_eta,
        )

    return DevicePhotoCalibrationResult(
        training_dataset_ids=fit_result.dataset_ids,
        training_dataset_hashes=(
            fit_result.dataset_hashes
        ),
        training_dataset_collection_hash=(
            _training_dataset_collection_hash(
                fit_result
            )
        ),
        validation_dataset_id=(
            validation_dataset.metadata.dataset_id
        ),
        validation_dataset_hash=validation_hash,
        validation_protocol=validation_protocol,
        qualification=qualification,
        prediction=prediction,
        calibrated_parameter=calibrated_parameter,
        calibrated_photo_config=(
            calibrated_photo_config
        ),
    )


__all__ = [
    "CalibratedPhotoCaptureEfficiency",
    "DevicePhotoCalibrationResult",
    "qualify_photo_capture_efficiency_fit",
]
