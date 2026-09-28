from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib.util
import json
from pathlib import Path

import pytest

from ncmemsim.dtco.metrics import ObjectiveDirection
from ncmemsim.ensemble.dtco import (
    EnsembleObjective,
    EnsembleScalarDefinition,
    EnsembleScalarKind,
    analyze_ensemble_pareto,
)
from ncmemsim.ensemble.reporting import (
    EnsembleReport,
    build_ensemble_report,
)
from ncmemsim.hashing import canonical_hash


def _load_k6a1_helpers():
    path = (
        Path(__file__).resolve().parent
        / "test_phase_k6_reporting_contracts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase_k6_reporting_contract_helpers",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Phase K6a-1 test helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_K6A1 = _load_k6a1_helpers()


def studies():
    return (
        _K6A1.report_study(
            point_index=0,
            point_value=1.0,
        ),
        _K6A1.report_study(
            point_index=1,
            point_value=2.0,
        ),
    )


def pareto_for(source_studies):
    objective = EnsembleObjective(
        name="mean_response",
        scalar=EnsembleScalarDefinition(
            name="mean_response",
            kind=EnsembleScalarKind.MEAN,
            unit="V",
            metric_name="response",
        ),
        direction=ObjectiveDirection.MAXIMIZE,
    )
    return analyze_ensemble_pareto(
        tuple(
            study.eligibility
            for study in source_studies
        ),
        (objective,),
        name="k6a-report-front",
    )


def reseal_report(raw):
    raw = dict(raw)
    raw.pop("report_hash", None)
    raw["report_hash"] = canonical_hash(raw)
    return json.dumps(raw)


def test_report_roundtrip_is_exact_and_deterministic():
    source = studies()
    first = build_ensemble_report(
        source,
        name="K6a snapshot test",
        metadata={"purpose": "roundtrip"},
    )
    second = build_ensemble_report(
        source,
        name="K6a snapshot test",
        metadata={"purpose": "roundtrip"},
    )

    assert first.to_json() == second.to_json()
    assert first.report_hash == second.report_hash

    restored = EnsembleReport.from_json(first.to_json())
    assert restored.to_json() == first.to_json()
    assert restored.report_hash == first.report_hash

    payload = restored.to_dict()
    assert payload["schema_version"] == "ensemble-report-v1"
    assert len(payload["studies"]) == 2
    assert payload["pareto"] is None


def test_report_snapshot_is_immutable_and_metadata_is_copied():
    source = studies()
    metadata = {"nested": [1]}
    report = build_ensemble_report(
        source,
        metadata=metadata,
    )

    metadata["nested"].append(2)
    exported = report.to_dict()
    exported["metadata"]["nested"].append(3)

    assert report.to_dict()["metadata"] == {"nested": [1]}
    with pytest.raises(FrozenInstanceError):
        report.payload_json = "{}"


def test_optional_pareto_is_integrity_linked_and_roundtrips():
    source = studies()
    pareto = pareto_for(source)

    report = build_ensemble_report(
        source,
        pareto=pareto,
    )
    payload = report.to_dict()

    assert payload["pareto"]["result_hash"] == pareto.result_hash
    assert (
        payload["pareto"]["data"]["source_result_hashes"]
        == [
            study.eligibility.result_hash
            for study in source
        ]
    )
    assert EnsembleReport.from_json(
        report.to_json()
    ).report_hash == report.report_hash


def test_builder_rejects_pareto_source_order_mismatch():
    source = studies()
    pareto = pareto_for(source)

    with pytest.raises(
        ValueError,
        match="Pareto source eligibility order differs",
    ):
        build_ensemble_report(
            tuple(reversed(source)),
            pareto=pareto,
        )


def test_stale_outer_hash_rejects_tampering():
    report = build_ensemble_report(studies())
    raw = report.to_dict()
    raw["name"] = "tampered"

    with pytest.raises(
        ValueError,
        match="report hash differs",
    ):
        EnsembleReport.from_json(json.dumps(raw))


def test_resealed_outer_hash_does_not_hide_nested_component_tampering():
    report = build_ensemble_report(studies())
    raw = report.to_dict()

    raw["studies"][0]["data"]["feasibility"]["data"]["counts"][
        "attempted"
    ] += 1

    with pytest.raises(
        ValueError,
        match="feasibility hash differs",
    ):
        EnsembleReport.from_json(reseal_report(raw))


def test_rehashed_nested_component_cannot_hide_adjacent_source_mismatch():
    report = build_ensemble_report(studies())
    raw = report.to_dict()

    study_wrapper = raw["studies"][0]
    metric_wrapper = study_wrapper["data"]["metric_analysis"]
    metric = metric_wrapper["data"]
    metric["source_result_hash"] = "0" * 64
    metric["analysis_hash"] = canonical_hash(
        {
            "schema_version": "ensemble-metric-analysis-run-v1",
            "spec": metric_wrapper["spec"],
            "source_result_hash": "0" * 64,
        }
    )
    metric_wrapper["result_hash"] = canonical_hash(metric)
    study_wrapper["result_hash"] = canonical_hash(
        study_wrapper["data"]
    )

    with pytest.raises(
        ValueError,
        match="K4a source differs",
    ):
        EnsembleReport.from_json(reseal_report(raw))


def test_rehashed_execution_cannot_hide_broken_embedded_manifest_identity():
    report = build_ensemble_report(studies())
    raw = report.to_dict()

    study_wrapper = raw["studies"][0]
    execution_wrapper = study_wrapper["data"]["execution"]
    execution_wrapper["data"]["manifest"]["manifest_hash"] = "0" * 64
    execution_wrapper["result_hash"] = canonical_hash(
        execution_wrapper["data"]
    )
    study_wrapper["result_hash"] = canonical_hash(
        study_wrapper["data"]
    )

    with pytest.raises(
        ValueError,
        match="sample manifest",
    ):
        EnsembleReport.from_json(reseal_report(raw))


def test_rehashed_pareto_cannot_hide_source_order_tampering():
    source = studies()
    report = build_ensemble_report(
        source,
        pareto=pareto_for(source),
    )
    raw = report.to_dict()

    pareto_wrapper = raw["pareto"]
    pareto = pareto_wrapper["data"]
    pareto["source_result_hashes"].reverse()
    pareto["analysis_hash"] = canonical_hash(
        {
            "schema_version": "ensemble-pareto-run-v1",
            "definition_hash": pareto["definition_hash"],
            "source_result_hashes": pareto["source_result_hashes"],
        }
    )
    pareto_wrapper["result_hash"] = canonical_hash(pareto)

    with pytest.raises(
        ValueError,
        match="Pareto source eligibility order differs",
    ):
        EnsembleReport.from_json(reseal_report(raw))


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(
        ValueError,
        match="duplicate JSON key",
    ):
        EnsembleReport.from_json(
            '{"report_hash":"x","schema_version":"a","schema_version":"b"}'
        )


@pytest.mark.parametrize(
    "kwargs",
    (
        {"name": ""},
        {"metadata": []},
        {"pareto": object()},
    ),
)
def test_builder_rejects_invalid_inputs(kwargs):
    with pytest.raises((TypeError, ValueError)):
        build_ensemble_report(
            studies(),
            **kwargs,
        )


def test_builder_requires_nonempty_typed_studies():
    with pytest.raises(ValueError, match="at least one study"):
        build_ensemble_report(())

    with pytest.raises(TypeError, match="EnsembleReportStudy"):
        build_ensemble_report((object(),))
