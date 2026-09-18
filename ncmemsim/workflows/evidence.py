"""Immutable, integrity-linked evidence; qualification is not provenance promotion."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json
import math
import platform
from typing import Any
import numpy as np
from .._version import __version__
from ..calibration import CalibrationQualification
from ..device_calibration import DeviceCalibrationSpec
from ..device_fit import DeviceCVFitResult
from ..experimental import DeviceObservableDataset, OpticalAbsorptionDataset, ExperimentalDatasetMetadata, ExperimentalCondition
from ..fit_diagnostics import FitUncertaintyDiagnostics, analyze_fit_uncertainty
from ..hashing import canonical_hash
from ..photo_program_fit import DevicePhotoProgramTimeFitResult
from ..program_fit import DeviceProgramTimeFitResult
from ..dtco.sweep import _json_snapshot


class DataOrigin(str, Enum):
    SYNTHETIC = "synthetic"
    MEASURED = "measured"


def _label(value: Any, field: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field} must be nonempty text without outer whitespace")


def _load(value: str) -> dict:
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = item
        return result
    def constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    result = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    if type(result) is not dict:
        raise ValueError("evidence must be a JSON object")
    _json_snapshot(result)
    return result


def _encode(value):
    # Existing rank diagnostics may legitimately carry infinity. Preserve the
    # exact value in strict JSON, rather than replacing it with zero or null.
    if type(value) is float and not math.isfinite(value):
        return {"_workflow_float": "nan" if math.isnan(value) else "positive_infinity" if value > 0 else "negative_infinity"}
    if type(value) is dict:
        if "_workflow_float" in value:
            raise ValueError("reserved non-finite diagnostic marker")
        return {key: _encode(item) for key, item in value.items()}
    if type(value) is list:
        return [_encode(item) for item in value]
    return value


def _decode(value):
    if type(value) is dict:
        if "_workflow_float" in value:
            if set(value) != {"_workflow_float"} or value["_workflow_float"] not in ("nan", "positive_infinity", "negative_infinity"):
                raise ValueError("invalid diagnostic float marker")
            return {"nan": float("nan"), "positive_infinity": float("inf"), "negative_infinity": -float("inf")}[value["_workflow_float"]]
        return {key: _decode(item) for key, item in value.items()}
    if type(value) is list:
        return [_decode(item) for item in value]
    return value


def _section(value: dict, *, diagnostics: bool = False) -> dict:
    return {"source_hash": canonical_hash(value), "data": _encode(value) if diagnostics else value}


def _check_section(section, *, diagnostics=False):
    if type(section) is not dict or set(section) != {"source_hash", "data"} or type(section["data"]) is not dict:
        raise ValueError("invalid source section")
    value = _decode(section["data"]) if diagnostics else section["data"]
    if canonical_hash(value) != section["source_hash"]:
        raise ValueError("source section hash mismatch")
    return value


def _validate_dataset(raw):
    """Reuse existing domain checks and require lossless canonical round-trip."""
    try:
        metadata = ExperimentalDatasetMetadata(**raw["metadata"])
        if raw["dataset_type"] == "device_observable":
            x, y = raw["independent_variable"], raw["observable"]
            result = DeviceObservableDataset(x["name"], x["unit"], x["values"],
                y["name"], y["unit"], y["values"], metadata,
                observed_uncertainty=y["uncertainty"],
                conditions=tuple(ExperimentalCondition(**item) for item in raw["conditions"]))
        else:
            result = OpticalAbsorptionDataset(raw["wavelength_nm"], raw["absorption_coefficient_m_inv"],
                raw["sn_fraction"], metadata, raw["absorption_uncertainty_m_inv"])
        if _json_snapshot(result.to_dict()) != _json_snapshot(raw):
            raise ValueError("dataset snapshot is not a lossless existing-schema representation")
    except (TypeError, KeyError, AttributeError) as error:
        raise ValueError("invalid dataset snapshot") from error


@dataclass(frozen=True)
class DatasetEvidence:
    """Full dataset snapshot plus explicitly declared origin/applicability."""
    payload_json: str

    def __post_init__(self):
        data = _load(self.payload_json)
        if "evidence_hash" in data:
            digest = data.pop("evidence_hash")
            if digest != canonical_hash(data):
                raise ValueError("dataset evidence integrity mismatch")
        if set(data) != {"schema_version", "origin", "source", "applicability", "dataset_hash", "dataset"} or data["schema_version"] != "workflow-dataset-evidence-v1":
            raise ValueError("unsupported dataset evidence schema")
        DataOrigin(data["origin"])
        _label(data["source"], "source")
        _label(data["applicability"], "applicability")
        dataset = data["dataset"]
        if type(dataset) is not dict or dataset.get("schema_version") != 1 or dataset.get("dataset_type") not in ("device_observable", "optical_absorption"):
            raise ValueError("unsupported dataset snapshot")
        if type(dataset.get("metadata")) is not dict:
            raise ValueError("dataset metadata is required")
        _label(dataset["metadata"].get("dataset_id"), "dataset_id")
        _validate_dataset(dataset)
        if canonical_hash(dataset) != data["dataset_hash"]:
            raise ValueError("dataset hash mismatch")
        object.__setattr__(self, "payload_json", _json_snapshot(data))

    @property
    def dataset_hash(self):
        return self.to_dict()["dataset_hash"]

    @property
    def evidence_hash(self):
        return canonical_hash(json.loads(self.payload_json))

    @property
    def origin(self):
        return DataOrigin(self.to_dict()["origin"])

    def to_dict(self):
        return {**json.loads(self.payload_json), "evidence_hash": self.evidence_hash}

    def to_json(self):
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value):
        data = _load(value)
        digest = data.pop("evidence_hash", None)
        if digest != canonical_hash(data):
            raise ValueError("dataset evidence integrity mismatch")
        return cls(_json_snapshot(data))


def capture_dataset_evidence(dataset, *, origin: DataOrigin, source: str, applicability: str) -> DatasetEvidence:
    if not isinstance(dataset, (DeviceObservableDataset, OpticalAbsorptionDataset, ExperimentalDatasetMetadata, ExperimentalCondition)):
        raise TypeError("dataset must be a supported dataset instance")
    if not isinstance(origin, DataOrigin):
        raise TypeError("origin must be DataOrigin")
    raw = dataset.to_dict()
    return DatasetEvidence(_json_snapshot({"schema_version": "workflow-dataset-evidence-v1",
        "origin": origin.value, "source": source, "applicability": applicability,
        "dataset_hash": dataset.dataset_hash(), "dataset": raw}))


_WORKFLOWS = {"single-dataset-cv-fit", "single-parameter-delta-vfb-vs-programming-time-fit",
    "single-parameter-photo-capture-efficiency-vs-programming-time-fit"}


def _check_workflow(data):
    fields = {"schema_version", "name", "fit_dataset", "validation_dataset", "fit_result",
        "calibration_specification", "diagnostics", "qualification", "runtime", "metadata"}
    if set(data) != fields or data["schema_version"] != "scientific-workflow-evidence-v1":
        raise ValueError("unsupported workflow evidence schema")
    _label(data["name"], "name")
    if type(data["runtime"]) is not dict or set(data["runtime"]) != {"python", "python_implementation", "numpy", "ncmemsim"}:
        raise ValueError("runtime provenance is required")
    for key, value in data["runtime"].items():
        _label(value, key)
    if type(data["metadata"]) is not dict:
        raise ValueError("metadata must be an object")
    training = DatasetEvidence.from_json(_json_snapshot(data["fit_dataset"]))
    validation = None if data["validation_dataset"] is None else DatasetEvidence.from_json(_json_snapshot(data["validation_dataset"]))
    dataset_raw = training.to_dict()["dataset"]
    if dataset_raw["dataset_type"] != "device_observable":
        raise ValueError("supported device fit requires a device-observable dataset")
    if validation is not None:
        other = validation.to_dict()["dataset"]
        if other["dataset_type"] != "device_observable" or any(
                dataset_raw[section][field] != other[section][field]
                for section in ("independent_variable", "observable") for field in ("name", "unit")):
            raise ValueError("validation observable/variable contract mismatch")
    fit = _check_section(data["fit_result"])
    spec = _check_section(data["calibration_specification"])
    if fit.get("schema_version") != 1 or fit.get("workflow") not in _WORKFLOWS or fit.get("scientific_status") != "FITTED":
        raise ValueError("unsupported fit evidence or scientific status")
    if fit.get("dataset_hash") != training.dataset_hash or fit.get("dataset_id") != training.to_dict()["dataset"]["metadata"]["dataset_id"]:
        raise ValueError("fit dataset identity mismatch")
    if spec.get("schema_version") != 1:
        raise ValueError("unsupported calibration specification schema")
    if fit.get("calibration_specification_hash") != canonical_hash(spec):
        raise ValueError("calibration specification identity mismatch")
    if type(fit.get("protocol")) is not dict:
        raise ValueError("fit protocol snapshot is required")
    if fit.get("protocol_hash") != canonical_hash(fit.get("protocol")):
        raise ValueError("fit protocol identity mismatch")
    application = fit.get("parameter_application")
    numerical = fit.get("numerical_result")
    if type(application) is not dict or application.get("specification_hash") != canonical_hash(spec) or type(numerical) is not dict:
        raise ValueError("fit application identity mismatch")
    if type(numerical.get("objective_residuals")) is not list or len(numerical["objective_residuals"]) != len(dataset_raw["observable"]["values"]):
        raise ValueError("fit observation count mismatch")
    if numerical.get("parameter_specification_hash") != canonical_hash(spec.get("parameter_set")) or numerical.get("parameter_specification") != spec.get("parameter_set"):
        raise ValueError("numerical parameter specification mismatch")
    if numerical.get("solver_configuration_hash") != canonical_hash(numerical.get("solver_configuration")):
        raise ValueError("solver configuration identity mismatch")
    if type(application.get("parameter_values")) is not dict or type(numerical.get("fitted_parameters")) is not dict or _json_snapshot(application["parameter_values"]) != _json_snapshot(numerical["fitted_parameters"]):
        raise ValueError("applied fitted values mismatch")
    diagnostics = None if data["diagnostics"] is None else _check_section(data["diagnostics"], diagnostics=True)
    if diagnostics is not None:
        names = [p["name"] for p in spec["parameter_set"]["parameters"]]
        if diagnostics.get("parameter_names") != names or diagnostics.get("n_parameters") != len(names) or diagnostics.get("n_observations") != len(numerical["objective_residuals"]):
            raise ValueError("diagnostic parameter/observation mismatch")
    if data["qualification"] is not None:
        qualification = _check_section(data["qualification"], diagnostics=True)
        if qualification.get("schema_version") != 1 or qualification.get("qualification_type") != "fit-validation-calibration-qualification":
            raise ValueError("unsupported qualification schema")
        if numerical.get("success") is not True:
            raise ValueError("qualification requires a successful numerical fit")
        if validation is None or diagnostics is None:
            raise ValueError("qualification requires validation dataset and diagnostics")
        if qualification.get("fit_dataset_hash") != training.dataset_hash or qualification.get("validation_dataset_hash") != validation.dataset_hash:
            raise ValueError("qualification dataset identity mismatch")
        if type(qualification.get("validation_objective")) is not dict or qualification["validation_objective"].get("n_points") != len(validation.to_dict()["dataset"]["observable"]["values"]):
            raise ValueError("qualification validation observation mismatch")
        if qualification.get("criteria_hash") != canonical_hash(qualification.get("criteria")):
            raise ValueError("qualification criteria identity mismatch")
        if _encode(qualification.get("uncertainty_diagnostics")) != _encode(diagnostics):
            raise ValueError("qualification diagnostic identity mismatch")
        results = qualification.get("criterion_results")
        if type(results) is not list or not results or any(type(p.get("passed")) is not bool for p in results):
            raise ValueError("invalid qualification criteria results")
        criterion_names = [p["name"] for p in results]
        if len(criterion_names) != len(set(criterion_names)):
            raise ValueError("duplicate qualification criterion")
        if type(qualification.get("eligible_for_calibration")) is not bool or qualification["eligible_for_calibration"] != all(p["passed"] for p in results) or qualification.get("failed_criteria") != [p["name"] for p in results if not p["passed"]]:
            raise ValueError("qualification accounting mismatch")
        if qualification["criteria"].get("require_distinct_validation_dataset") and training.dataset_hash == validation.dataset_hash and qualification["eligible_for_calibration"]:
            raise ValueError("independent validation identity mismatch")


@dataclass(frozen=True)
class WorkflowEvidence:
    """Source identities and qualification evidence; not a simulator context."""
    payload_json: str

    def __post_init__(self):
        data = _load(self.payload_json)
        try:
            _check_workflow(data)
        except (KeyError, IndexError, AttributeError) as error:
            raise ValueError("incomplete workflow evidence") from error
        object.__setattr__(self, "payload_json", _json_snapshot(data))

    @property
    def evidence_hash(self):
        return canonical_hash(json.loads(self.payload_json))

    @property
    def scientific_status(self):
        return "FITTED"

    @property
    def qualification_eligible(self):
        section = json.loads(self.payload_json)["qualification"]
        return None if section is None else section["data"]["eligible_for_calibration"]

    def to_dict(self):
        return {**json.loads(self.payload_json), "evidence_hash": self.evidence_hash}

    def to_json(self):
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value):
        data = _load(value)
        digest = data.pop("evidence_hash", None)
        if digest != canonical_hash(data):
            raise ValueError("workflow evidence integrity mismatch")
        return cls(_json_snapshot(data))


def build_workflow_evidence(*, name: str, fit_dataset: DatasetEvidence,
        fit_result, calibration_spec: DeviceCalibrationSpec,
        diagnostics: FitUncertaintyDiagnostics | None = None,
        validation_dataset: DatasetEvidence | None = None,
        qualification: CalibrationQualification | None = None,
        metadata: dict | None = None) -> WorkflowEvidence:
    if not isinstance(fit_dataset, DatasetEvidence) or validation_dataset is not None and not isinstance(validation_dataset, DatasetEvidence):
        raise TypeError("datasets must be DatasetEvidence")
    if not isinstance(fit_result, (DeviceCVFitResult, DeviceProgramTimeFitResult, DevicePhotoProgramTimeFitResult)):
        raise TypeError("fit_result must be a supported single-dataset device fit result")
    if not isinstance(calibration_spec, DeviceCalibrationSpec):
        raise TypeError("calibration_spec must be DeviceCalibrationSpec")
    if diagnostics is not None:
        if not isinstance(diagnostics, FitUncertaintyDiagnostics):
            raise TypeError("diagnostics must be FitUncertaintyDiagnostics")
        expected = analyze_fit_uncertainty(fit_result.numerical_result).to_dict()
        if _json_snapshot(_encode(expected)) != _json_snapshot(_encode(diagnostics.to_dict())):
            raise ValueError("diagnostics do not describe this numerical fit")
    if qualification is not None and not isinstance(qualification, CalibrationQualification):
        raise TypeError("qualification must be CalibrationQualification")
    payload = {"schema_version": "scientific-workflow-evidence-v1", "name": name,
        "fit_dataset": fit_dataset.to_dict(), "validation_dataset": None if validation_dataset is None else validation_dataset.to_dict(),
        "fit_result": _section(fit_result.to_dict()), "calibration_specification": _section(calibration_spec.to_dict()),
        "diagnostics": None if diagnostics is None else _section(diagnostics.to_dict(), diagnostics=True),
        "qualification": None if qualification is None else _section(qualification.to_dict(), diagnostics=True),
        "runtime": {"python": platform.python_version(), "python_implementation": platform.python_implementation(),
                    "numpy": np.__version__, "ncmemsim": __version__}, "metadata": {} if metadata is None else metadata}
    return WorkflowEvidence(_json_snapshot(payload))
